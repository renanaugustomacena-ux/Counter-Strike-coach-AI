#!/usr/bin/env python3
"""
Mine strategy labels from per-match shard databases (Path B).

Reads 270 match_*.db shards directly, classifies each round into strategy
labels across 5 families (economy/individual/setpiece/rotation/playbook),
and populates CoachingExperience with strategy_label set.

Shard data: matchtickstate (44 cols, ~2M rows/shard) + match_event_state
(12 event types, ~5-9K rows/shard). Event round_number is broken (always 1);
events are mapped to real rounds via tick-range bisection.

Usage:
    python tools/mine_shard_strategies.py --limit 3          # test on 3 shards
    python tools/mine_shard_strategies.py --dry-run           # count, no insert
    python tools/mine_shard_strategies.py                     # full run
"""

import argparse
import bisect
import hashlib
import json
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.core.tick_rate import DEFAULT_TICK_RATE  # noqa: E402

DEFAULT_SHARDS_DIR = Path(
    "/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS/match_data"
)
DB_PATH = PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"

KNOWN_MAPS = {
    "de_mirage": "mirage",
    "de_dust2": "dust2",
    "de_inferno": "inferno",
    "de_nuke": "nuke",
    "de_overpass": "overpass",
    "de_ancient": "ancient",
    "de_anubis": "anubis",
    "de_vertigo": "vertigo",
}
PRO_CONFIDENCE = 0.7
# Strategy windows in SECONDS — converted per shard from
# match_metadata.tick_rate (26-TICK: the old *_TICKS constants baked in a
# 64-tick assumption, halving every window on 128-tick shards).
TRADE_WINDOW_SECONDS = 2.0
WINDOW_20S = 20.0
WINDOW_30S = 30.0
WINDOW_45S = 45.0
_DEFAULT_TICK_RATE = float(DEFAULT_TICK_RATE)

# Bomb site centroids from K-means clustering (80 shards, ≥30 plants, ≥1500u separation)
# Convention: sorted by center_x (lower x = "a", higher x = "b")
BOMB_SITE_CENTROIDS: dict[str, dict[str, tuple[float, float]]] = {
    "dust2": {"a": (-1454, 2185), "b": (917, 2217)},
    "inferno": {"a": (482, 2578), "b": (1937, 327)},
    "mirage": {"a": (-1721, 172), "b": (-430, -1772)},
}


def _weapon_cat(weapon_str: str) -> str:
    w = weapon_str.lower()
    if "awp" in w:
        return "awp"
    if "deag" in w:
        return "deagle"
    if any(s in w for s in ("fiveseven", "cz75", "tec9")):
        return "upgraded_pistol"
    if any(s in w for s in ("galil", "famas")):
        return "budget_rifle"
    if any(s in w for s in ("ak47", "m4a1", "m4a4", "sg556", "aug")):
        return "rifle"
    if any(s in w for s in ("mac10", "mp9", "mp7", "mp5", "ump", "p90", "bizon")):
        return "smg"
    if any(s in w for s in ("glock", "hkp2000", "usp", "p250", "elite")):
        return "pistol"
    return "other"


def _classify_bomb_site(map_name: str, pos_x: float, pos_y: float) -> str | None:
    centroids = BOMB_SITE_CENTROIDS.get(map_name)
    if not centroids:
        return None
    dist_a = (pos_x - centroids["a"][0]) ** 2 + (pos_y - centroids["a"][1]) ** 2
    dist_b = (pos_x - centroids["b"][0]) ** 2 + (pos_y - centroids["b"][1]) ** 2
    return "a" if dist_a < dist_b else "b"


def _same_half(rn_a: int, rn_b: int) -> bool:
    if rn_a <= 12 and rn_b <= 12:
        return True
    if 13 <= rn_a <= 24 and 13 <= rn_b <= 24:
        return True
    if rn_a >= 25 and rn_b >= 25:
        return (rn_a - 25) // 3 == (rn_b - 25) // 3
    return False


@dataclass
class RoundData:
    shard_stem: str
    map_name: str
    round_number: int
    start_tick: int
    end_tick: int
    # Per-shard rate from match_metadata (26-TICK) — windows derive from it.
    tick_rate: float = _DEFAULT_TICK_RATE
    winner: Optional[str] = None  # "CT" or "T"
    players: dict = field(default_factory=dict)  # name → PlayerSnap
    deaths: list = field(default_factory=list)  # (tick, killer, k_team, victim, v_team, weapon)
    utility: list = field(default_factory=list)  # (tick, event_type, player, team)
    bomb_planted: bool = False
    bomb_defused: bool = False
    bomb_plant_tick: int = 0
    bomb_planter: str = ""
    bomb_defuser: str = ""
    bomb_plant_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class PlayerSnap:
    name: str
    team: str  # "CT" or "TERRORIST"
    equipment_value: int = 0
    money: int = 0
    active_weapon: str = ""
    health: int = 100
    has_helmet: bool = False
    has_defuser: bool = False
    teammates_alive: int = 5
    enemies_alive: int = 5
    team_economy: int = 0


@dataclass
class LabeledExperience:
    strategy_label: str
    granularity: str  # "team" or "player"
    player_name: Optional[str]
    team: str
    side: str  # "CT" or "T"
    action: str
    outcome: str
    delta: float
    map_name: str
    round_phase: str
    equipment_tier: str
    round_number: int
    shard_stem: str


# ── Data extraction ──────────────────────────────────────────────────


def load_shard(shard_path: Path) -> list[RoundData]:
    conn = sqlite3.connect(str(shard_path), timeout=10)
    conn.execute("PRAGMA query_only = ON")
    try:
        return _extract_rounds(conn, shard_path.stem)
    finally:
        conn.close()


def _extract_rounds(conn: sqlite3.Connection, shard_stem: str) -> list[RoundData]:
    # Round boundaries
    bounds_rows = conn.execute(
        "SELECT round_number, MIN(tick), MAX(tick) FROM matchtickstate "
        "GROUP BY round_number ORDER BY round_number"
    ).fetchall()
    if not bounds_rows:
        return []

    map_row = conn.execute("SELECT DISTINCT map_name FROM matchtickstate LIMIT 1").fetchone()
    raw_map = map_row[0] if map_row else "unknown"
    map_name = KNOWN_MAPS.get(raw_map, raw_map.replace("de_", ""))

    # 26-TICK: per-shard rate from match_metadata; validated to [32, 256].
    tick_rate = _DEFAULT_TICK_RATE
    try:
        tr_row = conn.execute("SELECT tick_rate FROM match_metadata LIMIT 1").fetchone()
        if tr_row and tr_row[0] and 32.0 <= float(tr_row[0]) <= 256.0:
            tick_rate = float(tr_row[0])
        else:
            print(
                f"  WARN {shard_stem}: match_metadata tick_rate={tr_row[0] if tr_row else None!r}"
                f" unusable — windows assume {_DEFAULT_TICK_RATE}"
            )
    except sqlite3.OperationalError:
        print(f"  WARN {shard_stem}: no match_metadata — windows assume {_DEFAULT_TICK_RATE}")

    rounds: dict[int, RoundData] = {}
    starts = []
    round_nums = []
    for rn, start_tick, end_tick in bounds_rows:
        rounds[rn] = RoundData(
            shard_stem=shard_stem,
            map_name=map_name,
            round_number=rn,
            start_tick=start_tick,
            end_tick=end_tick,
            tick_rate=tick_rate,
        )
        starts.append(start_tick)
        round_nums.append(rn)

    # Economy snapshot: first tick per player per round
    economy_sql = """
        SELECT t.round_number, t.player_name, t.team, t.equipment_value, t.money,
               t.active_weapon, t.health, t.has_helmet, t.has_defuser,
               t.teammates_alive, t.enemies_alive, t.team_economy
        FROM matchtickstate t
        INNER JOIN (
            SELECT round_number, player_name, MIN(tick) as min_tick
            FROM matchtickstate GROUP BY round_number, player_name
        ) f ON t.round_number = f.round_number
            AND t.player_name = f.player_name AND t.tick = f.min_tick
    """
    for row in conn.execute(economy_sql).fetchall():
        rn = row[0]
        if rn not in rounds:
            continue
        snap = PlayerSnap(
            name=row[1],
            team=row[2],
            equipment_value=row[3] or 0,
            money=row[4] or 0,
            active_weapon=row[5] or "",
            health=row[6] or 100,
            has_helmet=bool(row[7]),
            has_defuser=bool(row[8]),
            teammates_alive=row[9] or 5,
            enemies_alive=row[10] or 5,
            team_economy=row[11] or 0,
        )
        rounds[rn].players[snap.name] = snap

    # Events: map to correct round via tick bisection
    has_events = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='match_event_state'"
    ).fetchone()
    if has_events:
        events = conn.execute(
            "SELECT tick, event_type, player_name, player_team, "
            "victim_name, victim_team, weapon, damage "
            "FROM match_event_state ORDER BY tick"
        ).fetchall()

        for tick, etype, pname, pteam, vname, vteam, weapon, dmg in events:
            idx = bisect.bisect_right(starts, tick) - 1
            if idx < 0 or idx >= len(round_nums):
                continue
            rn = round_nums[idx]
            rd = rounds[rn]

            if etype == "player_death":
                rd.deaths.append((tick, pname, pteam, vname, vteam, weapon))
            elif etype in (
                "grenade_thrown",
                "flash_detonate",
                "smoke_start",
                "smoke_end",
                "molotov_start",
                "he_detonate",
            ):
                rd.utility.append((tick, etype, pname, pteam))
            elif etype == "bomb_planted":
                rd.bomb_planted = True
                rd.bomb_plant_tick = tick
                rd.bomb_planter = pname or ""
            elif etype == "bomb_defused":
                rd.bomb_defused = True
                rd.bomb_defuser = pname or ""

    # Extract bomb plant positions for site classification
    for rd in rounds.values():
        if rd.bomb_planted and rd.bomb_plant_tick > 0:
            pos_rows = conn.execute(
                "SELECT pos_x, pos_y FROM matchtickstate "
                "WHERE tick = ? AND team = 'TERRORIST' AND is_alive = 1",
                (rd.bomb_plant_tick,),
            ).fetchall()
            valid = [(r[0], r[1]) for r in pos_rows if r[0] != 0]
            if valid:
                cx = sum(x for x, _ in valid) / len(valid)
                cy = sum(y for _, y in valid) / len(valid)
                rd.bomb_plant_pos = (cx, cy, 0.0)

    # Determine round winners
    for rd in rounds.values():
        ct_dead = sum(1 for _, _, _, _, vt, _ in rd.deaths if vt == "CT")
        t_dead = sum(1 for _, _, _, _, vt, _ in rd.deaths if vt == "TERRORIST")

        if ct_dead >= 5:
            rd.winner = "T"
        elif t_dead >= 5:
            rd.winner = "CT"
        elif rd.bomb_planted and not rd.bomb_defused:
            rd.winner = "T"
        elif rd.bomb_planted and rd.bomb_defused:
            rd.winner = "CT"
        elif not rd.bomb_planted:
            rd.winner = "CT"  # timeout → CT wins

    return list(rounds.values())


# ── Strategy classifiers ─────────────────────────────────────────────


def _classify_round_phase(round_number: int, avg_equip: float) -> str:
    if round_number in (1, 13):
        return "pistol"
    if avg_equip < 2000:
        return "eco"
    if avg_equip < 4000:
        return "force"
    return "full_buy"


def _equip_tier(equip: int) -> str:
    if equip < 2000:
        return "eco"
    if equip < 4000:
        return "force"
    return "full"


def _side_label(team: str) -> str:
    return "CT" if team == "CT" else "T"


def classify_round(
    rd: RoundData, prev_rounds: list[RoundData] | None = None
) -> list[LabeledExperience]:
    labels: list[LabeledExperience] = []
    if not rd.players:
        return labels

    # 26-TICK: windows derived from the shard's real rate, never a baked 64.
    trade_window = int(TRADE_WINDOW_SECONDS * rd.tick_rate)
    w20 = int(WINDOW_20S * rd.tick_rate)
    w30 = int(WINDOW_30S * rd.tick_rate)
    w45 = int(WINDOW_45S * rd.tick_rate)

    teams: dict[str, list[PlayerSnap]] = defaultdict(list)
    for p in rd.players.values():
        teams[p.team].append(p)

    for team_name, players in teams.items():
        if not players:
            continue
        side = _side_label(team_name)
        avg_equip = sum(p.equipment_value for p in players) / len(players)
        round_phase = _classify_round_phase(rd.round_number, avg_equip)
        team_won = (
            rd.winner == side
            or (rd.winner == "T" and team_name == "TERRORIST")
            or (rd.winner == "CT" and team_name == "CT")
        )
        outcome = "round_win" if team_won else "round_loss"

        def _emit(
            label: str,
            action: str,
            out: str,
            delta: float,
            granularity: str = "team",
            player: str | None = None,
        ):
            labels.append(
                LabeledExperience(
                    strategy_label=label,
                    granularity=granularity,
                    player_name=player,
                    team=team_name,
                    side=side,
                    action=action,
                    outcome=out,
                    delta=delta,
                    map_name=rd.map_name,
                    round_phase=round_phase,
                    equipment_tier=_equip_tier(int(avg_equip)),
                    round_number=rd.round_number,
                    shard_stem=rd.shard_stem,
                )
            )

        # ── Economy family (team-level) ──
        equip_values = [p.equipment_value for p in players]
        max_equip = max(equip_values)
        min_equip = min(equip_values)

        if rd.round_number in (1, 13):
            _emit("economy.pistol_default", "pistol_buy", outcome, 0.05 if team_won else -0.05)
        elif rd.round_number in (2, 14):
            _emit("economy.bonus_round", "post_pistol", outcome, 0.10 if team_won else -0.05)
        elif avg_equip >= 4000:
            _emit("economy.full_buy", "full_buy", outcome, 0.05 if team_won else -0.10)
        elif avg_equip >= 2000:
            _emit("economy.force_buy", "force_buy", outcome, 0.15 if team_won else -0.05)
        elif avg_equip < 1500 and max_equip < 2000:
            _emit("economy.team_save", "team_save", outcome, -0.05 if team_won else 0.0)
        else:
            _emit("economy.eco_round", "eco_round", outcome, 0.20 if team_won else -0.02)

        if max_equip > 4000 and (sum(1 for e in equip_values if e < 2000) >= 3):
            _emit("economy.hero_buy", "hero_buy", outcome, 0.15 if team_won else -0.08)
        if min_equip < 2000 and max_equip > 3500 and len(players) >= 4:
            diff = max_equip - min_equip
            if diff > 2500:
                _emit("economy.half_buy", "half_buy", outcome, 0.10 if team_won else -0.05)

        # ── Individual family (player-level) ──
        team_deaths = [(t, k, kt, v, vt, w) for t, k, kt, v, vt, w in rd.deaths if vt == team_name]
        team_kills = [(t, k, kt, v, vt, w) for t, k, kt, v, vt, w in rd.deaths if kt == team_name]

        if rd.deaths:
            first_death = rd.deaths[0]
            first_kill_tick = first_death[0]

            # Entry frag: killer of the first death
            if first_death[2] == team_name:
                _emit("individual.entry_frag", "entry_frag", "kill", 0.15, "player", first_death[1])
            # Opening death: victim of the first death
            if first_death[4] == team_name:
                _emit(
                    "individual.opening_death",
                    "entry_frag",
                    "death",
                    -0.15,
                    "player",
                    first_death[3],
                )

        # Per-player kill counts + trades
        player_kills: dict[str, list] = defaultdict(list)
        for t, k, kt, v, vt, w in rd.deaths:
            if kt == team_name:
                player_kills[k].append((t, v, vt, w))

        for pname, kills in player_kills.items():
            kill_count = len(kills)
            if kill_count >= 3:
                _emit(
                    "individual.multi_kill",
                    "multi_kill",
                    f"{kill_count}k_{'win' if team_won else 'loss'}",
                    0.20 + 0.05 * (kill_count - 3),
                    "player",
                    pname,
                )
            if kill_count >= 5:
                _emit("individual.ace", "ace", outcome, 0.40, "player", pname)

            for kill_tick, victim, _, weapon in kills:
                if weapon and "awp" in weapon.lower():
                    _emit("individual.awp_aggression", "awp_kill", "kill", 0.10, "player", pname)
                    break

        # Trade kills: kill within trade_window of a teammate death
        sorted_deaths = sorted(rd.deaths, key=lambda x: x[0])
        for i, (tick, killer, k_team, victim, v_team, _) in enumerate(sorted_deaths):
            if k_team != team_name:
                continue
            for j in range(max(0, i - 5), i):
                prev_tick, _, _, prev_victim, prev_v_team, _ = sorted_deaths[j]
                if prev_v_team == team_name and (tick - prev_tick) <= trade_window:
                    _emit("individual.trade_kill", "trade_kill", "traded", 0.10, "player", killer)
                    break

        # Clutch: last alive on team in 1vN, won
        if team_won and len(team_deaths) >= 4 and len(players) == 5:
            alive_players = set(p.name for p in players) - set(
                v for _, _, _, v, vt, _ in rd.deaths if vt == team_name
            )
            if len(alive_players) == 1:
                clutcher = alive_players.pop()
                enemies_left = 5 - sum(1 for _, _, _, _, vt, _ in rd.deaths if vt != team_name)
                if enemies_left <= 0:
                    enemies_left = 1
                enemy_count_at_clutch = max(
                    1,
                    5
                    - len(
                        [
                            d
                            for d in rd.deaths
                            if d[4] != team_name and d[0] <= max(d2[0] for d2 in team_deaths)
                        ]
                    ),
                )
                if enemy_count_at_clutch >= 2:
                    _emit(
                        "individual.clutch_play",
                        f"clutch_1v{enemy_count_at_clutch}",
                        "round_win",
                        0.30,
                        "player",
                        clutcher,
                    )

        # ── Utility-based labels ──
        team_util = [u for u in rd.utility if u[3] == team_name]
        if len(team_util) >= 5 and team_won:
            _emit("setpiece.utility_heavy", "utility_execute", "round_win", 0.10)

        flash_events = [(t, p) for t, et, p, pt in team_util if et == "flash_detonate"]
        smoke_events = [(t, p) for t, et, p, pt in team_util if et == "smoke_start"]
        molly_events = [(t, p) for t, et, p, pt in team_util if et == "molotov_start"]

        for flash_tick, flasher in flash_events:
            for kill_tick, killer, kt, _, vt, _ in rd.deaths:
                if kt == team_name and vt != team_name and 0 < (kill_tick - flash_tick) <= 64:
                    _emit(
                        "individual.flash_assist",
                        "flash_assist",
                        "kill_after_flash",
                        0.08,
                        "player",
                        flasher,
                    )
                    break

        if molly_events and team_won:
            _emit("individual.molotov_deny", "molotov_usage", "area_denial", 0.05)

        if smoke_events and len(smoke_events) >= 2 and team_won:
            _emit("individual.smoke_execute", "smoke_usage", "site_take", 0.05)

        # ── Setpiece family ──
        if side == "T" and rd.deaths:
            first_engage_tick = rd.deaths[0][0]
            round_duration = rd.end_tick - rd.start_tick
            if round_duration > 0 and (first_engage_tick - rd.start_tick) / round_duration < 0.25:
                _emit("setpiece.fast_rush", "fast_rush", outcome, 0.12 if team_won else -0.08)

        if side == "T" and team_won and rd.bomb_planted:
            if len(team_util) >= 3:
                _emit("setpiece.site_execute", "coordinated_execute", "bomb_plant", 0.15)

        # ── Eco upset (cross-team) ──
        if avg_equip < 2000 and team_won and rd.round_number not in (1, 13):
            _emit("economy.eco_win", "eco_upset", "round_win", 0.30)

        # Anti-eco: full buy vs eco opponent
        other_team = "CT" if team_name == "TERRORIST" else "TERRORIST"
        other_players = teams.get(other_team, [])
        if other_players:
            other_avg = sum(p.equipment_value for p in other_players) / len(other_players)
            if avg_equip >= 4000 and other_avg < 2000 and rd.round_number not in (1, 13):
                _emit("economy.anti_eco", "anti_eco_buy", outcome, 0.02 if team_won else -0.25)

        # ── Additional setpiece labels ──
        if side == "T" and rd.deaths:
            first_engage_tick = rd.deaths[0][0]
            round_duration = rd.end_tick - rd.start_tick
            if round_duration > 0:
                engage_ratio = (first_engage_tick - rd.start_tick) / round_duration
                if engage_ratio > 0.50 and len(team_util) <= 2:
                    _emit(
                        "setpiece.slow_default",
                        "default_play",
                        outcome,
                        0.05 if team_won else -0.05,
                    )
                if len(team_util) <= 1 and team_won and rd.bomb_planted:
                    _emit("setpiece.dry_execute", "no_utility_take", "bomb_plant", 0.12)

        if side == "CT" and len(team_util) <= 1 and team_won:
            _emit("setpiece.default_hold", "passive_hold", "round_win", 0.05)

        if side == "CT" and rd.bomb_planted and team_won:
            _emit("setpiece.retake", "site_retake", "defuse", 0.20)

        # ── Rotation family ──
        if side == "CT" and team_kills:
            first_ct_kill = min(team_kills, key=lambda x: x[0])
            round_duration = rd.end_tick - rd.start_tick
            if round_duration > 0:
                engage_pct = (first_ct_kill[0] - rd.start_tick) / round_duration
                if engage_pct < 0.20:
                    _emit(
                        "rotation.ct_aggression",
                        "aggressive_push",
                        "early_kill",
                        0.12,
                        "player",
                        first_ct_kill[1],
                    )

        # Exit frag: kill during round loss
        if not team_won and team_kills:
            last_kill = max(team_kills, key=lambda x: x[0])
            _emit("individual.exit_frag", "exit_frag", "round_loss", 0.03, "player", last_kill[1])

        # HE grenade kills
        he_events = [(t, p) for t, et, p, pt in team_util if et == "he_detonate"]
        for he_tick, thrower in he_events:
            for kill_tick, killer, kt, victim, vt, weapon in rd.deaths:
                if vt != team_name and abs(kill_tick - he_tick) <= 32:
                    _emit("individual.nade_kill", "he_grenade", "kill", 0.08, "player", thrower)
                    break

        # ── Map-qualified playbook labels ──
        m = rd.map_name
        if side == "T" and team_won and rd.bomb_planted:
            _emit(f"playbook.{m}_t_bomb_win", "map_t_execute", "bomb_win", 0.10)
        if side == "CT" and team_won and rd.bomb_defused:
            _emit(f"playbook.{m}_ct_defuse", "map_ct_retake", "defuse_win", 0.15)
        if side == "CT" and team_won and not rd.bomb_planted:
            _emit(f"playbook.{m}_ct_denial", "map_ct_hold", "plant_denied", 0.08)
        if avg_equip < 2000 and team_won and rd.round_number not in (1, 13):
            _emit(f"playbook.{m}_eco_upset", "map_eco_play", "eco_win", 0.25)

        # ────────────────────────────────────────────────────────────────
        # Tier 1 extensions — 85 new labels across 5 families
        # ────────────────────────────────────────────────────────────────

        # ── Economy extensions ──
        for p in players:
            wcat = _weapon_cat(p.active_weapon)
            has_armor = p.has_helmet or p.equipment_value > (
                {"awp": 4750, "rifle": 2700, "deagle": 700}.get(wcat, 500) + 200
            )

            if wcat in ("rifle", "awp") and not has_armor and p.equipment_value < 4500:
                _emit(
                    "economy.glass_cannon",
                    "glass_cannon",
                    outcome,
                    0.12 if team_won else -0.10,
                    "player",
                    p.name,
                )

            if wcat == "smg":
                smg_kills = sum(
                    1 for _, k, kt, _, _, _ in rd.deaths if k == p.name and kt == team_name
                )
                if smg_kills >= 2:
                    _emit(
                        "economy.smg_farming",
                        "smg_farm",
                        f"{smg_kills}k",
                        0.08 * smg_kills,
                        "player",
                        p.name,
                    )

            if wcat == "deagle" and avg_equip < 2500:
                _emit(
                    "economy.deagle_force",
                    "deagle_force",
                    outcome,
                    0.15 if team_won else -0.05,
                    "player",
                    p.name,
                )

            if wcat == "upgraded_pistol" and has_armor:
                _emit(
                    "economy.upgraded_pistol",
                    "upgraded_pistol_buy",
                    outcome,
                    0.10 if team_won else -0.05,
                    "player",
                    p.name,
                )

            if wcat == "budget_rifle":
                _emit(
                    "economy.galil_famas_buy",
                    "budget_rifle_buy",
                    outcome,
                    0.08 if team_won else -0.05,
                    "player",
                    p.name,
                )

            if wcat == "pistol" and has_armor and rd.round_number not in (1, 13):
                _emit(
                    "economy.pistol_armor",
                    "pistol_armor_buy",
                    outcome,
                    0.10 if team_won else -0.05,
                    "player",
                    p.name,
                )

        awp_holders = [p for p in players if _weapon_cat(p.active_weapon) == "awp"]
        if len(awp_holders) >= 2:
            _emit("economy.double_awp", "double_awp_setup", outcome, 0.08 if team_won else -0.15)

        if not team_won:
            for p in players:
                survived = p.name not in [v for _, _, _, v, vt, _ in rd.deaths if vt == team_name]
                if survived and _weapon_cat(p.active_weapon) == "awp":
                    _emit("economy.awp_save", "awp_save", "survived_loss", 0.05, "player", p.name)

        if rd.round_number in (2, 14) and 2000 <= avg_equip < 4000:
            _emit(
                "economy.second_round_force",
                "2nd_round_force",
                outcome,
                0.12 if team_won else -0.08,
            )

        # ── Individual extensions ──
        dead_set = {v for _, _, _, v, vt, _ in rd.deaths if vt == team_name}
        for p in players:
            pk = player_kills.get(p.name, [])
            p_kill_count = len(pk)

            if not team_won and p.name not in dead_set and p.equipment_value > 4500:
                _emit(
                    "individual.weapon_save", "weapon_save", "survived_loss", 0.05, "player", p.name
                )

            if rd.round_number in (1, 13) and p_kill_count >= 5:
                _emit("individual.pistol_ace", "pistol_ace", "ace", 0.35, "player", p.name)

            if p_kill_count >= 4:
                _emit("individual.quad_kill", "quad_kill", outcome, 0.25, "player", p.name)

            if p_kill_count >= 2:
                kill_ticks = [t for t, _, _, _ in pk]
                kill_ticks.sort()
                for ki in range(len(kill_ticks) - 1):
                    if kill_ticks[ki + 1] - kill_ticks[ki] <= trade_window:
                        _emit(
                            "individual.double_kill", "double_kill", outcome, 0.12, "player", p.name
                        )
                        break

            if (
                not team_won
                and p.name in dead_set
                and p_kill_count == 0
                and p.equipment_value > 3000
            ):
                _emit(
                    "individual.no_kill_round",
                    "no_kill_death",
                    "round_loss",
                    -0.08,
                    "player",
                    p.name,
                )

        # Traded deaths
        for i_d, (tick_d, _, _, victim_d, vteam_d, _) in enumerate(sorted_deaths):
            if vteam_d != team_name:
                continue
            for j_d in range(i_d + 1, min(i_d + 6, len(sorted_deaths))):
                next_t, next_k, next_kt, _, _, _ = sorted_deaths[j_d]
                if next_kt == team_name and (next_t - tick_d) <= trade_window:
                    _emit(
                        "individual.traded_death",
                        "was_traded",
                        "death_traded",
                        0.03,
                        "player",
                        victim_d,
                    )
                    break

        # Bomb plant / defuse identification
        if rd.bomb_planted and rd.bomb_planter:
            planter_team = next(
                (p.team for p in rd.players.values() if p.name == rd.bomb_planter), None
            )
            if planter_team == team_name:
                _emit(
                    "individual.bomb_plant",
                    "bomb_plant",
                    "planted",
                    0.08,
                    "player",
                    rd.bomb_planter,
                )
        if rd.bomb_defused and rd.bomb_defuser:
            defuser_team = next(
                (p.team for p in rd.players.values() if p.name == rd.bomb_defuser), None
            )
            if defuser_team == team_name:
                _emit(
                    "individual.bomb_defuse",
                    "bomb_defuse",
                    "defused",
                    0.12,
                    "player",
                    rd.bomb_defuser,
                )

        # Post-plant / retake kills
        if rd.bomb_planted and rd.bomb_plant_tick > 0:
            for _, killer, kt, _, vt, _ in rd.deaths:
                if kt == team_name and vt != team_name:
                    if side == "T":
                        _emit(
                            "individual.post_plant_kill",
                            "post_plant_frag",
                            "kill",
                            0.08,
                            "player",
                            killer,
                        )
                        break
                    elif side == "CT":
                        _emit(
                            "individual.retake_kill", "retake_frag", "kill", 0.10, "player", killer
                        )
                        break

        # Clutch win/loss (refined — uses dead_set from above)
        if len(dead_set) >= 4 and len(players) == 5:
            alive = {p.name for p in players} - dead_set
            if len(alive) == 1:
                clutcher = next(iter(alive))
                if team_won:
                    _emit(
                        "individual.clutch_win", "clutch_win", "round_win", 0.30, "player", clutcher
                    )
                else:
                    _emit(
                        "individual.clutch_loss",
                        "clutch_loss",
                        "round_loss",
                        -0.10,
                        "player",
                        clutcher,
                    )

        # ── Setpiece extensions ──
        round_duration_ticks = rd.end_tick - rd.start_tick
        if round_duration_ticks > 0:
            team_util_count = len(team_util)

            if team_util_count >= 5:
                first_util_tick = min(t for t, _, _, _ in team_util)
                if (first_util_tick - rd.start_tick) <= w20:
                    _emit(
                        "setpiece.utility_stack",
                        "heavy_utility_open",
                        outcome,
                        0.12 if team_won else -0.05,
                    )

            if rd.deaths:
                first_death_tick = rd.deaths[0][0]
                if (first_death_tick - rd.start_tick) > w45:
                    _emit("setpiece.timeplay", "clock_burn", outcome, 0.08 if team_won else -0.05)

            late_util = [u for u in team_util if (u[0] - rd.start_tick) > w30]
            if len(late_util) >= 3 and rd.bomb_planted and side == "T":
                _emit(
                    "setpiece.delayed_execute", "late_execute", outcome, 0.10 if team_won else -0.05
                )

            if (
                side == "T"
                and avg_equip < 1500
                and rd.deaths
                and (rd.deaths[0][0] - rd.start_tick) < w20
            ):
                _emit("setpiece.eco_rush", "eco_rush", outcome, 0.18 if team_won else -0.03)

            if (
                other_players
                and sum(p.equipment_value for p in other_players) / len(other_players) < 1500
                and team_util_count >= 4
            ):
                _emit(
                    "setpiece.anti_eco_stack",
                    "anti_eco_utility",
                    outcome,
                    0.03 if team_won else -0.15,
                )

            util_ticks = sorted(t for t, _, _, _ in team_util)
            for ui in range(len(util_ticks) - 1):
                if util_ticks[ui + 1] - util_ticks[ui] <= 128:
                    _emit("setpiece.double_utility_lineup", "coordinated_throw", outcome, 0.06)
                    break

        # Post-plant setpiece labels
        if rd.bomb_planted and rd.bomb_plant_tick > 0:
            post_plant_mollies = [
                u
                for u in team_util
                if u[1] == "molotov_start" and u[0] > rd.bomb_plant_tick and u[3] == team_name
            ]
            if post_plant_mollies and side == "T":
                _emit(
                    "setpiece.post_plant_molotov",
                    "molly_on_bomb",
                    outcome,
                    0.10 if team_won else -0.03,
                )

            post_plant_util_ct = [
                u for u in rd.utility if u[0] > rd.bomb_plant_tick and u[3] != team_name
            ]
            if len(post_plant_util_ct) >= 2 and side == "T":
                _emit("setpiece.retake_utility", "ct_retake_util", outcome, 0.08)

            t_kills_post = [d for d in rd.deaths if d[0] > rd.bomb_plant_tick and d[2] == team_name]
            t_deaths_post = [
                d for d in rd.deaths if d[0] > rd.bomb_plant_tick and d[4] == team_name
            ]
            if side == "T" and rd.bomb_planted:
                if len(t_kills_post) >= 1 and len(t_deaths_post) == 0:
                    _emit(
                        "setpiece.post_plant_aggressive",
                        "post_plant_push",
                        outcome,
                        0.10 if team_won else -0.05,
                    )
                elif len(t_kills_post) == 0 and team_won:
                    _emit("setpiece.post_plant_passive", "post_plant_hold", "round_win", 0.08)

        # ── Rotation extensions ──
        if not team_won and avg_equip >= 2000:
            surviving = {p.name for p in players} - dead_set
            if len(surviving) >= 3:
                _emit("rotation.save_round", "save_decision", "round_loss", 0.02)

        # ── Playbook extensions (6 new × 9 maps) ──
        if side == "T" and team_won and not rd.bomb_planted:
            _emit(f"playbook.{m}_t_elimination", "t_elim_win", "elimination", 0.12)
        if team_won and 2000 <= avg_equip <= 4000 and rd.round_number not in (1, 13):
            _emit(f"playbook.{m}_force_buy_win", "force_buy_win", "round_win", 0.18)
        if rd.round_number in (1, 13):
            if side == "T" and team_won:
                _emit(f"playbook.{m}_pistol_t", "pistol_t_win", "round_win", 0.15)
            if side == "CT" and team_won:
                _emit(f"playbook.{m}_pistol_ct", "pistol_ct_win", "round_win", 0.15)
        if (
            side == "CT"
            and team_won
            and other_players
            and sum(p.equipment_value for p in other_players) / len(other_players) < 2000
            and rd.round_number not in (1, 13)
        ):
            _emit(f"playbook.{m}_anti_eco_hold", "anti_eco_ct_win", "round_win", 0.05)
        if rd.round_number > 30:
            _emit(
                f"playbook.{m}_overtime_round",
                "overtime_play",
                outcome,
                0.10 if team_won else -0.10,
            )

        # ────────────────────────────────────────────────────────────────
        # Tier 2 extensions — cross-round, site-specific, timing, context
        # ────────────────────────────────────────────────────────────────

        # ── T2: Cross-round economy (needs prev_rounds, same-half only) ──
        team_hist: list[dict] = []
        if prev_rounds:
            for pr in prev_rounds:
                if not _same_half(pr.round_number, rd.round_number):
                    continue
                pr_teams_d: dict[str, list] = defaultdict(list)
                for p in pr.players.values():
                    pr_teams_d[p.team].append(p)
                if team_name in pr_teams_d:
                    ps = pr_teams_d[team_name]
                    pr_side = _side_label(team_name)
                    won = (
                        pr.winner == pr_side
                        or (pr.winner == "T" and team_name == "TERRORIST")
                        or (pr.winner == "CT" and team_name == "CT")
                    )
                    avg_eq = sum(p.equipment_value for p in ps) / len(ps) if ps else 0
                    team_hist.append({"round": pr.round_number, "won": won, "avg_equip": avg_eq})
            team_hist.sort(key=lambda h: h["round"])

        if len(team_hist) >= 3:
            if all(not h["won"] for h in team_hist[-3:]):
                _emit("economy.loss_streak_3", "loss_streak", outcome, -0.12)

        if len(team_hist) >= 5:
            if all(not h["won"] for h in team_hist[-5:]):
                _emit("economy.loss_streak_5", "loss_streak", outcome, -0.20)

        if len(team_hist) >= 2 and avg_equip >= 4000:
            if all(h["avg_equip"] < 2000 for h in team_hist[-2:]):
                _emit("economy.reset_buy", "reset_purchase", outcome, 0.08)

        if len(team_hist) >= 1 and 2000 <= avg_equip <= 4000:
            if 2000 <= team_hist[-1]["avg_equip"] <= 4000:
                _emit("economy.consecutive_force", "force_again", outcome, 0.05)

        if len(team_hist) >= 3:
            if all(h["avg_equip"] < 1500 for h in team_hist[-3:]):
                _emit("economy.economy_collapse", "eco_collapse", outcome, -0.15)

        if len(team_hist) >= 1 and avg_equip >= 4000:
            if team_hist[-1]["avg_equip"] < 2000:
                _emit("economy.economy_recovery", "eco_recovery", outcome, 0.10)

        if len(team_hist) >= 1 and avg_equip < 2000 and rd.round_number not in (1, 13):
            if team_hist[-1]["won"]:
                _emit("economy.save_after_win", "save_win", outcome, 0.03)

        if (
            len(team_hist) >= 1
            and avg_equip < 2000
            and team_hist[-1]["avg_equip"] < 2000
            and rd.round_number not in (1, 2, 13, 14)
        ):
            _emit("economy.double_eco", "double_eco", outcome, -0.08)

        # ── T2: Site-specific execution ──
        if rd.bomb_planted and rd.bomb_plant_pos != (0.0, 0.0, 0.0) and side == "T":
            site = _classify_bomb_site(rd.map_name, rd.bomb_plant_pos[0], rd.bomb_plant_pos[1])
            if site:
                _emit(
                    f"setpiece.{site}_site_execute",
                    f"{site}_site_take",
                    outcome,
                    0.10 if team_won else -0.05,
                )

        # ── T2: Round context / pressure (half-scoped) ──
        if rd.round_number >= 8 and team_hist:
            team_wins_n = sum(1 for h in team_hist if h["won"])
            opp_wins_n = len(team_hist) - team_wins_n
            if abs(team_wins_n - opp_wins_n) <= 2 and len(team_hist) >= 6:
                _emit("individual.close_half_kill", "pressure_kill", outcome, 0.12)

        if len(team_hist) >= 5:
            total_wins = sum(1 for h in team_hist if h["won"])
            total_losses = len(team_hist) - total_wins
            if total_losses - total_wins >= 5 and team_won:
                _emit("individual.half_comeback_kill", "comeback_win", "round_win", 0.18)

        if rd.round_number in (2, 14) and not team_won:
            if team_hist and team_hist[-1]["won"]:
                _emit("economy.bonus_loss", "bonus_round_loss", "round_loss", -0.12)

        # ── T2: Timing-based ──
        round_dur = rd.end_tick - rd.start_tick
        if rd.deaths and round_dur > 0:
            sorted_d = sorted(rd.deaths, key=lambda d: d[0])
            t_first = sorted_d[0][0] - rd.start_tick

            if t_first < round_dur * 0.2 and sorted_d[0][2] == team_name:
                _emit("setpiece.early_aggression", "early_kill", outcome, 0.08)

            if round_dur < w20 and rd.round_number not in (1, 13):
                _emit("setpiece.fast_close", "fast_round", outcome, 0.10 if team_won else -0.08)

        if rd.bomb_planted and rd.bomb_plant_tick > 0 and side == "T" and round_dur > 0:
            plant_t = rd.bomb_plant_tick - rd.start_tick
            if plant_t > w45:
                _emit("setpiece.late_execute", "late_plant", outcome, 0.10 if team_won else -0.05)
            elif w20 <= plant_t <= w45:
                _emit("setpiece.mid_round_plant", "mid_plant", outcome, 0.05 if team_won else -0.03)

        # ── T2: Death trading patterns ──
        if rd.deaths:
            sorted_d = sorted(rd.deaths, key=lambda d: d[0])
            team_victim_deaths = [(d[0], d[3]) for d in sorted_d if d[4] == team_name]
            team_kill_ticks = [d[0] for d in sorted_d if d[2] == team_name]
            for dtick, victim in team_victim_deaths:
                if not any(0 < kt - dtick <= trade_window for kt in team_kill_ticks):
                    _emit("individual.untraded_death", "untraded", "death", -0.08, "player", victim)
                    break

            if len(sorted_d) >= 2:
                fd, sd = sorted_d[0], sorted_d[1]
                if fd[4] == team_name and sd[2] == team_name and sd[0] - fd[0] <= trade_window:
                    _emit("individual.first_blood_trade", "opening_trade", outcome, 0.10)

        # ── T2: Utility efficiency ──
        team_util_t2 = [u for u in rd.utility if u[3] == team_name]
        if len(team_util_t2) >= 8:
            _emit("setpiece.utility_flood", "utility_heavy", outcome, 0.06)

        if rd.bomb_planted and side == "T" and len(team_util_t2) <= 1:
            _emit("setpiece.dry_take", "dry_execute", outcome, 0.12 if team_won else -0.05)

        if rd.bomb_planted and side == "T" and rd.bomb_plant_tick > 0:
            t_deaths_pre_plant = sum(
                1 for d in rd.deaths if d[4] == team_name and d[0] <= rd.bomb_plant_tick
            )
            if t_deaths_pre_plant == 0:
                _emit("setpiece.all_alive_plant", "clean_plant", outcome, 0.08)

        # ── T2: Economy disparity ──
        if other_players:
            opp_avg = sum(p.equipment_value for p in other_players) / len(other_players)
            if opp_avg > avg_equip * 2 and avg_equip > 0:
                _emit(
                    "economy.massive_disadvantage",
                    "eco_vs_full",
                    outcome,
                    0.15 if team_won else -0.05,
                )
            if avg_equip > 0 and opp_avg > 0 and abs(avg_equip - opp_avg) < 1000:
                _emit("economy.economic_parity", "mirror_buy", outcome, 0.05 if team_won else -0.05)
            if team_won and avg_equip < 2000 and rd.round_number not in (1, 13):
                _emit("economy.thrifty_win", "thrifty_win", "round_win", 0.18)

        # ── T2: Individual extended ──
        if avg_equip < 2000 and rd.round_number not in (1, 13):
            eco_kills_by_player: dict[str, int] = defaultdict(int)
            for d in rd.deaths:
                if d[2] == team_name:
                    eco_kills_by_player[d[1]] += 1
            for pn, kc in eco_kills_by_player.items():
                if kc >= 3:
                    _emit("individual.eco_hero", "eco_hero_kills", outcome, 0.20, "player", pn)
                    break

        if rd.deaths:
            sorted_d = sorted(rd.deaths, key=lambda d: d[0])
            if len(sorted_d) >= 2 and sorted_d[0][2] == team_name and sorted_d[1][2] == team_name:
                _emit("individual.opening_duo", "opening_pair", outcome, 0.12)

        alive_set = {p.name for p in players} - dead_set
        if len(alive_set) == 1 and not team_won:
            survivor = next(iter(alive_set))
            if any(d[1] == survivor and d[2] == team_name for d in rd.deaths):
                _emit("individual.round_saver", "save_kill", "round_loss", 0.05, "player", survivor)

        if rd.round_number in (1, 13):
            pistol_kills_by: dict[str, int] = defaultdict(int)
            for d in rd.deaths:
                if d[2] == team_name:
                    pistol_kills_by[d[1]] += 1
            for pn, kc in pistol_kills_by.items():
                if kc >= 3:
                    _emit("individual.pistol_hero", "pistol_hero", outcome, 0.15, "player", pn)
                    break

        team_death_count = sum(1 for d in rd.deaths if d[4] == team_name)
        if team_death_count == 4 and team_won and len(players) == 5:
            _emit("individual.last_alive_win", "clutch_win", "round_win", 0.18)

        flash_ev_t2 = [u for u in rd.utility if u[1] == "flash_detonate" and u[3] == team_name]
        for d in rd.deaths:
            if d[2] == team_name:
                for fe in flash_ev_t2:
                    if 0 < d[0] - fe[0] <= trade_window and d[1] != fe[2]:
                        _emit(
                            "individual.flash_kill",
                            "flash_assist_kill",
                            outcome,
                            0.08,
                            "player",
                            d[1],
                        )
                        break
                else:
                    continue
                break

        if rd.deaths:
            if any("knife" in (d[5] or "").lower() for d in rd.deaths if d[2] == team_name):
                _emit("individual.knife_round", "knife_kill", outcome, 0.02)

        if avg_equip < 2000 and rd.round_number not in (1, 13):
            if any(_weapon_cat(p.active_weapon) == "deagle" for p in players):
                _emit("economy.deagle_eco", "deagle_force", outcome, 0.08)

    return labels


# ── Bulk insert ──────────────────────────────────────────────────────


def _compute_context_hash(map_name: str, round_phase: str, side: str, equipment_tier: str) -> str:
    key = f"{map_name}:{side}:{round_phase}:unknown"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _load_embedder():
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model, 384
    except ImportError:
        return None, 100


def bulk_insert(experiences: list[LabeledExperience], dry_run: bool = False) -> dict:
    import base64

    import numpy as np

    stats = {"total": len(experiences), "inserted": 0, "skipped_dup": 0, "errors": 0}
    if dry_run or not experiences:
        return stats

    model, embed_dim = _load_embedder()

    print(f"  Batch-embedding {len(experiences)} query texts...")
    t0 = time.time()
    query_texts = []
    for exp in experiences:
        ctx_str = f"{exp.map_name} {exp.round_phase} {exp.side} {exp.equipment_tier}"
        query_texts.append(f"{ctx_str} {exp.action} {exp.outcome}")

    if model is not None:
        embeddings = model.encode(
            query_texts, convert_to_numpy=True, batch_size=256, show_progress_bar=True
        )
    else:

        def _fallback(text: str) -> np.ndarray:
            vec = np.zeros(embed_dim, dtype=np.float32)
            for word in text.lower().split():
                h = int(hashlib.md5(word.encode(), usedforsecurity=False).hexdigest()[:8], 16)
                idx = h % embed_dim
                sign = 1.0 if (h // embed_dim) % 2 == 0 else -1.0
                vec[idx] += sign
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            return vec

        embeddings = np.array([_fallback(t) for t in query_texts])
    print(f"  Embedding done in {time.time() - t0:.1f}s")

    def _serialize(vec: np.ndarray) -> str:
        return base64.b64encode(vec.astype(np.float32).tobytes()).decode("ascii")

    from datetime import datetime, timezone

    print(f"  Building + deduplicating records...")
    rows = []
    seen_hashes = set()
    now = datetime.now(timezone.utc).isoformat()

    for i, exp in enumerate(experiences):
        context_hash = _compute_context_hash(
            exp.map_name,
            exp.round_phase,
            exp.side,
            exp.equipment_tier,
        )
        dedup_key = hashlib.md5(
            f"{context_hash}:{exp.action}:{exp.outcome}:{exp.strategy_label}:{exp.player_name}:{exp.shard_stem}:{exp.round_number}".encode(),
            usedforsecurity=False,
        ).hexdigest()
        if dedup_key in seen_hashes:
            stats["skipped_dup"] += 1
            continue
        seen_hashes.add(dedup_key)

        game_state = json.dumps(
            {
                "round_number": exp.round_number,
                "shard": exp.shard_stem,
                "side": exp.side,
                "equipment_tier": exp.equipment_tier,
                **({"player_name": exp.player_name} if exp.player_name else {}),
            }
        )

        rows.append(
            (
                context_hash,
                exp.map_name,
                exp.round_phase,
                exp.side,
                game_state,
                exp.action,
                exp.outcome,
                exp.delta,
                PRO_CONFIDENCE,
                0,  # usage_count
                exp.player_name,
                exp.shard_stem,
                _serialize(embeddings[i]),
                exp.strategy_label,
                now,
                False,
                0.0,  # created_at, outcome_validated, effectiveness_score
                0,
                0,
                25.0,
                25.0 / 3.0,  # times_advice_given/followed, mu_skill, sigma_skill
                0,
                0,  # times_retrieved, times_validated
            )
        )

    print(f"  Inserting {len(rows)} records into CoachingExperience...")
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    inserted = 0
    for row in rows:
        try:
            conn.execute(
                """INSERT INTO coachingexperience
                   (context_hash, map_name, round_phase, side, game_state_json,
                    action_taken, outcome, delta_win_prob, confidence, usage_count,
                    pro_player_name, source_demo, embedding, strategy_label,
                    created_at, outcome_validated, effectiveness_score,
                    times_advice_given, times_advice_followed, mu_skill, sigma_skill,
                    times_retrieved, times_validated)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                row,
            )
            inserted += 1
        except sqlite3.IntegrityError:
            stats["skipped_dup"] += 1
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 5:
                print(f"    ERROR: {e}")

        if inserted % 1000 == 0 and inserted > 0:
            conn.commit()
            print(f"    {inserted} inserted...")

    conn.commit()
    conn.close()
    stats["inserted"] = inserted
    return stats


# ── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine strategy labels from match shards")
    parser.add_argument("--shards-dir", type=Path, default=DEFAULT_SHARDS_DIR)
    parser.add_argument("--limit", type=int, default=0, help="Process only N shards (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Classify but don't insert")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete existing miner rows before inserting (avoids duplicates)",
    )
    args = parser.parse_args()

    shards = sorted(args.shards_dir.glob("match_*.db"))
    if args.limit > 0:
        shards = shards[: args.limit]

    print(f"=== Shard Strategy Miner ===")
    print(f"  Shards dir: {args.shards_dir}")
    print(f"  Shards to process: {len(shards)}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    all_labels: list[LabeledExperience] = []
    shard_stats = {"processed": 0, "skipped": 0, "total_rounds": 0}
    t_start = time.time()

    for i, shard_path in enumerate(shards, 1):
        try:
            rounds = load_shard(shard_path)
            if not rounds:
                shard_stats["skipped"] += 1
                continue

            shard_labels = []
            sorted_rounds = sorted(rounds, key=lambda r: r.round_number)
            for idx, rd in enumerate(sorted_rounds):
                shard_labels.extend(classify_round(rd, prev_rounds=sorted_rounds[:idx] or None))

            all_labels.extend(shard_labels)
            shard_stats["processed"] += 1
            shard_stats["total_rounds"] += len(rounds)

            if i % 10 == 0 or i == len(shards):
                elapsed = time.time() - t_start
                rate = i / elapsed if elapsed > 0 else 0
                print(
                    f"  [{i}/{len(shards)}] {shard_path.stem}: "
                    f"{len(rounds)} rounds, {len(shard_labels)} labels "
                    f"({rate:.1f} shards/s)"
                )

        except Exception as e:
            print(f"  ERROR [{shard_path.stem}]: {e}")
            shard_stats["skipped"] += 1

    # Summary
    label_counts = Counter(exp.strategy_label for exp in all_labels)
    family_counts = Counter(exp.strategy_label.split(".")[0] for exp in all_labels)

    print(f"\n=== Mining Summary ===")
    print(f"  Shards processed: {shard_stats['processed']}")
    print(f"  Shards skipped: {shard_stats['skipped']}")
    print(f"  Total rounds: {shard_stats['total_rounds']}")
    print(f"  Total labels mined: {len(all_labels)}")
    print(f"  Distinct strategy labels: {len(label_counts)}")
    print(f"\n  By family:")
    for fam, count in sorted(family_counts.items()):
        print(f"    {fam}: {count}")
    print(f"\n  By label (top 30):")
    for label, count in label_counts.most_common(30):
        print(f"    {label}: {count}")

    if args.dry_run:
        print(f"\n  DRY RUN — no records inserted.")
        return

    # Insert
    if args.fresh:
        print(f"\n=== Truncating existing miner rows ===")
        _conn = sqlite3.connect(str(DB_PATH), timeout=30)
        _conn.execute("PRAGMA journal_mode=WAL")
        # Only THIS miner's rows carry strategy_label; a blanket DELETE
        # also destroyed mine_coaching_experience's records while the
        # message claimed "miner rows".
        old_count = _conn.execute(
            "SELECT COUNT(*) FROM coachingexperience WHERE strategy_label IS NOT NULL"
        ).fetchone()[0]
        _conn.execute("DELETE FROM coachingexperience WHERE strategy_label IS NOT NULL")
        _conn.commit()
        _conn.close()
        print(f"  Deleted {old_count} strategy-labeled rows (other experiences preserved)")

    print(f"\n=== Inserting ===")
    stats = bulk_insert(all_labels, dry_run=args.dry_run)
    print(f"\n=== Done ===")
    print(f"  Inserted: {stats['inserted']}")
    print(f"  Duplicates skipped: {stats['skipped_dup']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Wall time: {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
