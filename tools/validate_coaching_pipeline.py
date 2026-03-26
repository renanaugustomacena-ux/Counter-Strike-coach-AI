"""End-to-end coaching pipeline validator.

Proves the product works: takes a .dem file, ingests it, generates coaching
insights, and prints them.  Exit code 0 = success, 1 = failure.

Usage:
    python tools/validate_coaching_pipeline.py /path/to/demo.dem [player_name]

If player_name is omitted, uses "ALL" to capture all players in the demo.
The script creates a temporary PlayerProfile if one does not already exist,
so the coaching gate (_is_profile_ready) will pass.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/validate_coaching_pipeline.py <demo.dem> [player_name]")
        sys.exit(1)

    demo_path = Path(sys.argv[1])
    player_name = sys.argv[2] if len(sys.argv) > 2 else None

    if not demo_path.exists():
        print(f"ERROR: Demo file not found: {demo_path}")
        sys.exit(1)
    if not demo_path.suffix == ".dem":
        print(f"ERROR: File does not have .dem extension: {demo_path}")
        sys.exit(1)

    print(f"=== CS2 Coaching Pipeline Validator ===")
    print(f"Demo: {demo_path.name}")
    print(f"Size: {demo_path.stat().st_size / (1024 * 1024):.1f} MB")
    print()

    # ── Step 1: Initialize database ──
    print("[1/6] Initializing database...")
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

    init_database()
    db_manager = get_db_manager()
    print("  OK")

    # ── Step 2: Parse demo ──
    print("[2/6] Parsing demo (aggregate stats)...")
    from Programma_CS2_RENAN.backend.data_sources.demo_parser import parse_demo

    target = player_name if player_name else "ALL"
    df = parse_demo(str(demo_path), target_player=target)
    if df.empty:
        print(f"  FAIL: parse_demo returned empty DataFrame (target='{target}')")
        print("  Hint: Check that the player name matches exactly what appears in the demo.")
        sys.exit(1)

    players = df["player_name"].unique().tolist()
    print(f"  OK — {len(df)} player-rows parsed, players: {players}")

    # If no player_name given, pick the first non-pro player
    if not player_name:
        player_name = players[0]
        print(f"  Using player: '{player_name}'")
    elif player_name not in players:
        print(f"  WARNING: '{player_name}' not in demo players {players}")
        player_name = players[0]
        print(f"  Falling back to: '{player_name}'")

    # ── Step 3: Ensure PlayerProfile exists ──
    print("[3/6] Ensuring PlayerProfile exists...")
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerProfile

    with db_manager.get_session() as session:
        profile = session.exec(
            select(PlayerProfile).where(PlayerProfile.player_name == player_name)
        ).first()
        if not profile:
            session.add(PlayerProfile(player_name=player_name))
            session.commit()
            print(f"  Created PlayerProfile for '{player_name}'")
        else:
            print(f"  Profile exists for '{player_name}'")

    # ── Step 4: Save player stats ──
    print("[4/6] Saving player stats to database...")
    import math

    row = df[df["player_name"] == player_name].iloc[0]
    stats_dict = row.to_dict()
    stats_dict.pop("player_name", None)

    # Sanitize NaN/Inf
    for key, val in list(stats_dict.items()):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            stats_dict[key] = 0.0

    # Clamp rating
    if "rating" in stats_dict:
        stats_dict["rating"] = max(0.0, min(5.0, float(stats_dict["rating"])))
    for field in ("avg_kills", "avg_adr"):
        if field in stats_dict and stats_dict[field] < 0:
            stats_dict[field] = 0.0

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    clean_demo_name = demo_path.stem
    match_stats = PlayerMatchStats(
        player_name=player_name,
        demo_name=clean_demo_name,
        is_pro=False,
        **stats_dict,
    )
    db_manager.upsert(match_stats)
    print(f"  OK — Stats saved for '{player_name}' / '{clean_demo_name}'")

    # Print key stats
    for key in ("avg_kills", "avg_deaths", "avg_adr", "avg_hs", "avg_kast", "rating"):
        if key in stats_dict:
            print(f"    {key}: {stats_dict[key]:.2f}")

    # ── Step 5: Run ML pipeline (coaching generation) ──
    print("[5/6] Running coaching pipeline...")
    from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections
    from Programma_CS2_RENAN.backend.processing.baselines.pro_baseline import (
        calculate_deviations,
        get_pro_baseline,
    )

    baseline = get_pro_baseline()
    print(f"  Pro baseline loaded: {len(baseline)} features")

    deviations = calculate_deviations(stats_dict, baseline)
    print(f"  Deviations computed: {len(deviations)} features")
    for feat, val in list(deviations.items())[:5]:
        z = val[0] if isinstance(val, (tuple, list)) else val
        print(f"    {feat}: Z={z:+.2f}")

    corrections = generate_corrections(deviations, 30)
    print(f"  Top corrections: {len(corrections)}")

    # Generate narrative insights
    from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
    from Programma_CS2_RENAN.backend.processing.skill_assessment import SkillAxes

    insights_text = []
    for c in corrections:
        feat = c["feature"]
        category = SkillAxes.DECISION
        if "hs" in feat or "accuracy" in feat:
            category = SkillAxes.MECHANICS
        elif "aggression" in feat or "deaths" in feat:
            category = SkillAxes.POSITIONING

        context = {
            "weapon": (
                feat.replace("avg_", "").split("_")[0]
                if "accuracy" in feat or "hs" in feat
                else "equipment"
            ),
            "location": "critical sectors" if category == SkillAxes.POSITIONING else "the site",
        }

        message = ExplanationGenerator.generate_narrative(
            category=category,
            feature=feat,
            delta=c["weighted_z"],
            context=context,
            skill_level=5,
        )
        if message:
            insights_text.append(
                {
                    "feature": feat,
                    "severity": ExplanationGenerator.classify_insight_severity(c["weighted_z"]),
                    "category": category,
                    "message": message,
                }
            )

    print(f"  Narrative insights generated: {len(insights_text)}")

    # ── Step 6: Report results ──
    print()
    print("=" * 60)
    print("COACHING OUTPUT")
    print("=" * 60)

    if not insights_text:
        print()
        print("  NO INSIGHTS GENERATED")
        print("  This means the corrections were too small to produce coaching text,")
        print("  or the ExplanationGenerator returned empty narratives.")
        print()
        print("  Raw corrections:")
        for c in corrections:
            print(f"    {c['feature']}: weighted_z={c['weighted_z']:.3f}")
        print()
        print("RESULT: FAIL (no coaching output produced)")
        sys.exit(1)

    for i, insight in enumerate(insights_text, 1):
        print()
        print(f"--- Insight {i} ---")
        print(f"  Feature:  {insight['feature']}")
        print(f"  Category: {insight['category']}")
        print(f"  Severity: {insight['severity']}")
        print(f"  Message:")
        # Wrap long messages
        msg = insight["message"]
        for line in msg.split("\n"):
            print(f"    {line}")

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Player:     {player_name}")
    print(f"  Demo:       {clean_demo_name}")
    print(f"  Insights:   {len(insights_text)}")
    severities = {}
    for ins in insights_text:
        severities[ins["severity"]] = severities.get(ins["severity"], 0) + 1
    print(f"  Severities: {severities}")
    total_words = sum(len(ins["message"].split()) for ins in insights_text)
    print(f"  Total words: {total_words}")
    print()

    if len(insights_text) >= 1 and total_words >= 10:
        print("RESULT: PASS")
        sys.exit(0)
    else:
        print("RESULT: FAIL (insufficient coaching output)")
        sys.exit(1)


if __name__ == "__main__":
    main()
