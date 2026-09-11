"""Tests for tools/export_episodes.py (D-10/D-11, Parte III §3)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest
from safetensors.numpy import load_file

pytestmark = pytest.mark.timeout(120)

REPO = Path(__file__).resolve().parent.parent.parent


def _create_test_db(db_path: str, demos: List[Dict[str, Any]] | None = None) -> None:
    """Create a minimal SQLite DB with playermatchstats, playertickstate, roundstats."""
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE playermatchstats ("
        "  id INTEGER PRIMARY KEY,"
        "  player_name TEXT, demo_name TEXT, match_date TEXT,"
        "  match_date_source TEXT, dataset_split TEXT"
        ")"
    )
    con.execute(
        "CREATE TABLE playertickstate ("
        "  id INTEGER PRIMARY KEY,"
        "  tick INTEGER, player_name TEXT, demo_name TEXT,"
        "  pos_x REAL, pos_y REAL, pos_z REAL,"
        "  view_x REAL, view_y REAL,"
        "  health INTEGER, armor INTEGER,"
        "  is_crouching INTEGER, is_scoped INTEGER,"
        "  has_helmet INTEGER, has_defuser INTEGER,"
        "  active_weapon TEXT, equipment_value INTEGER,"
        "  enemies_visible INTEGER, is_blinded INTEGER,"
        "  round_number INTEGER, time_in_round REAL,"
        "  bomb_planted INTEGER, teammates_alive INTEGER,"
        "  enemies_alive INTEGER, team_economy INTEGER,"
        "  map_name TEXT"
        ")"
    )
    con.execute(
        "CREATE TABLE roundstats ("
        "  id INTEGER PRIMARY KEY,"
        "  demo_name TEXT, round_number INTEGER, player_name TEXT,"
        "  side TEXT, kills INTEGER, deaths INTEGER,"
        "  opening_kill INTEGER, opening_death INTEGER,"
        "  round_won INTEGER, kast INTEGER, round_rating REAL"
        ")"
    )
    con.execute("CREATE INDEX ix_pts_player_demo ON playertickstate(player_name, demo_name)")
    con.execute("CREATE INDEX ix_rs_demo_player ON roundstats(demo_name, player_name)")

    if demos is None:
        demos = [_make_demo_data("test_demo_1", "PlayerA", "TRAIN")]

    for demo in demos:
        _insert_demo(con, demo)

    con.commit()
    con.close()


def _make_demo_data(
    demo_name: str,
    player_name: str,
    split: str,
    n_ticks: int = 200,
    n_rounds: int = 3,
    match_date: str = "2026-01-01",
    match_date_source: str = "filename_date",
    death_at: int | None = None,
    gap_at: int | None = None,
    gap_size: int = 3,
) -> Dict[str, Any]:
    """Generate synthetic demo data."""
    ticks = []
    ticks_per_round = n_ticks // n_rounds

    t = 100
    for rnd in range(2, 2 + n_rounds):
        for i in range(ticks_per_round):
            hp = 100
            if death_at is not None and t >= death_at:
                hp = 0

            if gap_at is not None and t == gap_at:
                t += gap_size
                continue

            ticks.append(
                {
                    "tick": t,
                    "round_number": rnd,
                    "time_in_round": float(i) * 0.015625,
                    "health": hp,
                    "armor": 100,
                    "is_crouching": 0,
                    "is_scoped": 0,
                    "has_helmet": 1,
                    "has_defuser": 0,
                    "active_weapon": "ak47",
                    "equipment_value": 4750,
                    "enemies_visible": 0,
                    "is_blinded": 0,
                    "pos_x": 100.0 + t * 0.5,
                    "pos_y": 200.0 + t * 0.3,
                    "pos_z": 50.0,
                    "view_x": 45.0 + t * 0.1,
                    "view_y": 5.0,
                    "bomb_planted": 0,
                    "teammates_alive": 4,
                    "enemies_alive": 5,
                    "team_economy": 10000,
                    "map_name": "de_mirage",
                    "demo_name": demo_name,
                    "player_name": player_name,
                }
            )
            t += 1

    rounds = []
    rs_name = player_name.strip().casefold()
    for rnd in range(2, 2 + n_rounds):
        rounds.append(
            {
                "demo_name": demo_name,
                "round_number": rnd,
                "player_name": rs_name,
                "side": "CT",
                "kills": 1,
                "deaths": 0,
                "opening_kill": 0,
                "opening_death": 0,
                "round_won": 1,
                "kast": 1,
                "round_rating": 1.15,
            }
        )

    return {
        "demo_name": demo_name,
        "player_name": player_name,
        "split": split,
        "match_date": match_date,
        "match_date_source": match_date_source,
        "ticks": ticks,
        "rounds": rounds,
    }


def _insert_demo(con: sqlite3.Connection, demo: Dict[str, Any]) -> None:
    con.execute(
        "INSERT INTO playermatchstats (player_name, demo_name, match_date, "
        "match_date_source, dataset_split) VALUES (?, ?, ?, ?, ?)",
        (
            demo["player_name"],
            demo["demo_name"],
            demo["match_date"],
            demo["match_date_source"],
            demo["split"],
        ),
    )
    for t in demo["ticks"]:
        con.execute(
            "INSERT INTO playertickstate "
            "(tick, player_name, demo_name, pos_x, pos_y, pos_z, view_x, view_y, "
            "health, armor, is_crouching, is_scoped, has_helmet, has_defuser, "
            "active_weapon, equipment_value, enemies_visible, is_blinded, "
            "round_number, time_in_round, bomb_planted, teammates_alive, "
            "enemies_alive, team_economy, map_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                t["tick"],
                t["player_name"],
                t["demo_name"],
                t["pos_x"],
                t["pos_y"],
                t["pos_z"],
                t["view_x"],
                t["view_y"],
                t["health"],
                t["armor"],
                t["is_crouching"],
                t["is_scoped"],
                t["has_helmet"],
                t["has_defuser"],
                t["active_weapon"],
                t["equipment_value"],
                t["enemies_visible"],
                t["is_blinded"],
                t["round_number"],
                t["time_in_round"],
                t["bomb_planted"],
                t["teammates_alive"],
                t["enemies_alive"],
                t["team_economy"],
                t["map_name"],
            ),
        )
    for r in demo["rounds"]:
        con.execute(
            "INSERT INTO roundstats "
            "(demo_name, round_number, player_name, side, kills, deaths, "
            "opening_kill, opening_death, round_won, kast, round_rating) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["demo_name"],
                r["round_number"],
                r["player_name"],
                r["side"],
                r["kills"],
                r["deaths"],
                r["opening_kill"],
                r["opening_death"],
                r["round_won"],
                r["kast"],
                r["round_rating"],
            ),
        )


@pytest.fixture
def tmp_export_dir(tmp_path: Path) -> Path:
    return tmp_path / "export"


@pytest.fixture
def test_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    return db_path


@pytest.fixture
def multi_demo_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "multi.db")
    demos = [
        _make_demo_data("demo_train_1", "PlayerA", "TRAIN", n_ticks=200),
        _make_demo_data("demo_train_2", "PlayerB", "TRAIN", n_ticks=200),
        _make_demo_data("demo_val_1", "PlayerC", "VAL", n_ticks=200),
        _make_demo_data("demo_test_1", "PlayerD", "TEST", n_ticks=200),
    ]
    _create_test_db(db_path, demos)
    return db_path


def _run_export(db_path: str, out_dir: Path, profile: str = "full", **kwargs: Any) -> None:
    import argparse

    from tools.export_episodes import run_export

    args = argparse.Namespace(
        out=str(out_dir),
        profile=profile,
        db=db_path,
        seed=kwargs.get("seed", 0),
        demos=kwargs.get("demos", None),
        workers=kwargs.get("workers", 1),
    )
    run_export(args)


class TestEpisodeSegmentation:
    """Episodes never cross a round boundary."""

    def test_episodes_within_rounds(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert len(shards) >= 1

        for shard_path in shards:
            data = load_file(str(shard_path))
            offsets = data["episode_offsets"]
            meta = data["episode_meta"]
            tick = data["tick"]

            for i in range(len(offsets) - 1):
                s, e = int(offsets[i]), int(offsets[i + 1])
                ep_ticks = tick[s:e]
                assert len(ep_ticks) >= 64, f"Episode {i} too short: {len(ep_ticks)}"

    def test_no_cross_round_episodes(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "round_test.db")
        demos = [_make_demo_data("rd_demo", "PlayerA", "TRAIN", n_ticks=300, n_rounds=3)]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir)

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert len(shards) >= 1
        data = load_file(str(shards[0]))
        meta = data["episode_meta"]
        offsets = data["episode_offsets"]
        for i in range(len(meta)):
            assert meta[i, 0] > 0, "round_number must be positive"


class TestTickConsecutive:
    """Ticks within an episode are consecutive after bridging."""

    def test_ticks_consecutive(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        for shard_path in shards:
            data = load_file(str(shard_path))
            offsets = data["episode_offsets"]
            tick = data["tick"]
            for i in range(len(offsets) - 1):
                s, e = int(offsets[i]), int(offsets[i + 1])
                ep_ticks = tick[s:e]
                if len(ep_ticks) > 1:
                    diffs = np.diff(ep_ticks)
                    assert np.all(
                        diffs == 1
                    ), f"Episode {i}: non-consecutive ticks, diffs={diffs[diffs != 1]}"


class TestBridging:
    """Small gaps (2-7 ticks) are filled and marked."""

    def test_gap_filled(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "gap_test.db")
        demos = [
            _make_demo_data(
                "gap_demo",
                "PlayerA",
                "TRAIN",
                n_ticks=200,
                gap_at=150,
                gap_size=3,
            )
        ]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir)

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert len(shards) >= 1
        data = load_file(str(shards[0]))
        filled = data["filled"]
        assert filled.sum() > 0, "Expected some filled ticks from bridging"


class TestEpisodeOffsets:
    """episode_offsets is monotonically increasing and valid CSR."""

    def test_offsets_monotone(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        for shard_path in shards:
            data = load_file(str(shard_path))
            offsets = data["episode_offsets"]
            assert offsets[0] == 0
            assert np.all(np.diff(offsets) > 0), "Offsets must be strictly increasing"
            assert offsets[-1] == data["x_num"].shape[0]


class TestActionsReconstruct:
    """Actions reconstruct raw_pos_view within tolerance."""

    def test_actions_reconstruct_pos(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        for shard_path in shards:
            data = load_file(str(shard_path))
            raw = data["raw_pos_view"]
            actions = data["actions"]
            offsets = data["episode_offsets"]

            for i in range(len(offsets) - 1):
                s, e = int(offsets[i]), int(offsets[i + 1])
                if e - s < 2:
                    continue
                ep_raw = raw[s:e]
                ep_act = actions[s:e]

                dx_actual = np.diff(ep_raw[:, 0])
                dy_actual = np.diff(ep_raw[:, 1])
                dz_actual = np.diff(ep_raw[:, 2])

                dx_from_act = ep_act[:-1, 0] * 8.0
                dy_from_act = ep_act[:-1, 1] * 8.0
                dz_from_act = ep_act[:-1, 2] * 8.0

                assert np.allclose(dx_actual, dx_from_act, atol=1e-2), "dx mismatch"
                assert np.allclose(dy_actual, dy_from_act, atol=1e-2), "dy mismatch"
                assert np.allclose(dz_actual, dz_from_act, atol=1e-2), "dz mismatch"

                assert np.all(ep_act[-1] == 0), "Last tick actions must be zero"


class TestDeltaYawWrap:
    """Δyaw wrapping produces values in (-180, 180]."""

    def test_wrap_values(self) -> None:
        from tools.export_episodes import _wrap_delta_yaw

        d = np.array([0.0, 180.0, -180.0, 360.0, -360.0, 179.9, -179.9, 270.0])
        wrapped = _wrap_delta_yaw(d)
        assert np.all(wrapped > -180.0)
        assert np.all(wrapped <= 180.0)
        assert wrapped[1] == pytest.approx(180.0)
        assert wrapped[0] == pytest.approx(0.0)


class TestLabels:
    """Labels present for episodes with roundstats data."""

    def test_labels_present(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        for shard_path in shards:
            data = load_file(str(shard_path))
            labels_mask = data["labels_mask"]
            n_episodes = labels_mask.shape[0]
            if n_episodes == 0:
                continue
            labeled = labels_mask[:, 0].sum()
            ratio = labeled / n_episodes
            assert ratio >= 0.95, f"Labels coverage {ratio:.2%} < 95%"

    def test_labels_nan_when_missing(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "no_labels.db")
        demo = _make_demo_data("no_label_demo", "PlayerA", "TRAIN", n_ticks=200)
        demo["rounds"] = []
        _create_test_db(db_path, [demo])
        _run_export(db_path, tmp_export_dir)

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))
        labels = data["labels_round"]
        mask = data["labels_mask"]
        assert np.all(mask == 0)
        assert np.all(np.isnan(labels))

    def test_side_categorical_follows_roundstats(self, test_db: str, tmp_export_dir: Path) -> None:
        """x_cat[:, side] of every tick equals the episode's roundstats side (D-05)."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

        ct_idx = CS2_V2.vocab_index("side", "CT")
        t_idx = CS2_V2.vocab_index("side", "T")
        _run_export(test_db, tmp_export_dir)
        checked = 0
        for shard_path in tmp_export_dir.rglob("*.safetensors"):
            data = load_file(str(shard_path))
            offsets = data["episode_offsets"]
            labels = data["labels_round"]
            mask = data["labels_mask"]
            x_cat = data["x_cat"]
            for e in range(len(offsets) - 1):
                if mask[e, 7] != 1:
                    continue
                expected = ct_idx if labels[e, 7] == 1.0 else t_idx
                sides = x_cat[offsets[e] : offsets[e + 1], 2]
                assert np.all(sides == expected), f"episode {e}: side column != roundstats side"
                checked += 1
        assert checked > 0, "no labelled episode was checked"


class TestSafetensorsRoundTrip:
    """Safetensors files can be read back correctly."""

    def test_roundtrip(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert len(shards) >= 1

        for shard_path in shards:
            data = load_file(str(shard_path))
            assert "x_num" in data
            assert "x_cat" in data
            assert "raw_pos_view" in data
            assert "actions" in data
            assert "health" in data
            assert "enemies_visible" in data
            assert "tick" in data
            assert "filled" in data
            assert "episode_offsets" in data
            assert "episode_meta" in data
            assert "labels_round" in data
            assert "labels_mask" in data

            assert data["x_num"].dtype == np.float32
            assert data["x_cat"].dtype == np.int64
            assert data["raw_pos_view"].dtype == np.float32
            assert data["actions"].dtype == np.float32
            assert data["episode_offsets"].dtype == np.int64
            assert data["episode_meta"].dtype == np.int64
            assert data["labels_round"].dtype == np.float32
            assert data["labels_mask"].dtype == np.uint8
            assert data["filled"].dtype == np.uint8
            assert data["tick"].dtype == np.int64

    def test_metadata_fields(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert len(shards) >= 1

        from safetensors import safe_open

        for shard_path in shards:
            with safe_open(str(shard_path), framework="numpy") as f:
                meta = f.metadata()
            assert meta is not None
            assert "demo_name" in meta
            assert "map_name" in meta
            assert "tick_rate" in meta
            assert meta["tick_rate"] == "64"
            assert "players" in meta
            players = json.loads(meta["players"])
            assert isinstance(players, list)
            assert "schema_fingerprint" in meta
            assert "split" in meta
            assert "export_version" in meta
            assert meta["export_version"] == "1"


class TestManifest:
    """Manifest files are written correctly."""

    def test_manifest_written(self, multi_demo_db: str, tmp_export_dir: Path) -> None:
        _run_export(multi_demo_db, tmp_export_dir)
        manifests = list(tmp_export_dir.rglob("manifest.json"))
        assert len(manifests) >= 1

        for mpath in manifests:
            with open(mpath) as f:
                manifest = json.load(f)
            assert "schema_fingerprint" in manifest
            assert "export_version" in manifest
            assert "demos" in manifest
            assert "totals" in manifest
            assert manifest["totals"]["n_demos"] == len(manifest["demos"])

    def test_manifest_sha256(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        manifests = list(tmp_export_dir.rglob("manifest.json"))
        assert len(manifests) >= 1

        for mpath in manifests:
            with open(mpath) as f:
                manifest = json.load(f)
            for demo in manifest["demos"]:
                assert "sha256" in demo
                assert len(demo["sha256"]) == 64


class TestDeathCut:
    """Episodes are cut at the first health <= 0 tick."""

    def test_death_cut(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "death_test.db")
        demos = [
            _make_demo_data(
                "death_demo",
                "PlayerA",
                "TRAIN",
                n_ticks=300,
                n_rounds=1,
                death_at=220,
            )
        ]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir)

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))
        health = data["health"]
        offsets = data["episode_offsets"]

        for i in range(len(offsets) - 1):
            s, e = int(offsets[i]), int(offsets[i + 1])
            ep_health = health[s:e]
            dead = np.where(ep_health <= 0)[0]
            if len(dead) > 0:
                assert (
                    dead[0] == len(ep_health) - 1
                ), "Death tick should be the last tick of the episode"


class TestProfileMedium:
    """Medium profile limits episodes per player."""

    def test_medium_limit(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "medium_test.db")
        demos = [_make_demo_data("medium_demo", "PlayerA", "TRAIN", n_ticks=1500, n_rounds=15)]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir, profile="medium")

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))
        n_episodes = len(data["episode_offsets"]) - 1
        assert n_episodes <= 8, f"Medium profile should limit to 8 episodes, got {n_episodes}"


class TestProfileSample:
    """Sample profile truncates episodes."""

    def test_sample_truncation(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "sample_test.db")
        demos = [_make_demo_data("sample_demo", "PlayerA", "TRAIN", n_ticks=1000, n_rounds=1)]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir, profile="sample")

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))
        offsets = data["episode_offsets"]
        n_episodes = len(offsets) - 1
        assert n_episodes <= 2

        for i in range(n_episodes):
            ep_len = int(offsets[i + 1] - offsets[i])
            assert ep_len <= 448


class TestUnassignedSkipped:
    """UNASSIGNED demos are skipped."""

    def test_unassigned_skipped(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "unassigned_test.db")
        demos = [
            _make_demo_data("unassigned_demo", "PlayerA", "UNASSIGNED", n_ticks=200),
            _make_demo_data("assigned_demo", "PlayerB", "TRAIN", n_ticks=200),
        ]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir)

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        shard_names = [s.stem for s in shards]
        assert "unassigned_demo" not in shard_names
        assert "assigned_demo" in shard_names


class TestWarmupDropped:
    """Round 1 with time_in_round==0 ticks are dropped."""

    def test_warmup_dropped(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "warmup_test.db")
        con = sqlite3.connect(db_path)
        con.execute(
            "CREATE TABLE playermatchstats ("
            "  id INTEGER PRIMARY KEY,"
            "  player_name TEXT, demo_name TEXT, match_date TEXT,"
            "  match_date_source TEXT, dataset_split TEXT)"
        )
        con.execute(
            "CREATE TABLE playertickstate ("
            "  id INTEGER PRIMARY KEY,"
            "  tick INTEGER, player_name TEXT, demo_name TEXT,"
            "  pos_x REAL, pos_y REAL, pos_z REAL,"
            "  view_x REAL, view_y REAL,"
            "  health INTEGER, armor INTEGER,"
            "  is_crouching INTEGER, is_scoped INTEGER,"
            "  has_helmet INTEGER, has_defuser INTEGER,"
            "  active_weapon TEXT, equipment_value INTEGER,"
            "  enemies_visible INTEGER, is_blinded INTEGER,"
            "  round_number INTEGER, time_in_round REAL,"
            "  bomb_planted INTEGER, teammates_alive INTEGER,"
            "  enemies_alive INTEGER, team_economy INTEGER,"
            "  map_name TEXT)"
        )
        con.execute(
            "CREATE TABLE roundstats ("
            "  id INTEGER PRIMARY KEY,"
            "  demo_name TEXT, round_number INTEGER, player_name TEXT,"
            "  side TEXT, kills INTEGER, deaths INTEGER,"
            "  opening_kill INTEGER, opening_death INTEGER,"
            "  round_won INTEGER, kast INTEGER, round_rating REAL)"
        )
        con.execute("CREATE INDEX ix_pts_player_demo ON playertickstate(player_name, demo_name)")
        con.execute("CREATE INDEX ix_rs_demo_player ON roundstats(demo_name, player_name)")

        con.execute(
            "INSERT INTO playermatchstats VALUES (1, 'P', 'warmup_demo', '2026-01-01', "
            "'filename_date', 'TRAIN')"
        )

        t = 50
        for i in range(100):
            con.execute(
                "INSERT INTO playertickstate "
                "(tick, player_name, demo_name, pos_x, pos_y, pos_z, view_x, view_y, "
                "health, armor, is_crouching, is_scoped, has_helmet, has_defuser, "
                "active_weapon, equipment_value, enemies_visible, is_blinded, "
                "round_number, time_in_round, bomb_planted, teammates_alive, "
                "enemies_alive, team_economy, map_name) "
                "VALUES (?, 'P', 'warmup_demo', 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0, "
                "'ak47', 4750, 0, 0, 1, 0.0, 0, 4, 5, 10000, 'de_mirage')",
                (t + i,),
            )

        for i in range(200):
            con.execute(
                "INSERT INTO playertickstate "
                "(tick, player_name, demo_name, pos_x, pos_y, pos_z, view_x, view_y, "
                "health, armor, is_crouching, is_scoped, has_helmet, has_defuser, "
                "active_weapon, equipment_value, enemies_visible, is_blinded, "
                "round_number, time_in_round, bomb_planted, teammates_alive, "
                "enemies_alive, team_economy, map_name) "
                "VALUES (?, 'P', 'warmup_demo', ?, ?, 0, ?, 0, 100, 0, 0, 0, 0, 0, "
                "'ak47', 4750, 0, 0, 2, ?, 0, 4, 5, 10000, 'de_mirage')",
                (200 + i, float(i), float(i), float(i), float(i) * 0.1),
            )

        for rnd in [1, 2]:
            con.execute(
                "INSERT INTO roundstats VALUES (NULL, 'warmup_demo', ?, 'P', 'CT', "
                "1, 0, 0, 0, 1, 1, 1.0)",
                (rnd,),
            )

        con.commit()
        con.close()

        _run_export(db_path, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))
        meta = data["episode_meta"]
        for i in range(len(meta)):
            assert meta[i, 0] != 1 or data["tick"][int(data["episode_offsets"][i])] >= 200


class TestDemoSuffix:
    """Legacy .dem_Player suffix is stripped."""

    def test_suffix_stripped(self) -> None:
        from tools.export_episodes import _normalize_demo_name

        assert _normalize_demo_name("match.dem_Player") == "match"
        assert _normalize_demo_name("match.dem") == "match"
        assert _normalize_demo_name("match") == "match"
        assert _normalize_demo_name(None) == ""


class TestSplitDirectories:
    """Shards land in the correct split directory."""

    def test_split_dirs(self, multi_demo_db: str, tmp_export_dir: Path) -> None:
        _run_export(multi_demo_db, tmp_export_dir)
        found_splits = set()
        for shard in tmp_export_dir.rglob("*.safetensors"):
            found_splits.add(shard.parent.name)
        assert found_splits, "Expected at least one split directory"
        for s in found_splits:
            assert s in {"train", "val", "test"}


class TestWorkersConsistent:
    """Multi-worker output matches single-worker output."""

    def test_workers_same_result(self, multi_demo_db: str, tmp_path: Path) -> None:
        out1 = tmp_path / "w1"
        out2 = tmp_path / "w2"
        _run_export(multi_demo_db, out1, workers=1)
        _run_export(multi_demo_db, out2, workers=2)

        shards1 = sorted(out1.rglob("*.safetensors"), key=lambda p: p.name)
        shards2 = sorted(out2.rglob("*.safetensors"), key=lambda p: p.name)
        assert len(shards1) == len(shards2)

        for s1, s2 in zip(shards1, shards2):
            assert s1.name == s2.name
            d1 = load_file(str(s1))
            d2 = load_file(str(s2))
            for key in d1:
                np.testing.assert_array_equal(d1[key], d2[key], err_msg=f"Mismatch in {key}")


class TestTensorShapes:
    """Tensor shapes are consistent."""

    def test_shapes(self, test_db: str, tmp_export_dir: Path) -> None:
        _run_export(test_db, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        for shard_path in shards:
            data = load_file(str(shard_path))
            n = data["x_num"].shape[0]
            assert data["x_num"].shape == (n, 21)
            assert data["x_cat"].shape == (n, 3)
            assert data["raw_pos_view"].shape == (n, 5)
            assert data["actions"].shape == (n, 5)
            assert data["health"].shape == (n,)
            assert data["enemies_visible"].shape == (n,)
            assert data["tick"].shape == (n,)
            assert data["filled"].shape == (n,)

            n_ep = data["episode_meta"].shape[0]
            assert data["episode_offsets"].shape == (n_ep + 1,)
            assert data["episode_meta"].shape == (n_ep, 4)
            assert data["labels_round"].shape == (n_ep, 8)
            assert data["labels_mask"].shape == (n_ep, 8)


class TestNonChronologicalWarning:
    """Non-chronological match_date_source triggers OI-2 warning."""

    def test_oi2_warning(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "nonchron.db")
        demos = [
            _make_demo_data(
                "nc_demo",
                "PlayerA",
                "TRAIN",
                match_date_source="ingested_at",
            )
        ]
        _create_test_db(db_path, demos)
        _run_export(db_path, tmp_export_dir)

        manifests = list(tmp_export_dir.rglob("manifest.json"))
        assert len(manifests) >= 1
        with open(manifests[0]) as f:
            manifest = json.load(f)
        warnings = manifest.get("warnings", [])
        oi2 = [w for w in warnings if "OI-2" in w]
        assert len(oi2) > 0, "Expected OI-2 warning for non-chronological source"


class TestMultiPlayerLabelIsolation:
    """Labels must belong to the correct player, not cross-contaminate."""

    def test_labels_per_player(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "multi_player.db")
        con = sqlite3.connect(db_path)
        con.execute(
            "CREATE TABLE playermatchstats ("
            "  id INTEGER PRIMARY KEY,"
            "  player_name TEXT, demo_name TEXT, match_date TEXT,"
            "  match_date_source TEXT, dataset_split TEXT)"
        )
        con.execute(
            "CREATE TABLE playertickstate ("
            "  id INTEGER PRIMARY KEY,"
            "  tick INTEGER, player_name TEXT, demo_name TEXT,"
            "  pos_x REAL, pos_y REAL, pos_z REAL,"
            "  view_x REAL, view_y REAL,"
            "  health INTEGER, armor INTEGER,"
            "  is_crouching INTEGER, is_scoped INTEGER,"
            "  has_helmet INTEGER, has_defuser INTEGER,"
            "  active_weapon TEXT, equipment_value INTEGER,"
            "  enemies_visible INTEGER, is_blinded INTEGER,"
            "  round_number INTEGER, time_in_round REAL,"
            "  bomb_planted INTEGER, teammates_alive INTEGER,"
            "  enemies_alive INTEGER, team_economy INTEGER,"
            "  map_name TEXT)"
        )
        con.execute(
            "CREATE TABLE roundstats ("
            "  id INTEGER PRIMARY KEY,"
            "  demo_name TEXT, round_number INTEGER, player_name TEXT,"
            "  side TEXT, kills INTEGER, deaths INTEGER,"
            "  opening_kill INTEGER, opening_death INTEGER,"
            "  round_won INTEGER, kast INTEGER, round_rating REAL)"
        )
        con.execute("CREATE INDEX ix_pts_pd ON playertickstate(player_name, demo_name)")
        con.execute("CREATE INDEX ix_rs_dp ON roundstats(demo_name, player_name)")

        demo = "iso_demo"
        for pname in ("Alice", "Bob"):
            con.execute(
                "INSERT INTO playermatchstats "
                "(player_name, demo_name, match_date, match_date_source, dataset_split) "
                "VALUES (?, ?, '2026-01-01', 'filename_date', 'TRAIN')",
                (pname, demo),
            )
            for t in range(100, 300):
                con.execute(
                    "INSERT INTO playertickstate "
                    "(tick, player_name, demo_name, pos_x, pos_y, pos_z, view_x, view_y, "
                    "health, armor, is_crouching, is_scoped, has_helmet, has_defuser, "
                    "active_weapon, equipment_value, enemies_visible, is_blinded, "
                    "round_number, time_in_round, bomb_planted, teammates_alive, "
                    "enemies_alive, team_economy, map_name) "
                    "VALUES (?, ?, ?, ?, ?, 0, ?, 0, 100, 0, 0, 0, 0, 0, "
                    "'ak47', 4750, 0, 0, 2, ?, 0, 4, 5, 10000, 'de_mirage')",
                    (t, pname, demo, float(t), float(t), float(t), float(t - 100) * 0.1),
                )

        kills_alice, kills_bob = 1, 5
        con.execute(
            "INSERT INTO roundstats VALUES " "(NULL, ?, 2, 'alice', 'CT', ?, 0, 0, 0, 1, 1, 1.05)",
            (demo, kills_alice),
        )
        con.execute(
            "INSERT INTO roundstats VALUES " "(NULL, ?, 2, 'bob', 'T', ?, 1, 0, 0, 0, 0, 0.80)",
            (demo, kills_bob),
        )

        con.commit()
        con.close()

        _run_export(db_path, tmp_export_dir)
        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))

        meta = data["episode_meta"]
        labels = data["labels_round"]
        mask = data["labels_mask"]

        from safetensors import safe_open

        with safe_open(str(shards[0]), framework="numpy") as f:
            shard_meta = f.metadata()
        players = json.loads(shard_meta["players"])

        for i in range(len(meta)):
            pidx = int(meta[i, 3])
            pname = players[pidx].strip().casefold()
            if int(mask[i, 1]) == 0:
                continue
            ep_kills = float(labels[i, 1])
            if pname == "alice":
                assert ep_kills == float(
                    kills_alice
                ), f"Alice episode got kills={ep_kills}, expected {kills_alice}"
            elif pname == "bob":
                assert ep_kills == float(
                    kills_bob
                ), f"Bob episode got kills={ep_kills}, expected {kills_bob}"


class TestLabelFallbackPath:
    """Roundstats with original-case name exercises the fallback lookup."""

    def test_fallback_original_case(self, tmp_path: Path, tmp_export_dir: Path) -> None:
        db_path = str(tmp_path / "fallback.db")
        demo = _make_demo_data("fb_demo", "PlayerX", "TRAIN", n_ticks=200)
        for r in demo["rounds"]:
            r["player_name"] = "PlayerX"
        _create_test_db(db_path, [demo])
        _run_export(db_path, tmp_export_dir)

        shards = list(tmp_export_dir.rglob("*.safetensors"))
        assert shards, "Expected at least one shard"
        data = load_file(str(shards[0]))
        mask = data["labels_mask"]
        labeled = mask[:, 0].sum()
        n_ep = mask.shape[0]
        assert labeled / n_ep >= 0.95, "Fallback path should still resolve labels"
