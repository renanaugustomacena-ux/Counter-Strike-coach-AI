"""GAP-15 / TASKS#48: LLM answer-quality eval for the coaching dialogue.

Builds fixture questions from LIVE database ground truth (top-kill rounds,
ambiguous team pairings, per-player match stats), asks them through the real
CoachingDialogueEngine, and scores each answer on groundedness: the fraction
of expected DB facts actually present in the response.

This measures the full pipeline — tool phase, retrieval, disambiguation,
prompt rules — not the LLM in isolation.

Usage (repo root, venv on):
    python tools/coach_answer_eval.py             # full run (needs Ollama)
    python tools/coach_answer_eval.py --dry-run   # build + print fixtures only
    python tools/coach_answer_eval.py --limit 4
Report: reports/coach_answer_eval_<UTC>.json  · exit 0 ok, 2 = env not ready.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import func  # noqa: E402
from sqlmodel import select  # noqa: E402

from Programma_CS2_RENAN.backend.storage.database import get_db_manager  # noqa: E402
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, RoundStats  # noqa: E402
from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

logger = get_logger("cs2analyzer.coach_answer_eval")


@dataclass
class Fixture:
    fixture_id: str
    category: str
    question: str
    expected_facts: List[str]
    check: str = "all"  # "all" = every fact scored; "any" = one hit suffices


@dataclass
class Result:
    fixture_id: str
    category: str
    question: str
    expected_facts: List[str]
    facts_found: List[str] = field(default_factory=list)
    score: float = 0.0
    answer_preview: str = ""


def build_fixtures(limit: int = 0) -> List[Fixture]:
    """Derive fixtures from DB ground truth. Read-only."""
    fixtures: List[Fixture] = []
    db = get_db_manager()

    with db.get_session() as session:
        # Demos with the richest round data
        rows = session.exec(
            select(RoundStats.demo_name, func.count())
            .group_by(RoundStats.demo_name)
            .order_by(func.count().desc())
            .limit(3)
        ).all()
        rich_demos = [r[0] for r in rows if r[0]]

        # 1. Round drill-down: top-kill round per demo, expected = the
        #    round's leader (unambiguous DB fact).
        for demo in rich_demos[:2]:
            top = session.exec(
                select(RoundStats)
                .where(RoundStats.demo_name == demo)
                .order_by(
                    RoundStats.kills.desc(),  # type: ignore[union-attr]
                    RoundStats.damage_dealt.desc(),  # type: ignore[union-attr]
                )
                .limit(1)
            ).first()
            if top is None:
                continue
            fixtures.append(
                Fixture(
                    fixture_id=f"round_drill:{demo}:R{top.round_number}",
                    category="round_drill",
                    question=(
                        f"In the match {demo}, what happened in round "
                        f"{top.round_number}? Who led the kills?"
                    ),
                    expected_facts=[top.player_name],
                )
            )

        # 2. Ambiguity: a team pairing with >= 2 demos — a grounded answer
        #    must surface more than one candidate instead of guessing.
        all_demos = [
            d for d in session.exec(select(PlayerMatchStats.demo_name).distinct()).all() if d
        ]
        pair_fixture = None
        for demo in all_demos:
            tokens = demo.lower().replace("_", "-").split("-vs-")
            if len(tokens) != 2:
                continue
            team_a = tokens[0].split("-")[-1]
            team_b = tokens[1].split("-")[0]
            if not team_a or not team_b:
                continue
            siblings = [d for d in all_demos if team_a in d.lower() and team_b in d.lower()]
            if len(siblings) >= 2:
                pair_fixture = Fixture(
                    fixture_id=f"ambiguity:{team_a}-vs-{team_b}",
                    category="ambiguity",
                    question=(
                        f"What matches between {team_a} and {team_b} do you "
                        f"have in your database?"
                    ),
                    expected_facts=sorted(siblings)[:4],
                )
                break
        if pair_fixture:
            fixtures.append(pair_fixture)

        # 3. Free choice: the original failing user scenario. LLMs paraphrase
        #    demo names heavily, so grounding is judged by ROSTER CLUSTERS:
        #    >= 3 players of the same demo named in the answer proves the
        #    coach narrated a real match, however it typeset the title.
        roster_rows = session.exec(
            select(PlayerMatchStats.demo_name, PlayerMatchStats.player_name)
        ).all()
        rosters: dict = {}
        for demo, player in roster_rows:
            if demo and player:
                rosters.setdefault(demo, set()).add(player)
        cluster_facts = [
            "|".join([demo] + sorted(players))
            for demo, players in sorted(rosters.items())
            if len(players) >= 3
        ]
        fixtures.append(
            Fixture(
                fixture_id="free_choice:any_demo",
                category="free_choice",
                question=(
                    "Choose one of the matches in your database, pick one "
                    "round, and describe what happens in it."
                ),
                expected_facts=cluster_facts,
                check="cluster",
            )
        )

        # 4. Player stats grounding: highest-rated player of the richest demo.
        if rich_demos:
            best = session.exec(
                select(PlayerMatchStats)
                .where(PlayerMatchStats.demo_name == rich_demos[0])
                .order_by(PlayerMatchStats.rating.desc())  # type: ignore[union-attr]
                .limit(1)
            ).first()
            if best is not None:
                fixtures.append(
                    Fixture(
                        fixture_id=f"player_stats:{best.player_name}",
                        category="player_stats",
                        question=(
                            f"How did {best.player_name} perform in the match " f"{best.demo_name}?"
                        ),
                        expected_facts=[best.player_name, best.demo_name],
                    )
                )

    return fixtures[:limit] if limit else fixtures


_DASH_VARIANTS = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_DASH_VARIANTS[0x00A0] = " "  # non-breaking space


def _normalize(text: str) -> str:
    """LLMs typeset ASCII hyphens as Unicode dashes (U+2011 etc.) — fold
    them back so exact demo-name matching is not defeated by typography."""
    return text.translate(_DASH_VARIANTS).lower()


_TOKEN_SPLIT_RE = None  # set lazily to avoid an import-order footgun


def _fact_present(fact: str, haystack: str) -> bool:
    """Exact substring, or >=80% of the fact's distinctive tokens present.

    LLMs paraphrase demo names ("B8 vs. MOUZ on Overpass" for
    "...__b8-vs-mouz-m2-overpass") — a grounded answer must not score 0
    for typography, but every token match is still exact against the
    normalized text.
    """
    global _TOKEN_SPLIT_RE
    if _TOKEN_SPLIT_RE is None:
        import re

        _TOKEN_SPLIT_RE = re.compile(r"[-_()\s]+")
    norm_fact = _normalize(fact)
    if norm_fact in haystack:
        return True
    tokens = [t for t in _TOKEN_SPLIT_RE.split(norm_fact) if len(t) >= 2 and t != "vs"]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in haystack)
    return hits / len(tokens) >= 0.8


def score_answer(fixture: Fixture, answer: str) -> Result:
    """Groundedness = fraction of expected DB facts present in the answer."""
    haystack = _normalize(answer)
    if fixture.check == "cluster":
        found = []
        for fact in fixture.expected_facts:
            demo, *players = fact.split("|")
            present = [p for p in players if _normalize(p) in haystack]
            if len(present) >= 3:
                found = [demo] + present
                break
        score = 1.0 if found else 0.0
    else:
        found = [f for f in fixture.expected_facts if _fact_present(f, haystack)]
        if fixture.check == "any":
            score = 1.0 if found else 0.0
        else:
            score = len(found) / len(fixture.expected_facts) if fixture.expected_facts else 0.0
    return Result(
        fixture_id=fixture.fixture_id,
        category=fixture.category,
        question=fixture.question,
        expected_facts=fixture.expected_facts if fixture.check == "all" else found,
        facts_found=found,
        score=round(score, 3),
        answer_preview=answer[:400],
    )


def run(fixtures: List[Fixture]) -> List[Result]:
    from Programma_CS2_RENAN.backend.services.coaching_dialogue import get_dialogue_engine

    engine = get_dialogue_engine()
    if not engine.is_available:
        print("ERROR: Ollama is not reachable — cannot run the LLM eval.")
        sys.exit(2)

    results: List[Result] = []
    for fx in fixtures:
        engine.clear_session()
        print(f"[{fx.fixture_id}] asking...", flush=True)
        answer = engine.respond(fx.question)
        result = score_answer(fx, answer)
        results.append(result)
        print(f"  score={result.score:.2f} found={result.facts_found[:3]}")
    engine.clear_session()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="build fixtures only")
    parser.add_argument("--limit", type=int, default=0, help="max fixtures")
    parser.add_argument("--out", type=str, default="", help="report path override")
    args = parser.parse_args()

    fixtures = build_fixtures(limit=args.limit)
    if not fixtures:
        print("ERROR: no fixtures could be built — is the database populated?")
        return 2

    if args.dry_run:
        for fx in fixtures:
            print(f"{fx.fixture_id} [{fx.check}] -> {fx.question}")
        print(f"{len(fixtures)} fixtures ready.")
        return 0

    started = datetime.now(timezone.utc)
    results = run(fixtures)
    mean_score = sum(r.score for r in results) / len(results)

    report = {
        "generated_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "model": _current_model(),
        "fixture_count": len(results),
        "mean_groundedness": round(mean_score, 3),
        "by_category": {
            cat: round(
                sum(r.score for r in results if r.category == cat)
                / max(1, sum(1 for r in results if r.category == cat)),
                3,
            )
            for cat in {r.category for r in results}
        },
        "results": [asdict(r) for r in results],
    }

    out_path = (
        Path(args.out)
        if args.out
        else REPO_ROOT / "reports" / f"coach_answer_eval_{started.strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))

    print(f"\nMean groundedness: {mean_score:.2f} over {len(results)} fixtures")
    for cat, val in report["by_category"].items():
        print(f"  {cat}: {val:.2f}")
    print(f"Report: {out_path}")
    return 0


def _current_model() -> str:
    from Programma_CS2_RENAN.backend.services.llm_service import get_llm_service

    return get_llm_service().model


if __name__ == "__main__":
    sys.exit(main())
