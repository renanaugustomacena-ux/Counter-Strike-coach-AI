"""
Trade Kill Detection Engine — Identifies trade kills from demo death events.

A trade kill occurs when a player is killed within a short time window after
they killed an opponent, and the retaliating killer is a teammate of the
original victim. This measures team responsiveness and positioning discipline.

Algorithm (derived from cstat-main reference, adapted for demoparser2):
  For each kill K at tick T:
    Look backward in time for kills by the victim
    If victim killed a teammate of K's killer within TRADE_WINDOW_TICKS:
      Mark K as a trade kill
      Mark the original victim as "was traded"

Reference: fusion_plan.md Proposal 1
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.trade_kill_detector")

# Trade window in seconds; computed as ticks at runtime based on tick rate.
TRADE_WINDOW_S: float = 3.0
DEFAULT_TICK_RATE: int = 64
TRADE_WINDOW_TICKS: int = int(TRADE_WINDOW_S * DEFAULT_TICK_RATE)


@dataclass
class TradeKillResult:
    """Result of trade kill analysis for a single match."""

    total_kills: int = 0
    trade_kills: int = 0
    players_traded: int = 0  # Deaths that were traded by teammates
    trade_details: List[Dict] = field(default_factory=list)

    @property
    def trade_kill_ratio(self) -> float:
        return self.trade_kills / max(1, self.total_kills)

    @property
    def was_traded_ratio(self) -> float:
        return self.players_traded / max(1, self.total_kills)


def build_team_roster(parser) -> Dict[str, int]:
    """
    Build a player_name -> team_num mapping from tick data.

    Uses early-match ticks to determine team assignments.
    team_num values: 2 and 3 represent the two competing teams.

    Args:
        parser: demoparser2.DemoParser instance.

    Returns:
        Dict mapping lowercase player name to team number.
    """
    try:
        ticks = pd.DataFrame(parser.parse_ticks(["player_name", "team_num"]))
        if ticks.empty or "team_num" not in ticks.columns:
            return {}

        # Resolve player name column (may be "player_name" or "name")
        p_col = next((c for c in ["player_name", "name"] if c in ticks.columns), None)
        if not p_col:
            logger.warning("No player name column in tick data (columns: %s)", list(ticks.columns))
            return {}
        if p_col != "player_name":
            ticks = ticks.rename(columns={p_col: "player_name"})

        # Use early ticks for stable team assignment
        early = ticks[ticks["tick"] < ticks["tick"].quantile(0.1)]
        if early.empty:
            early = ticks

        roster = {}
        for name, group in early.groupby("player_name"):
            name_str = str(name).strip()
            if not name_str:
                continue
            mode_result = group["team_num"].mode()
            if mode_result.empty:
                continue
            team = int(mode_result.iloc[0])
            if team in (2, 3):
                roster[name_str.lower()] = team

        logger.info("Team roster built: %s players across 2 teams", len(roster))
        return roster

    except Exception as e:
        logger.warning("Failed to build team roster: %s", e)
        return {}


def get_round_boundaries(parser) -> List[int]:
    """
    Extract round-end tick boundaries from demo.

    Returns:
        Sorted list of round-end ticks. Prepend 0 as the match start.
    """
    try:
        events = parser.parse_events(["round_end"])
        if not events:
            return [0]
        df = events[0][1] if isinstance(events[0], tuple) else pd.DataFrame(events)
        if df.empty or "tick" not in df.columns:
            return [0]
        boundaries = sorted([0] + df["tick"].tolist())
        return boundaries
    except Exception:
        logger.debug("Round boundary extraction failed, using fallback [0]", exc_info=True)
        return [0]


def assign_round_numbers(death_ticks: pd.Series, round_boundaries: List[int]) -> pd.Series:
    """
    Assign a round number to each death based on tick boundaries.

    Args:
        death_ticks: Series of tick values from death events.
        round_boundaries: Sorted list of round boundary ticks.

    Returns:
        Series of round numbers (1-indexed).
    """
    import numpy as np

    boundaries_arr = np.array(round_boundaries)
    rounds = np.searchsorted(boundaries_arr, death_ticks.values, side="right")
    return pd.Series(rounds, index=death_ticks.index)


def detect_trade_kills(
    deaths_df: pd.DataFrame,
    team_roster: Dict[str, int],
    trade_window: Optional[int] = None,
    tick_rate: int = DEFAULT_TICK_RATE,
) -> TradeKillResult:
    """
    Detect trade kills from a DataFrame of player_death events.

    Algorithm:
      For each kill K at tick T in round R:
        Look backward in the SAME ROUND for kills by the victim
        If victim killed a teammate of K's killer within [T - window, T]:
          Mark K as trade_kill
          Mark victim's original target as was_traded

    Args:
        deaths_df: DataFrame with columns: tick, attacker_name, user_name, round_num
        team_roster: Dict mapping lowercase player name to team number
        trade_window: Maximum tick gap for a trade. Computed from tick_rate if None.
        tick_rate: Server tick rate (default 64). Used to compute trade_window.

    Returns:
        TradeKillResult with all trade kill data.
    """
    if trade_window is None:
        trade_window = int(TRADE_WINDOW_S * tick_rate)

    result = TradeKillResult()

    if deaths_df.empty or not team_roster:
        return result

    # Verify required columns before access
    if "attacker_name" not in deaths_df.columns or "user_name" not in deaths_df.columns:
        logger.warning(
            "Death DataFrame missing required columns (have: %s)", list(deaths_df.columns)
        )
        return result

    # Normalize names for matching
    df = deaths_df.copy()
    df["attacker_lower"] = df["attacker_name"].astype(str).str.strip().str.lower()
    df["victim_lower"] = df["user_name"].astype(str).str.strip().str.lower()

    # Sort by tick for temporal ordering
    df = df.sort_values("tick").reset_index(drop=True)

    result.total_kills = len(df)

    # Track which deaths were traded
    traded_indices = set()
    trade_kill_indices = set()

    for i, kill in df.iterrows():
        killer = kill["attacker_lower"]
        victim = kill["victim_lower"]
        tick = kill["tick"]
        round_num = kill.get("round_num", 0)

        # Skip if killer or victim not in roster (spectators, world damage, etc.)
        if killer not in team_roster or victim not in team_roster:
            continue

        killer_team = team_roster[killer]
        victim_team = team_roster[victim]

        # Skip team kills
        if killer_team == victim_team:
            continue

        # Look backward for kills where the VICTIM was the killer
        # (i.e., the victim of this kill had previously killed someone)
        for j in range(i - 1, -1, -1):
            prior = df.iloc[j]
            prior_tick = prior["tick"]

            # Stop searching if outside time window
            if tick - prior_tick >= trade_window:  # M-05: inclusive boundary
                break

            # Must be same round
            if prior.get("round_num", 0) != round_num:
                break

            prior_killer = prior["attacker_lower"]
            prior_victim = prior["victim_lower"]

            # Check: Was the current victim the killer in a prior event?
            # And was the prior victim a teammate of the current killer?
            if prior_killer == victim and prior_victim in team_roster:
                prior_victim_team = team_roster[prior_victim]
                if prior_victim_team == killer_team:
                    # This IS a trade kill
                    trade_kill_indices.add(i)
                    traded_indices.add(j)

                    result.trade_details.append(
                        {
                            "trade_tick": tick,
                            "trade_killer": killer,
                            "original_killer": victim,
                            "original_victim": prior_victim,
                            "original_tick": prior_tick,
                            "response_ticks": tick - prior_tick,
                            "round": round_num,
                        }
                    )
                    break  # Only count the most recent trade opportunity

    result.trade_kills = len(trade_kill_indices)
    result.players_traded = len(traded_indices)

    logger.info(  # F6-09: %s format instead of f-string
        "Trade kill analysis: %s/%s kills were trades (%.1f%%), %s deaths traded",
        result.trade_kills,
        result.total_kills,
        result.trade_kill_ratio * 100,
        result.players_traded,
    )

    return result


def get_player_trade_stats(
    result: TradeKillResult,
    team_roster: Dict[str, int],
) -> Dict[str, Dict[str, float]]:
    """
    Aggregate trade kill statistics per player.

    Args:
        result: TradeKillResult from detect_trade_kills().
        team_roster: Player-to-team mapping.

    Returns:
        Dict mapping player name to their trade statistics:
          trade_kills, times_traded, avg_response_ticks, trade_kill_ratio
    """
    player_stats: Dict[str, Dict] = {}

    # Initialize for all known players
    for name in team_roster:
        player_stats[name] = {
            "trade_kills": 0,
            "times_traded": 0,  # Their death was avenged
            "total_response_ticks": 0,
            "trade_kill_count": 0,
        }

    for detail in result.trade_details:
        trader = detail["trade_killer"]
        traded_player = detail["original_victim"]
        ticks = detail["response_ticks"]

        if trader in player_stats:
            player_stats[trader]["trade_kills"] += 1
            player_stats[trader]["total_response_ticks"] += ticks
            player_stats[trader]["trade_kill_count"] += 1

        if traded_player in player_stats:
            player_stats[traded_player]["times_traded"] += 1

    # Compute averages
    for name, stats in player_stats.items():
        count = stats.pop("trade_kill_count")
        stats["avg_response_ticks"] = stats.pop("total_response_ticks") / max(1, count)

    return player_stats


def analyze_demo_trades(parser) -> Tuple[TradeKillResult, Dict[str, Dict[str, float]]]:
    """
    Full trade kill analysis pipeline for a demo.

    This is the main entry point — call with a demoparser2.DemoParser instance.

    Args:
        parser: demoparser2.DemoParser instance (already constructed).

    Returns:
        Tuple of (TradeKillResult, per_player_stats dict).
    """
    # Step 1: Build team roster from tick data
    roster = build_team_roster(parser)
    if not roster:
        logger.warning("Could not build team roster — skipping trade kill analysis")
        return TradeKillResult(), {}

    # Step 2: Parse death events
    try:
        events = parser.parse_events(["player_death"])
        if not events:
            return TradeKillResult(), {}
        deaths_df = events[0][1] if isinstance(events[0], tuple) else pd.DataFrame(events)
        if deaths_df.empty:
            return TradeKillResult(), {}
    except Exception as e:
        logger.error("Failed to parse player_death events: %s", e)
        return TradeKillResult(), {}

    # Step 3: Assign round numbers
    round_boundaries = get_round_boundaries(parser)
    deaths_df["round_num"] = assign_round_numbers(deaths_df["tick"], round_boundaries)

    # Verify required columns exist before trade kill detection
    required_cols = {"attacker_name", "user_name", "tick"}
    missing = required_cols - set(deaths_df.columns)
    if missing:
        logger.warning("Death events missing columns for trade detection: %s", missing)
        return TradeKillResult(), {}

    # Step 4: Detect trade kills (DS-07: use actual tick_rate from demo header)
    try:
        header = parser.parse_header()
        tick_rate = int(float(header.get("tick_rate", DEFAULT_TICK_RATE) or DEFAULT_TICK_RATE))
    except Exception:
        tick_rate = DEFAULT_TICK_RATE
    result = detect_trade_kills(deaths_df, roster, tick_rate=tick_rate)

    # Step 5: Per-player aggregation
    per_player = get_player_trade_stats(result, roster)

    return result, per_player
