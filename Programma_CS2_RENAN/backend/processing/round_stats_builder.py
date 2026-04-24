"""
Round Stats Builder — Constructs per-round, per-player statistics from demo events.

This module bridges raw demo event data (player_death, player_hurt, weapon_fire,
round_end, player_blind) into the RoundStats isolation layer defined in db_models.py.

Fusion Plan Proposal 4: Per-Round Statistical Isolation Layer.
Fusion Plan Phase 1: Wires trade kills, kill enrichment, and utility effectiveness
into the aggregation pipeline (Proposals 1, 2, 3).

Usage:
    from Programma_CS2_RENAN.backend.processing.round_stats_builder import (
        build_round_stats, enrich_from_demo
    )
    round_stats = build_round_stats(parser, demo_name="match.dem")
    enrichment, round_stats = enrich_from_demo("path/to/demo.dem", "demo.dem")
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.round_stats_builder")

# Grenade weapon identifiers in demoparser2.
#
# Q1-03: demoparser2 uses inconsistent weapon naming across event types:
#   - `player_hurt.weapon` emits unprefixed names: "hegrenade", "inferno"
#   - `weapon_fire.weapon`  emits `weapon_`-prefixed names: "weapon_smokegrenade",
#     "weapon_flashbang", "weapon_hegrenade", "weapon_molotov", "weapon_incgrenade"
# The sets below include BOTH forms so the same match check works for either
# event type without requiring the caller to normalize.
HE_WEAPONS = {"hegrenade", "weapon_hegrenade"}
FIRE_WEAPONS = {"inferno", "molotov", "incgrenade", "weapon_molotov", "weapon_incgrenade"}
SMOKE_WEAPONS = {"smokegrenade", "weapon_smokegrenade"}
FLASH_WEAPONS = {"flashbang", "weapon_flashbang"}
ALL_GRENADE_WEAPONS = HE_WEAPONS | FIRE_WEAPONS | SMOKE_WEAPONS | FLASH_WEAPONS

# R4-07-01: Flash assist window — 2 seconds at default 64 tick.
# P-RSB-01: This is now a DEFAULT only. build_round_stats() derives a
# per-demo local value instead of mutating this global.
_DEFAULT_FLASH_ASSIST_WINDOW_TICKS = 128


def _parse_events_safe(parser, event_name: str) -> pd.DataFrame:
    """Parse events from demo, returning empty DataFrame on failure."""
    try:
        events = parser.parse_events([event_name])
        if events:
            return events[0][1] if isinstance(events[0], tuple) else pd.DataFrame(events)
    except Exception as e:
        logger.warning("Failed to parse %s: %s", event_name, e)
    return pd.DataFrame()


def _build_round_boundaries(round_end_df: pd.DataFrame) -> List[Dict]:
    """
    Build round metadata from round_end events.

    Returns:
        List of dicts with keys: round_number, start_tick, end_tick, winner
    """
    if round_end_df.empty:
        return []

    boundaries = []
    ticks = sorted(round_end_df["tick"].tolist())

    for i, (_, row) in enumerate(round_end_df.sort_values("tick").iterrows()):
        round_num = int(row.get("round", i + 1))
        end_tick = int(row["tick"])
        # H-18: Use previous end_tick + 1 as start to prevent overlap.
        # Round i's end_tick and round i+1's start_tick no longer share a tick.
        start_tick = ticks[i - 1] + 1 if i > 0 else 0
        winner = str(row.get("winner", "")).strip() if pd.notna(row.get("winner")) else None

        boundaries.append(
            {
                "round_number": round_num,
                "start_tick": start_tick,
                "end_tick": end_tick,
                "winner": winner,
            }
        )

    # H-06: Validate round boundary completeness
    if boundaries:
        expected_rounds = set(range(1, len(boundaries) + 1))
        actual_rounds = {b["round_number"] for b in boundaries}
        missing = expected_rounds - actual_rounds
        if missing:
            logger.warning("Missing round boundaries for rounds: %s", sorted(missing))
        if any(b["start_tick"] > b["end_tick"] for b in boundaries):
            logger.error("Inverted round boundary detected (start > end)")

    return boundaries


def _assign_round(tick: int, boundaries: List[Dict]) -> Optional[int]:
    """Assign a tick to a round number using boundaries.

    P-RSB-04: Returns None for ticks outside all boundaries (warmup/overtime)
    instead of silently attributing them to the last round.
    """
    for b in boundaries:
        if b["start_tick"] <= tick <= b["end_tick"]:
            return b["round_number"]
    return None


def _get_team_roster(parser) -> Dict[str, int]:
    """Get player -> team_num mapping from tick data."""
    try:
        from Programma_CS2_RENAN.backend.data_sources.trade_kill_detector import build_team_roster

        return build_team_roster(parser)
    except Exception:
        logger.warning("Team roster extraction failed — trade kills unavailable", exc_info=True)
        return {}


def _team_num_to_side(team_num: int, round_number: int) -> str:
    """
    Convert team_num to CT/T side, accounting for half-switch at round 13.

    In CS2: teams switch sides after round 12 (MR12 format).
    team_num 2 and 3 alternate meaning based on half.
    """
    # Before half-switch (rounds 1-12): team 2 = one side, team 3 = other
    # After half-switch (rounds 13+): sides swap
    # We don't know which team_num is CT vs T from the data alone,
    # but we can provide consistent labeling
    if round_number <= 12:
        return "CT" if team_num == 3 else "T"
    else:
        return "T" if team_num == 3 else "CT"


def compute_round_rating(stats: Dict) -> float:
    """
    Compute HLTV 2.0 rating for a single round.

    Per-round values map directly to per-round-rates since n_rounds=1:
      KPR = kills, DPR = deaths, ADR = damage_dealt
      KAST = 1.0 if player got a Kill, Assist, Survived, or was Traded

    Uses the unified rating module to ensure training-inference consistency.

    Args:
        stats: Dict with round stat fields (kills, deaths, assists, etc.)

    Returns:
        HLTV 2.0 rating for this single round.
    """
    from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
        compute_hltv2_rating,
    )

    kills = stats.get("kills", 0)
    deaths = stats.get("deaths", 0)
    assists = stats.get("assists", 0)
    damage = stats.get("damage_dealt", 0)
    was_traded = stats.get("was_traded", False)

    kpr = float(kills)
    dpr = float(deaths)
    adr = float(damage)

    # KAST: 1.0 if player contributed (Kill, Assist, Survived, or Traded)
    survived = deaths == 0
    kast = 1.0 if (kills > 0 or assists > 0 or survived or was_traded) else 0.0

    return compute_hltv2_rating(kpr=kpr, dpr=dpr, kast=kast, avg_adr=adr)


def _derive_flash_assist_window(parser) -> int:
    """Derive per-demo flash assist window from header tick_rate.

    P-RSB-01: Computed locally per demo (no global mutation).
    P-RSB-05: tick_rate validated to [32, 256]; falls back to default.

    Returns:
        Flash assist window in ticks (tick_rate * 2 = 2-second window).
    """
    try:
        header = parser.parse_header()
        tick_rate = int(float(header.get("tick_rate", 64) or 64))
        if not (32 <= tick_rate <= 256):
            logger.warning(
                "P-RSB-05: tick_rate %d outside valid range [32, 256], using default",
                tick_rate,
            )
            return _DEFAULT_FLASH_ASSIST_WINDOW_TICKS
        return tick_rate * 2
    except Exception:
        return _DEFAULT_FLASH_ASSIST_WINDOW_TICKS


def _collect_player_names(
    deaths_df: pd.DataFrame,
    team_roster: Dict[str, int],
) -> set:
    """Collect all unique player names from death events and the team roster.

    P-RSB-02: Only roster entries with valid team_num (2 or 3) are included;
    team_num 0 means unassigned/spectator and produces unreliable stats.

    Returns:
        Set of lowercase, stripped player name strings (empty string excluded).
    """
    all_players: set = set()
    if not deaths_df.empty:
        if "attacker_name" in deaths_df.columns:
            all_players.update(
                deaths_df["attacker_name"].dropna().astype(str).str.strip().str.lower().unique()
            )
        if "user_name" in deaths_df.columns:
            all_players.update(
                deaths_df["user_name"].dropna().astype(str).str.strip().str.lower().unique()
            )
    for name, tnum in team_roster.items():
        if tnum in (2, 3):
            all_players.add(name)
    all_players.discard("")
    return all_players


def _init_round_player_accumulators(
    boundaries: List[Dict],
    all_players: set,
    team_roster: Dict[str, int],
    demo_name: str,
) -> Dict[Tuple[int, str], Dict]:
    """Initialize zeroed stat accumulators for every (round, player) pair.

    M6 FIX: Players are sorted for deterministic iteration order.
    P-RSB-02: Players without a valid team assignment (2 or 3) are skipped.

    Returns:
        Dict keyed by (round_number, player_name) with zeroed stat dicts.
    """
    round_player_stats: Dict[Tuple[int, str], Dict] = {}

    for b in boundaries:
        rn = b["round_number"]
        for player in sorted(all_players):
            team_num = team_roster.get(player, 0)
            if team_num not in (2, 3):
                continue
            side = _team_num_to_side(team_num, rn)

            round_won = False
            if b["winner"] and side != "unknown":
                round_won = b["winner"].upper() == side

            round_player_stats[(rn, player)] = {
                "demo_name": demo_name,
                "round_number": rn,
                "player_name": player,
                "side": side,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "damage_dealt": 0,
                "headshot_kills": 0,
                "trade_kills": 0,
                "was_traded": False,
                # GAP-03: accumulate trade-kill response timing so
                # aggregate_round_stats_to_match() can emit avg_trade_response_ticks.
                "trade_response_ticks_sum": 0,
                "trade_response_count": 0,
                "thrusmoke_kills": 0,
                "wallbang_kills": 0,
                "noscope_kills": 0,
                "blind_kills": 0,
                "opening_kill": False,
                "opening_death": False,
                "he_damage": 0.0,
                "molotov_damage": 0.0,
                "flashes_thrown": 0,
                "smokes_thrown": 0,
                "flash_assists": 0,
                # Q1-01: Utility blind metrics — sum of flash durations inflicted on
                # enemies and the set of distinct enemy names blinded this round.
                # Aggregated to match level in aggregate_round_stats_to_match().
                "blind_time_on_enemies": 0.0,
                "enemies_blinded": set(),
                "equipment_value": 0,
                "round_won": round_won,
                "mvp": False,
                "kast": False,
                "round_rating": None,
            }

    return round_player_stats


def _process_death_events(
    deaths_df: pd.DataFrame,
    boundaries: List[Dict],
    round_player_stats: Dict[Tuple[int, str], Dict],
) -> None:
    """Accumulate kills, deaths, assists, and opening duels from player_death events.

    Mutates *round_player_stats* in place.
    P-RSB-04: Ticks outside all round boundaries (warmup/overtime) are skipped.
    """
    if deaths_df.empty:
        return

    deaths_df = deaths_df.sort_values("tick").reset_index(drop=True)

    if "assister_name" not in deaths_df.columns:
        logger.info(
            "player_death events lack 'assister_name' — assists counted from other sources only"
        )

    first_death_per_round: Dict[int, bool] = {}

    for _, death in deaths_df.iterrows():
        tick = int(death["tick"])
        rn = _assign_round(tick, boundaries)
        if rn is None:
            continue

        attacker = str(death.get("attacker_name", "")).strip().lower()
        victim = str(death.get("user_name", "")).strip().lower()

        # Kills + kill enrichment for attacker
        key_a = (rn, attacker)
        if key_a in round_player_stats:
            round_player_stats[key_a]["kills"] += 1
            if death.get("headshot", False):
                round_player_stats[key_a]["headshot_kills"] += 1
            if death.get("thrusmoke", False):
                round_player_stats[key_a]["thrusmoke_kills"] += 1
            if int(death.get("penetrated", 0)) > 0:
                round_player_stats[key_a]["wallbang_kills"] += 1
            if death.get("noscope", False):
                round_player_stats[key_a]["noscope_kills"] += 1
            if death.get("attackerblind", False):
                round_player_stats[key_a]["blind_kills"] += 1

        # Death for victim
        key_v = (rn, victim)
        if key_v in round_player_stats:
            round_player_stats[key_v]["deaths"] += 1

        # Assists
        assister = str(death.get("assister_name", "")).strip().lower()
        key_assist = (rn, assister)
        if assister and key_assist in round_player_stats:
            round_player_stats[key_assist]["assists"] += 1

        # Opening duel (first death in each round)
        if rn not in first_death_per_round:
            first_death_per_round[rn] = True
            if key_a in round_player_stats:
                round_player_stats[key_a]["opening_kill"] = True
            if key_v in round_player_stats:
                round_player_stats[key_v]["opening_death"] = True


def _process_damage_events(
    hurt_df: pd.DataFrame,
    boundaries: List[Dict],
    round_player_stats: Dict[Tuple[int, str], Dict],
) -> None:
    """Accumulate damage_dealt, he_damage, and molotov_damage from player_hurt events.

    Mutates *round_player_stats* in place.
    """
    if hurt_df.empty or "dmg_health" not in hurt_df.columns:
        return

    for _, hurt in hurt_df.iterrows():
        tick = int(hurt["tick"])
        rn = _assign_round(tick, boundaries)
        if rn is None:
            continue
        attacker = str(hurt.get("attacker_name", "")).strip().lower()
        weapon = str(hurt.get("weapon", "")).strip().lower()
        dmg = int(hurt.get("dmg_health", 0))

        key = (rn, attacker)
        if key not in round_player_stats:
            continue

        round_player_stats[key]["damage_dealt"] += dmg

        if weapon in HE_WEAPONS:
            round_player_stats[key]["he_damage"] += dmg
        elif weapon in FIRE_WEAPONS:
            round_player_stats[key]["molotov_damage"] += dmg


def _process_utility_throws(
    parser,
    boundaries: List[Dict],
    round_player_stats: Dict[Tuple[int, str], Dict],
) -> None:
    """Count flash and smoke throws from weapon_fire events.

    Q1-04: demoparser2 weapon_fire uses 'user_name' (not 'player_name') as the
    actor column. We try user_name first and fall back to player_name.
    Mutates *round_player_stats* in place.
    """
    fire_df = _parse_events_safe(parser, "weapon_fire")
    if fire_df.empty or "weapon" not in fire_df.columns:
        return

    for _, fire in fire_df.iterrows():
        tick = int(fire["tick"])
        rn = _assign_round(tick, boundaries)
        if rn is None:
            continue
        player = str(fire.get("user_name", fire.get("player_name", ""))).strip().lower()
        weapon = str(fire.get("weapon", "")).strip().lower()

        key = (rn, player)
        if key not in round_player_stats:
            continue

        if weapon in FLASH_WEAPONS:
            round_player_stats[key]["flashes_thrown"] += 1
        elif weapon in SMOKE_WEAPONS:
            round_player_stats[key]["smokes_thrown"] += 1


def _process_blind_events(
    parser,
    deaths_df: pd.DataFrame,
    boundaries: List[Dict],
    team_roster: Dict[str, int],
    flash_assist_window: int,
    round_player_stats: Dict[Tuple[int, str], Dict],
) -> None:
    """Accumulate blind metrics and detect flash assists from player_blind events.

    Q1-01: Always processes blind events for blind_time_on_enemies and
    enemies_blinded even when no kills occur. Only ENEMY blinds are counted;
    teammate blinds are ignored.
    Mutates *round_player_stats* in place.
    """
    blind_df = _parse_events_safe(parser, "player_blind")
    if blind_df.empty or "blind_duration" not in blind_df.columns:
        return

    blind_df = blind_df.sort_values("tick").reset_index(drop=True)
    deaths_sorted = (
        deaths_df.sort_values("tick").reset_index(drop=True) if not deaths_df.empty else None
    )

    for _, blind_event in blind_df.iterrows():
        blind_tick = int(blind_event["tick"])
        blinder = str(blind_event.get("attacker_name", "")).strip().lower()
        blinded_player = str(blind_event.get("user_name", "")).strip().lower()
        rn = _assign_round(blind_tick, boundaries)
        if rn is None:
            continue

        if not blinder or not blinded_player:
            continue

        blinder_team = team_roster.get(blinder, 0)
        blinded_team = team_roster.get(blinded_player, 0)

        is_enemy_blind = (
            blinder_team in (2, 3) and blinded_team in (2, 3) and blinder_team != blinded_team
        )

        if is_enemy_blind:
            key = (rn, blinder)
            if key in round_player_stats:
                try:
                    duration = float(blind_event.get("blind_duration", 0.0) or 0.0)
                except (TypeError, ValueError):
                    duration = 0.0
                round_player_stats[key]["blind_time_on_enemies"] += duration
                round_player_stats[key]["enemies_blinded"].add(blinded_player)

        # Flash assist cross-reference: kill of the blinded player within the
        # assist window by a teammate of the blinder.
        if deaths_sorted is None:
            continue

        for _, kill in deaths_sorted.iterrows():
            kill_tick = int(kill["tick"])
            if kill_tick < blind_tick:
                continue
            if kill_tick > blind_tick + flash_assist_window:
                break

            victim = str(kill.get("user_name", "")).strip().lower()
            killer = str(kill.get("attacker_name", "")).strip().lower()

            if victim != blinded_player:
                continue

            killer_team = team_roster.get(killer, 0)
            if killer_team == blinder_team and killer != blinder and killer_team in (2, 3):
                key = (rn, blinder)
                if key in round_player_stats:
                    round_player_stats[key]["flash_assists"] += 1
                break  # Only count one assist per blind event


def _integrate_trade_kills(
    parser,
    round_player_stats: Dict[Tuple[int, str], Dict],
) -> None:
    """Integrate trade kill / was-traded flags from the trade kill detector.

    Mutates *round_player_stats* in place. Failures are logged and skipped
    (trade data is enrichment, not critical path).
    """
    try:
        from Programma_CS2_RENAN.backend.data_sources.trade_kill_detector import analyze_demo_trades

        trade_result, _ = analyze_demo_trades(parser)
        for detail in trade_result.trade_details:
            rn = detail["round"]
            trader = detail["trade_killer"]
            traded_victim = detail["original_victim"]
            response_ticks = int(detail.get("response_ticks", 0) or 0)

            key_trader = (rn, trader)
            if key_trader in round_player_stats:
                round_player_stats[key_trader]["trade_kills"] += 1
                # GAP-03: capture how fast the teammate responded. Lower =
                # faster team revenge / better positioning discipline.
                if response_ticks > 0:
                    round_player_stats[key_trader]["trade_response_ticks_sum"] += response_ticks
                    round_player_stats[key_trader]["trade_response_count"] += 1

            key_traded = (rn, traded_victim)
            if key_traded in round_player_stats:
                round_player_stats[key_traded]["was_traded"] = True
    except Exception as e:
        logger.warning("Trade kill integration into round stats skipped: %s", e)


def _compute_kast_and_ratings(
    round_player_stats: Dict[Tuple[int, str], Dict],
) -> None:
    """Compute per-round KAST flag and HLTV 2.0 rating for each entry.

    KAST = True if the player got a Kill, Assist, Survived, or was Traded.
    Mutates *round_player_stats* in place.
    """
    for _key, stats in round_player_stats.items():
        survived = stats["deaths"] == 0
        stats["kast"] = bool(
            stats["kills"] > 0 or stats["assists"] > 0 or survived or stats["was_traded"]
        )
        stats["round_rating"] = compute_round_rating(stats)


def build_round_stats(
    parser,
    demo_name: str,
    team_roster: Optional[Dict[str, int]] = None,
) -> List[Dict]:
    """
    Build per-round, per-player statistics from a parsed demo.

    Orchestrates event parsing and delegates to focused sub-functions:
    _derive_flash_assist_window, _collect_player_names,
    _init_round_player_accumulators, _process_death_events,
    _process_damage_events, _process_utility_throws,
    _process_blind_events, _integrate_trade_kills,
    _compute_kast_and_ratings.

    Args:
        parser: demoparser2.DemoParser instance.
        demo_name: Name of the demo file for DB linking.
        team_roster: Optional pre-built team roster. If None, built from parser.

    Returns:
        List of dicts, each representing one RoundStats row.
    """
    flash_assist_window = _derive_flash_assist_window(parser)

    # Parse all needed events
    round_end_df = _parse_events_safe(parser, "round_end")
    deaths_df = _parse_events_safe(parser, "player_death")
    hurt_df = _parse_events_safe(parser, "player_hurt")

    if round_end_df.empty:
        logger.warning("No round_end events — cannot build round stats")
        return []

    boundaries = _build_round_boundaries(round_end_df)
    if not boundaries:
        return []

    # Get team roster
    if team_roster is None:
        team_roster = _get_team_roster(parser)

    # R4-07-02: Validate team mapping — all team_num values should be 0, 2, or 3
    invalid_teams = {v for v in team_roster.values() if v not in (0, 2, 3)}
    if invalid_teams:
        logger.warning("R4-07-02: Unexpected team_num values in roster: %s", invalid_teams)

    all_players = _collect_player_names(deaths_df, team_roster)

    round_player_stats = _init_round_player_accumulators(
        boundaries, all_players, team_roster, demo_name
    )

    _process_death_events(deaths_df, boundaries, round_player_stats)
    _process_damage_events(hurt_df, boundaries, round_player_stats)
    _process_utility_throws(parser, boundaries, round_player_stats)
    _process_blind_events(
        parser, deaths_df, boundaries, team_roster, flash_assist_window, round_player_stats
    )
    _integrate_trade_kills(parser, round_player_stats)
    _compute_kast_and_ratings(round_player_stats)

    result = list(round_player_stats.values())
    logger.info(
        "Built %d round stats entries (%d rounds x %d players) for %s",
        len(result),
        len(boundaries),
        len(all_players),
        demo_name,
    )
    return result


def aggregate_round_stats_to_match(
    round_stats: List[Dict],
    player_name: str,
) -> Dict:
    """
    Aggregate per-round stats for a single player into match-level enrichment fields.

    These fields are designed to merge directly into PlayerMatchStats via dict.update().

    Args:
        round_stats: Full list of round stat dicts (all players, all rounds).
        player_name: Lowercase player name to filter for.

    Returns:
        Dict with enrichment keys matching PlayerMatchStats field names.
    """
    player_rounds = [rs for rs in round_stats if rs["player_name"] == player_name]

    if not player_rounds:
        return {}

    num_rounds = len(player_rounds)
    total_kills = sum(rs["kills"] for rs in player_rounds)
    total_deaths = sum(rs["deaths"] for rs in player_rounds)

    # Q1-01: Union of enemies blinded across all rounds for distinct count.
    enemies_blinded_union: set = set()
    for rs in player_rounds:
        enemies_blinded_union.update(rs.get("enemies_blinded", set()))

    # GAP-03: average response ticks for the trade kills this player executed.
    # Aggregated across rounds; missing data (no trade kills) → 0.0 default
    # (PlayerMatchStats.avg_trade_response_ticks schema default).
    _resp_sum = sum(rs.get("trade_response_ticks_sum", 0) for rs in player_rounds)
    _resp_count = sum(rs.get("trade_response_count", 0) for rs in player_rounds)
    _avg_trade_response_ticks = float(_resp_sum) / _resp_count if _resp_count > 0 else 0.0

    enrichment = {
        # Trade kill metrics (Proposal 1)
        "trade_kill_ratio": sum(rs["trade_kills"] for rs in player_rounds) / max(1, total_kills),
        "was_traded_ratio": sum(1 for rs in player_rounds if rs["was_traded"])
        / max(1, total_deaths),
        "avg_trade_response_ticks": _avg_trade_response_ticks,
        # Kill enrichment (Proposal 1)
        "thrusmoke_kill_pct": sum(rs["thrusmoke_kills"] for rs in player_rounds)
        / max(1, total_kills),
        "wallbang_kill_pct": sum(rs["wallbang_kills"] for rs in player_rounds)
        / max(1, total_kills),
        "noscope_kill_pct": sum(rs["noscope_kills"] for rs in player_rounds) / max(1, total_kills),
        "blind_kill_pct": sum(rs["blind_kills"] for rs in player_rounds) / max(1, total_kills),
        # Utility breakdown (Proposal 2)
        "he_damage_per_round": sum(rs["he_damage"] for rs in player_rounds) / max(1, num_rounds),
        "molotov_damage_per_round": sum(rs["molotov_damage"] for rs in player_rounds)
        / max(1, num_rounds),
        "smokes_per_round": sum(rs["smokes_thrown"] for rs in player_rounds) / max(1, num_rounds),
        "flash_assists": float(sum(rs["flash_assists"] for rs in player_rounds)),
        # Q1-01: Utility blind metrics — sum of flash durations inflicted on enemies
        # and count of distinct enemies blinded across the match.
        "utility_blind_time": float(
            sum(rs.get("blind_time_on_enemies", 0.0) for rs in player_rounds)
        ),
        "utility_enemies_blinded": float(len(enemies_blinded_union)),
    }

    # Opening duel win % (only count rounds where player was in an opening duel)
    opening_kills = sum(1 for rs in player_rounds if rs["opening_kill"])
    opening_deaths = sum(1 for rs in player_rounds if rs["opening_death"])
    total_opening_duels = opening_kills + opening_deaths
    if total_opening_duels > 0:
        enrichment["opening_duel_win_pct"] = opening_kills / total_opening_duels

    return enrichment


def enrich_from_demo(
    demo_path: str,
    demo_name: str,
    target_player: Optional[str] = None,
) -> Tuple[Dict[str, Dict], List[Dict]]:
    """
    Build round stats from a demo and aggregate to match-level enrichment.

    This is the bridge function that connects the round_stats_builder to the
    ingestion pipeline, closing the gap where enrichment fields were never populated.

    Args:
        demo_path: Path to the .dem file.
        demo_name: Name of the demo file for DB linking.
        target_player: If set, return enrichment only for this player (lowercase).
                       If None, return enrichment for all players.

    Returns:
        Tuple of:
        - enrichment_by_player: Dict[player_name, enrichment_dict] for PlayerMatchStats
        - round_stats: List[Dict] raw round stats for RoundStats DB persistence
    """
    from demoparser2 import DemoParser

    try:
        parser = DemoParser(demo_path)
        round_stats = build_round_stats(parser, demo_name)
    except Exception as e:
        logger.exception("Failed to build round stats for %s", demo_name)
        return {}, []

    if not round_stats:
        return {}, []

    # Get unique player names
    all_players = {rs["player_name"] for rs in round_stats}
    if target_player:
        all_players = {p for p in all_players if p == target_player.strip().lower()}

    # Aggregate per player
    enrichment_by_player = {}
    for player in all_players:
        enrichment = aggregate_round_stats_to_match(round_stats, player)
        if enrichment:
            enrichment_by_player[player] = enrichment

    logger.info(
        "Enrichment complete for %s: %d players, %d round entries",
        demo_name,
        len(enrichment_by_player),
        len(round_stats),
    )
    return enrichment_by_player, round_stats
