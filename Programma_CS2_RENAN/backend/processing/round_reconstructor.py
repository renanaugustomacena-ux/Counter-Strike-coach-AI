"""
Round Reconstructor — Tick data to structured human-readable timelines.

WR-76: Bridges the gap between raw playertickstate data and the coaching LLM.
Produces structured timelines with callout positions, weapon sequences,
engagement timing, and health deltas — grounded facts the LLM can narrate
instead of hallucinating tactical details.

Usage:
    from Programma_CS2_RENAN.backend.processing.round_reconstructor import (
        RoundReconstructor, get_round_reconstructor,
    )

    reconstructor = get_round_reconstructor()
    timeline = reconstructor.reconstruct_round("demo.dem", 5, "NiKo", "de_mirage")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from sqlmodel import Session, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerTickState, RoundStats
from Programma_CS2_RENAN.core.map_callouts import get_callout
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.processing.round_reconstructor")

# Tick sampling: 128 ticks/sec, sample every ~2 seconds for position tracking
_POSITION_SAMPLE_INTERVAL = 256
# Minimum position change (world units) to consider a meaningful movement
_SIGNIFICANT_MOVEMENT = 400.0
# Maximum ticks to load per round (safety cap for performance)
_MAX_TICKS_PER_ROUND = 20_000
# CS2 tick rate
_TICK_RATE = 128

# Explicit list of what the tick data cannot tell us
_DATA_LIMITATIONS = [
    "Voice communications are not captured in demo data.",
    "Teammate callouts and team coordination context are not available.",
    "Opponent intent and off-screen information cannot be determined.",
    "Exact crosshair placement between ticks is interpolated, not precise.",
    "Audio cues (footsteps, reloads) that informed decisions are not recorded.",
]

# Weapon display name cleanup
_WEAPON_DISPLAY = {
    "weapon_ak47": "AK-47",
    "weapon_m4a1": "M4A1",
    "weapon_m4a1_silencer": "M4A1-S",
    "weapon_awp": "AWP",
    "weapon_deagle": "Desert Eagle",
    "weapon_usp_silencer": "USP-S",
    "weapon_glock": "Glock-18",
    "weapon_famas": "FAMAS",
    "weapon_galil": "Galil AR",
    "weapon_aug": "AUG",
    "weapon_sg556": "SG 553",
    "weapon_ssg08": "SSG 08 (Scout)",
    "weapon_p250": "P250",
    "weapon_tec9": "Tec-9",
    "weapon_cz75a": "CZ75-Auto",
    "weapon_fiveseven": "Five-SeveN",
    "weapon_mp9": "MP9",
    "weapon_mac10": "MAC-10",
    "weapon_ump45": "UMP-45",
    "weapon_p90": "P90",
    "weapon_mp7": "MP7",
    "weapon_bizon": "PP-Bizon",
    "weapon_mag7": "MAG-7",
    "weapon_nova": "Nova",
    "weapon_sawedoff": "Sawed-Off",
    "weapon_xm1014": "XM1014",
    "weapon_negev": "Negev",
    "weapon_m249": "M249",
    "weapon_knife": "Knife",
    "weapon_knife_t": "Knife",
    "weapon_c4": "C4",
    "weapon_hegrenade": "HE Grenade",
    "weapon_flashbang": "Flashbang",
    "weapon_smokegrenade": "Smoke",
    "weapon_molotov": "Molotov",
    "weapon_incgrenade": "Incendiary",
    "weapon_decoy": "Decoy",
    "unknown": "Unknown",
}


def _weapon_name(raw: str) -> str:
    """Convert raw weapon ID to display name."""
    return _WEAPON_DISPLAY.get(raw, raw.replace("weapon_", "").replace("_", " ").title())


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------


@dataclass
class RoundEvent:
    """A single event in a round timeline."""

    tick: int
    time_in_round: float  # seconds from round start
    event_type: str  # position_change, health_delta, weapon_switch, engagement,
    # kill, death, utility, bomb_action, scope, crouch
    description: str  # human-readable, using callout names
    details: Dict = field(default_factory=dict)


@dataclass
class RoundTimeline:
    """Structured timeline of a player's round, built from tick data."""

    player_name: str
    demo_name: str
    round_number: int
    map_name: str
    side: str  # "CT" or "T"
    outcome: str  # "won", "lost"
    survived: bool
    kills: int
    deaths: int
    damage_dealt: int
    equipment_value: int
    events: List[RoundEvent] = field(default_factory=list)
    summary: str = ""
    data_limitations: List[str] = field(default_factory=lambda: list(_DATA_LIMITATIONS))
    tick_count: int = 0  # how many ticks were available

    def format_for_llm(self) -> str:
        """Format timeline as structured text block for LLM context injection."""
        lines = []
        lines.append(
            f"ROUND TIMELINE (Round {self.round_number} — "
            f"{self.side} side, {self.outcome}, "
            f"{self.kills}K/{self.deaths}D, {self.damage_dealt} dmg, "
            f"${self.equipment_value} equipment)"
        )
        if self.summary:
            lines.append(f"Summary: {self.summary}")
        lines.append(f"Tick data points: {self.tick_count}")
        lines.append("Events:")
        for event in self.events:
            lines.append(f"  [{event.time_in_round:.1f}s] {event.description}")
        lines.append("Data limitations:")
        for lim in self.data_limitations:
            lines.append(f"  - {lim}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reconstructor
# ---------------------------------------------------------------------------


class RoundReconstructor:
    """
    Reconstructs human-readable round timelines from PlayerTickState data.

    Queries the monolith database for tick-level data and produces structured
    RoundTimeline objects that the coaching dialogue engine can inject as
    grounded LLM context.
    """

    def reconstruct_round(
        self,
        demo_name: str,
        round_number: int,
        player_name: str,
        map_name: Optional[str] = None,
    ) -> Optional[RoundTimeline]:
        """
        Reconstruct a single round timeline.

        Args:
            demo_name: Demo file identifier.
            round_number: 1-based round number.
            player_name: Player to track.
            map_name: Map identifier (e.g., "de_mirage"), or None to auto-detect.

        Returns:
            RoundTimeline with events and summary, or None if no data found.
        """
        timelines = self.reconstruct_rounds(demo_name, player_name, [round_number], map_name)
        return timelines[0] if timelines else None

    def reconstruct_rounds(
        self,
        demo_name: str,
        player_name: str,
        round_numbers: Sequence[int],
        map_name: Optional[str] = None,
    ) -> List[RoundTimeline]:
        """
        Reconstruct timelines for multiple rounds in a single DB query.

        Fetches all ticks for the player in the demo, partitions by round,
        and builds timelines. Avoids N+1 query pattern.

        If map_name is None, it is auto-detected from the first tick row.
        """
        if not round_numbers:
            return []

        db_manager = get_db_manager()
        timelines = []

        try:
            with Session(db_manager.engine) as session:
                # Fetch RoundStats for context (kills, deaths, outcome)
                round_stats_map = self._fetch_round_stats(
                    session, demo_name, player_name, round_numbers
                )

                # Fetch ticks for all requested rounds in one query
                ticks_by_round = self._fetch_ticks_by_round(
                    session, demo_name, player_name, round_numbers
                )

                # Auto-detect map_name from tick data if not provided
                effective_map = map_name
                if not effective_map:
                    for tick_list in ticks_by_round.values():
                        if tick_list:
                            effective_map = tick_list[0].map_name
                            break
                if not effective_map:
                    effective_map = "de_unknown"

                for rn in round_numbers:
                    ticks = ticks_by_round.get(rn, [])
                    rs = round_stats_map.get(rn)

                    if not ticks:
                        logger.debug(
                            "No ticks for %s round %d in %s",
                            player_name,
                            rn,
                            demo_name,
                        )
                        continue

                    timeline = self._build_timeline(
                        ticks, rs, player_name, demo_name, rn, effective_map
                    )
                    timelines.append(timeline)

        except Exception:
            logger.exception("Failed to reconstruct rounds for %s in %s", player_name, demo_name)

        return timelines

    # ------------------------------------------------------------------
    # DB queries
    # ------------------------------------------------------------------

    def _fetch_round_stats(
        self,
        session: Session,
        demo_name: str,
        player_name: str,
        round_numbers: Sequence[int],
    ) -> Dict[int, RoundStats]:
        """Fetch RoundStats for the given rounds, keyed by round_number."""
        stmt = (
            select(RoundStats)
            .where(RoundStats.demo_name == demo_name)
            .where(RoundStats.player_name == player_name)
            .where(RoundStats.round_number.in_(list(round_numbers)))
        )
        results = session.exec(stmt).all()
        return {rs.round_number: rs for rs in results}

    def _fetch_ticks_by_round(
        self,
        session: Session,
        demo_name: str,
        player_name: str,
        round_numbers: Sequence[int],
    ) -> Dict[int, List[PlayerTickState]]:
        """Fetch PlayerTickState rows partitioned by round_number."""
        stmt = (
            select(PlayerTickState)
            .where(PlayerTickState.demo_name == demo_name)
            .where(PlayerTickState.player_name == player_name)
            .where(PlayerTickState.round_number.in_(list(round_numbers)))
            .order_by(PlayerTickState.tick)
            .limit(_MAX_TICKS_PER_ROUND * len(round_numbers))
        )
        results = session.exec(stmt).all()

        by_round: Dict[int, List[PlayerTickState]] = {}
        for tick in results:
            by_round.setdefault(tick.round_number, []).append(tick)
        return by_round

    # ------------------------------------------------------------------
    # Timeline construction
    # ------------------------------------------------------------------

    def _build_timeline(
        self,
        ticks: List[PlayerTickState],
        round_stats: Optional[RoundStats],
        player_name: str,
        demo_name: str,
        round_number: int,
        map_name: str,
    ) -> RoundTimeline:
        """Build a RoundTimeline from tick data and optional RoundStats."""
        # Round metadata from RoundStats (if available)
        side = round_stats.side if round_stats else "?"
        outcome = "won" if (round_stats and round_stats.round_won) else "lost"
        kills = round_stats.kills if round_stats else 0
        deaths_count = round_stats.deaths if round_stats else 0
        damage = round_stats.damage_dealt if round_stats else 0
        equip = round_stats.equipment_value if round_stats else 0

        # Check if player survived (health > 0 at last tick)
        survived = ticks[-1].health > 0 if ticks else True

        events: List[RoundEvent] = []

        # Starting position
        first_tick = ticks[0]
        start_callout = get_callout(map_name, first_tick.pos_x, first_tick.pos_y, first_tick.pos_z)
        events.append(
            RoundEvent(
                tick=first_tick.tick,
                time_in_round=first_tick.time_in_round,
                event_type="position_change",
                description=f"Round start at {start_callout} with {_weapon_name(first_tick.active_weapon)}",
                details={
                    "callout": start_callout,
                    "weapon": first_tick.active_weapon,
                    "health": first_tick.health,
                    "armor": first_tick.armor,
                },
            )
        )

        # Process ticks for state transitions
        prev = first_tick
        last_callout = start_callout
        sample_counter = 0

        for tick in ticks[1:]:
            sample_counter += 1

            # Health delta (damage taken)
            if tick.health < prev.health and prev.health > 0:
                damage_taken = prev.health - tick.health
                callout = get_callout(map_name, tick.pos_x, tick.pos_y, tick.pos_z)
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="health_delta",
                        description=(
                            f"Took {damage_taken} damage at {callout} "
                            f"(HP: {prev.health} -> {tick.health})"
                        ),
                        details={
                            "damage": damage_taken,
                            "health_before": prev.health,
                            "health_after": tick.health,
                            "callout": callout,
                        },
                    )
                )

            # Death detection
            if prev.health > 0 and tick.health <= 0:
                callout = get_callout(map_name, prev.pos_x, prev.pos_y, prev.pos_z)
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="death",
                        description=f"Died at {callout}",
                        details={"callout": callout, "weapon_held": prev.active_weapon},
                    )
                )

            # Weapon switch
            if tick.active_weapon != prev.active_weapon and tick.health > 0:
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="weapon_switch",
                        description=(f"Switched to {_weapon_name(tick.active_weapon)}"),
                        details={
                            "from": prev.active_weapon,
                            "to": tick.active_weapon,
                        },
                    )
                )

            # Enemies visible transitions
            if tick.enemies_visible > 0 and prev.enemies_visible == 0:
                callout = get_callout(map_name, tick.pos_x, tick.pos_y, tick.pos_z)
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="engagement",
                        description=(
                            f"Spotted {tick.enemies_visible} "
                            f"enem{'y' if tick.enemies_visible == 1 else 'ies'} "
                            f"at {callout}"
                        ),
                        details={
                            "enemies": tick.enemies_visible,
                            "callout": callout,
                            "weapon": tick.active_weapon,
                            "scoped": tick.is_scoped,
                        },
                    )
                )

            # Bomb plant/defuse
            if tick.bomb_planted and not prev.bomb_planted:
                callout = get_callout(map_name, tick.pos_x, tick.pos_y, tick.pos_z)
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="bomb_action",
                        description=f"Bomb planted (player at {callout})",
                        details={"callout": callout},
                    )
                )

            # Teammates/enemies alive changes
            if tick.teammates_alive < prev.teammates_alive:
                lost = prev.teammates_alive - tick.teammates_alive
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="teammate_lost",
                        description=(
                            f"Lost {lost} teammate{'s' if lost > 1 else ''} "
                            f"({tick.teammates_alive + 1}v{tick.enemies_alive} situation)"
                        ),
                        details={
                            "teammates_alive": tick.teammates_alive,
                            "enemies_alive": tick.enemies_alive,
                        },
                    )
                )

            if tick.enemies_alive < prev.enemies_alive and prev.enemies_alive > 0:
                eliminated = prev.enemies_alive - tick.enemies_alive
                callout = get_callout(map_name, tick.pos_x, tick.pos_y, tick.pos_z)
                events.append(
                    RoundEvent(
                        tick=tick.tick,
                        time_in_round=tick.time_in_round,
                        event_type="enemy_eliminated",
                        description=(
                            f"Enemy eliminated near {callout} "
                            f"({tick.teammates_alive + 1}v{tick.enemies_alive} situation)"
                        ),
                        details={
                            "eliminated": eliminated,
                            "callout": callout,
                            "weapon": tick.active_weapon,
                            "teammates_alive": tick.teammates_alive,
                            "enemies_alive": tick.enemies_alive,
                        },
                    )
                )

            # Position sampling (every ~2 seconds for significant movement)
            if sample_counter >= _POSITION_SAMPLE_INTERVAL and tick.health > 0:
                sample_counter = 0
                callout = get_callout(map_name, tick.pos_x, tick.pos_y, tick.pos_z)
                if callout != last_callout:
                    events.append(
                        RoundEvent(
                            tick=tick.tick,
                            time_in_round=tick.time_in_round,
                            event_type="position_change",
                            description=f"Moved to {callout}",
                            details={
                                "callout": callout,
                                "crouching": tick.is_crouching,
                            },
                        )
                    )
                    last_callout = callout

            prev = tick

        # Sort events by tick (they should already be, but ensure)
        events.sort(key=lambda e: e.tick)

        # Build summary
        summary = self._build_summary(events, side, outcome, kills, deaths_count, survived)

        return RoundTimeline(
            player_name=player_name,
            demo_name=demo_name,
            round_number=round_number,
            map_name=map_name,
            side=side,
            outcome=outcome,
            survived=survived,
            kills=kills,
            deaths=deaths_count,
            damage_dealt=damage,
            equipment_value=equip,
            events=events,
            summary=summary,
            tick_count=len(ticks),
        )

    def _build_summary(
        self,
        events: List[RoundEvent],
        side: str,
        outcome: str,
        kills: int,
        deaths: int,
        survived: bool,
    ) -> str:
        """Generate a one-line summary from the event sequence."""
        parts = []

        # Starting position
        start_events = [e for e in events if e.event_type == "position_change"]
        if start_events:
            parts.append(f"Started at {start_events[0].details.get('callout', '?')}")

        # Engagements
        engagements = [e for e in events if e.event_type == "engagement"]
        if engagements:
            parts.append(f"{len(engagements)} engagement{'s' if len(engagements) > 1 else ''}")

        # Kills
        enemy_elims = [e for e in events if e.event_type == "enemy_eliminated"]
        if enemy_elims:
            parts.append(f"{len(enemy_elims)} kill{'s' if len(enemy_elims) > 1 else ''}")

        # Outcome
        if survived:
            parts.append(f"survived ({outcome})")
        else:
            death_events = [e for e in events if e.event_type == "death"]
            if death_events:
                parts.append(f"died at {death_events[0].details.get('callout', '?')} ({outcome})")
            else:
                parts.append(outcome)

        return ", ".join(parts) + "." if parts else f"Round {outcome}."


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------

_reconstructor: Optional[RoundReconstructor] = None


def get_round_reconstructor() -> RoundReconstructor:
    """Get or create the singleton RoundReconstructor."""
    global _reconstructor  # noqa: PLW0603
    if _reconstructor is None:
        _reconstructor = RoundReconstructor()
    return _reconstructor
