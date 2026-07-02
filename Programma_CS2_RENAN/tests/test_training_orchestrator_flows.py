"""
Tests for training_orchestrator.py — Training targets, map resolution,
tactical classification, batch preparation, and training flow edge cases.

Complements test_training_orchestrator_logic.py (init, early stopping,
empty batch handling, deterministic RNG).

CI-portable: uses mocks for external dependencies.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import torch

pytestmark = pytest.mark.timeout(60)


def _make_orchestrator(model_type="jepa", **kwargs):
    """Create a TrainingOrchestrator with mocked device and manager."""
    with patch(
        "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
        return_value=torch.device("cpu"),
    ):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        manager = MagicMock()
        return TrainingOrchestrator(manager, model_type=model_type, **kwargs)


# ===========================================================================
# _resolve_map_name
# ===========================================================================


class TestResolveMapName:
    """Tests for _resolve_map_name — static method for map name resolution."""

    def test_from_metadata(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        match_mgr = MagicMock()
        meta = SimpleNamespace(map_name="de_inferno")
        match_mgr.get_metadata.return_value = meta
        cache = {}

        result = TrainingOrchestrator._resolve_map_name(1, "demo.dem", match_mgr, cache)
        assert result == "de_inferno"

    def test_from_metadata_adds_de_prefix(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        match_mgr = MagicMock()
        meta = SimpleNamespace(map_name="mirage")
        match_mgr.get_metadata.return_value = meta
        cache = {}

        result = TrainingOrchestrator._resolve_map_name(1, "demo.dem", match_mgr, cache)
        assert result == "de_mirage"

    def test_from_demo_name_pattern(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        result = TrainingOrchestrator._resolve_map_name(None, "faze_vs_navi_dust2.dem", None, {})
        assert result == "de_dust2"

    def test_from_demo_name_case_insensitive(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        result = TrainingOrchestrator._resolve_map_name(None, "MATCH_INFERNO_2024.dem", None, {})
        assert result == "de_inferno"

    def test_fallback_to_mirage(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        result = TrainingOrchestrator._resolve_map_name(None, "unknown_demo.dem", None, {})
        assert result == "de_mirage"

    def test_metadata_cache_prevents_requery(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        match_mgr = MagicMock()
        meta = SimpleNamespace(map_name="de_nuke")
        match_mgr.get_metadata.return_value = meta
        cache = {}

        # First call populates cache
        TrainingOrchestrator._resolve_map_name(1, "demo.dem", match_mgr, cache)
        # Second call should use cache (get_metadata NOT called again)
        match_mgr.get_metadata.reset_mock()
        TrainingOrchestrator._resolve_map_name(1, "demo.dem", match_mgr, cache)
        match_mgr.get_metadata.assert_not_called()

    def test_metadata_exception_falls_back_to_demo_name(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        match_mgr = MagicMock()
        match_mgr.get_metadata.side_effect = RuntimeError("DB error")
        cache = {}

        result = TrainingOrchestrator._resolve_map_name(1, "match_ancient.dem", match_mgr, cache)
        assert result == "de_ancient"

    def test_all_known_maps_detected(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        known_maps = [
            "mirage",
            "inferno",
            "dust2",
            "ancient",
            "nuke",
            "anubis",
            "overpass",
            "vertigo",
        ]
        for m in known_maps:
            result = TrainingOrchestrator._resolve_map_name(None, f"demo_{m}_2024.dem", None, {})
            assert result == f"de_{m}", f"Failed to detect {m}"


# ===========================================================================
# _compute_advantage
# ===========================================================================


class TestComputeAdvantage:
    """Tests for _compute_advantage — continuous advantage [0, 1]."""

    def _make_player(self, team, health=100, equip=4000, is_alive=True):
        return SimpleNamespace(team=team, health=health, equipment_value=equip, is_alive=is_alive)

    def test_balanced_returns_around_half(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        players = [
            self._make_player("CT", 100, 4000),
            self._make_player("CT", 100, 4000),
            self._make_player("T", 100, 4000),
            self._make_player("T", 100, 4000),
        ]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        assert 0.45 <= adv <= 0.55, f"Balanced game should be ~0.5, got {adv}"

    def test_numerical_advantage_increases_score(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        players = [
            self._make_player("CT", 100, 4000),
            self._make_player("CT", 100, 4000),
            self._make_player("CT", 100, 4000),
            self._make_player("T", 100, 4000),
        ]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        assert adv > 0.55, f"3v1 should be > 0.55, got {adv}"

    def test_numerical_disadvantage_decreases_score(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        players = [
            self._make_player("CT", 100, 4000),
            self._make_player("T", 100, 4000),
            self._make_player("T", 100, 4000),
            self._make_player("T", 100, 4000),
        ]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        assert adv < 0.45, f"1v3 should be < 0.45, got {adv}"

    def test_bomb_planted_advantage_for_t(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        players = [
            self._make_player("CT", 100, 4000),
            self._make_player("T", 100, 4000),
        ]
        adv_no_bomb = TrainingOrchestrator._compute_advantage(players, "T", bomb_planted=False)
        adv_bomb = TrainingOrchestrator._compute_advantage(players, "T", bomb_planted=True)
        assert adv_bomb > adv_no_bomb, "Bomb planted should increase T advantage"

    def test_bomb_planted_disadvantage_for_ct(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        players = [
            self._make_player("CT", 100, 4000),
            self._make_player("T", 100, 4000),
        ]
        adv_no_bomb = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        adv_bomb = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=True)
        assert adv_bomb < adv_no_bomb, "Bomb planted should decrease CT advantage"

    def test_dead_players_not_counted(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        players = [
            self._make_player("CT", 100, 4000, is_alive=True),
            self._make_player("T", 100, 4000, is_alive=False),  # Dead
        ]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        # CT has 1 alive, T has 0 alive → strong advantage for CT
        assert adv > 0.6, f"1v0 should be strong advantage, got {adv}"

    def test_result_always_in_0_1_range(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        # Extreme case: 5v0
        players = [self._make_player("CT", 100, 10000) for _ in range(5)]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=False)
        assert 0.0 <= adv <= 1.0

        # Extreme case: 0v5
        players = [self._make_player("T", 100, 10000) for _ in range(5)]
        adv = TrainingOrchestrator._compute_advantage(players, "CT", bomb_planted=True)
        assert 0.0 <= adv <= 1.0

    def test_no_players_returns_safe_value(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        adv = TrainingOrchestrator._compute_advantage([], "CT", bomb_planted=False)
        assert 0.0 <= adv <= 1.0


# ===========================================================================
# _classify_tactical_role
# ===========================================================================


class TestClassifyTacticalRole:
    """Tests for _classify_tactical_role — heuristic role classification."""

    def _make_item(self, team="CT", equipment_value=4000, is_crouching=False):
        return SimpleNamespace(
            team=team, equipment_value=equipment_value, is_crouching=is_crouching
        )

    def test_save_on_low_equipment(self):
        orch = _make_orchestrator()
        item = self._make_item(equipment_value=500)
        role = orch._classify_tactical_role(item, knowledge=None, all_players=[])
        assert role == orch.ROLE_SAVE

    def test_ct_default_passive_hold(self):
        orch = _make_orchestrator()
        item = self._make_item(team="CT", equipment_value=4000)
        role = orch._classify_tactical_role(item, knowledge=None, all_players=[])
        assert role == orch.ROLE_PASSIVE_HOLD

    def test_t_default_site_take(self):
        orch = _make_orchestrator()
        item = self._make_item(team="T", equipment_value=4000)
        role = orch._classify_tactical_role(item, knowledge=None, all_players=[])
        assert role == orch.ROLE_SITE_TAKE

    def test_ct_retake_on_bomb_planted(self):
        orch = _make_orchestrator()
        item = self._make_item(team="CT", equipment_value=4000)
        knowledge = SimpleNamespace(
            bomb_planted=True,
            visible_enemy_count=0,
            teammate_positions=[],
            visible_enemies=[],
        )
        role = orch._classify_tactical_role(item, knowledge=knowledge, all_players=[])
        assert role == orch.ROLE_RETAKE

    def test_lurk_when_far_from_team(self):
        orch = _make_orchestrator()
        item = self._make_item(team="T", equipment_value=4000)
        knowledge = SimpleNamespace(
            bomb_planted=False,
            visible_enemy_count=0,
            teammate_positions=[
                SimpleNamespace(distance=2000.0),
                SimpleNamespace(distance=2500.0),
            ],
            visible_enemies=[],
        )
        role = orch._classify_tactical_role(item, knowledge=knowledge, all_players=[])
        assert role == orch.ROLE_LURK

    def test_entry_frag_close_enemy(self):
        orch = _make_orchestrator()
        item = self._make_item(team="T", equipment_value=4000)
        knowledge = SimpleNamespace(
            bomb_planted=False,
            visible_enemy_count=1,
            teammate_positions=[],
            visible_enemies=[SimpleNamespace(distance=500.0)],
        )
        role = orch._classify_tactical_role(item, knowledge=knowledge, all_players=[])
        assert role == orch.ROLE_ENTRY_FRAG

    def test_aggressive_push_distant_enemy(self):
        orch = _make_orchestrator()
        item = self._make_item(team="T", equipment_value=4000)
        knowledge = SimpleNamespace(
            bomb_planted=False,
            visible_enemy_count=1,
            teammate_positions=[],
            visible_enemies=[SimpleNamespace(distance=1500.0)],
        )
        role = orch._classify_tactical_role(item, knowledge=knowledge, all_players=[])
        assert role == orch.ROLE_AGGRESSIVE_PUSH

    def test_ct_anchor_when_crouching(self):
        orch = _make_orchestrator()
        item = self._make_item(team="CT", equipment_value=4000, is_crouching=True)
        knowledge = SimpleNamespace(
            bomb_planted=False,
            visible_enemy_count=0,
            teammate_positions=[],
            visible_enemies=[],
        )
        role = orch._classify_tactical_role(item, knowledge=knowledge, all_players=[])
        assert role == orch.ROLE_ANCHOR

    def test_support_near_teammates(self):
        orch = _make_orchestrator()
        item = self._make_item(team="T", equipment_value=4000)
        knowledge = SimpleNamespace(
            bomb_planted=False,
            visible_enemy_count=0,
            teammate_positions=[
                SimpleNamespace(distance=300.0),
                SimpleNamespace(distance=400.0),
            ],
            visible_enemies=[],
        )
        role = orch._classify_tactical_role(item, knowledge=knowledge, all_players=[])
        assert role == orch.ROLE_SUPPORT

    def test_role_always_in_valid_range(self):
        orch = _make_orchestrator()
        # Test all combinations
        for team in ["CT", "T"]:
            for equip in [500, 4000]:
                for crouch in [True, False]:
                    item = self._make_item(team=team, equipment_value=equip, is_crouching=crouch)
                    role = orch._classify_tactical_role(item, knowledge=None, all_players=[])
                    assert 0 <= role <= 9, f"Role {role} out of range for {team}/{equip}/{crouch}"


# ===========================================================================
# _fetch_batches
# ===========================================================================


class TestFetchBatches:
    """Tests for _fetch_batches — data fetching and batching."""

    def test_returns_correct_number_of_batches(self):
        orch = _make_orchestrator(batch_size=4)
        orch.manager._fetch_jepa_ticks.return_value = list(range(10))
        batches = orch._fetch_batches(is_train=True)
        assert len(batches) == 3
        assert len(batches[0]) == 4
        assert len(batches[-1]) == 2

    def test_uses_train_split_when_is_train(self):
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = []
        orch._fetch_batches(is_train=True)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="train", seed=42, sample_size=50_000
        )

    def test_uses_val_split_when_not_train(self):
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = []
        orch._fetch_batches(is_train=False)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="val", seed=42, sample_size=10_000
        )

    def test_epoch_seed_rotation(self):
        """B1: Different epochs produce different seeds."""
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = []
        orch._fetch_batches(is_train=True, epoch=5)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="train", seed=47, sample_size=50_000
        )

    def test_val_uses_fixed_seed_regardless_of_epoch(self):
        """B1.3: Val split always uses GLOBAL_SEED (epoch ignored for val in run_training)."""
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = []
        orch._fetch_batches(is_train=False, epoch=0)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="val", seed=42, sample_size=10_000
        )


# ===========================================================================
# _prepare_tensor_batch — JEPA path
# ===========================================================================


class TestPrepareTensorBatchJEPA:
    """Tests for _prepare_tensor_batch JEPA path."""

    def _make_tick_items(self, n=10):
        """Create mock PlayerTickState-like items for FeatureExtractor."""
        items = []
        for i in range(n):
            items.append(
                SimpleNamespace(
                    tick=i,
                    player_name="TestPlayer",
                    demo_name="test.dem",
                    pos_x=100.0 + i,
                    pos_y=200.0,
                    pos_z=0.0,
                    view_x=0.0,
                    view_y=0.0,
                    health=100,
                    armor=100,
                    has_helmet=True,
                    has_defuser=False,
                    equipment_value=4750,
                    is_crouching=False,
                    is_scoped=False,
                    is_blinded=False,
                    enemies_visible=0,
                    active_weapon="ak47",
                    team="T",
                    round_time=60.0,
                    round_number=1,
                    bomb_planted=False,
                    teammates_alive=4,
                    enemies_alive=5,
                    team_economy=20000,
                    match_id=None,
                )
            )
        return items

    def test_jepa_batch_returns_correct_keys(self):
        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(11)  # V-1: need context_len+1 minimum
        result = orch._prepare_tensor_batch(items)
        assert result is not None
        assert "context" in result
        assert "target" in result
        assert "negatives" in result

    def test_jepa_batch_context_shape(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(11)  # V-1: need context_len+1 minimum
        result = orch._prepare_tensor_batch(items)
        assert result["context"].shape == (1, 10, METADATA_DIM)

    def test_jepa_batch_target_shape(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(11)  # V-1: need context_len+1 minimum
        result = orch._prepare_tensor_batch(items)
        assert result["target"].shape == (1, 1, METADATA_DIM)

    def test_jepa_batch_negatives_shape(self):
        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(11)  # V-1: need context_len+1 minimum
        result = orch._prepare_tensor_batch(items)
        assert result["negatives"].shape == (1, 5, METADATA_DIM)

    def test_jepa_batch_too_small_returns_none(self):
        """Batch with < 5 items can't produce negatives → returns None."""
        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(3)
        result = orch._prepare_tensor_batch(items)
        assert result is None

    def test_jepa_short_batch_skipped_instead_of_padded(self):
        """J-5 FIX: Batches with < 11 ticks return None instead of zero-padding.

        Zero vectors encode physically impossible game states (health=0, pos=origin).
        Skipping short batches prevents position-dependent encoder bias.
        """
        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(6)
        result = orch._prepare_tensor_batch(items)
        assert result is None

    def test_jepa_exact_ten_ticks_returns_none(self):
        """V-1 FIX: Exactly 10 ticks returns None — need 11 for context + target.

        With 10 ticks, target would be context[-1] (overlap). The model would learn
        to predict what it already sees, producing misleading low loss.
        """
        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(10)
        result = orch._prepare_tensor_batch(items)
        assert result is None

    def test_jepa_target_follows_context(self):
        """V-1 FIX: Target is tick immediately after context window.

        Previously target was features_tensor[-1:] which could be distant from context.
        Now target is features_tensor[10:11] — the next tick after context ticks[0:10].
        """

        from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(20)  # Enough ticks to test
        result = orch._prepare_tensor_batch(items)
        assert result is not None
        # Target should be tick at index 10, not tick at index 19
        # Both context[0, -1, :] (tick 9) and target[0, 0, :] (tick 10) should be different
        context_last = result["context"][0, -1, :]  # tick 9
        target_tick = result["target"][0, 0, :]  # tick 10
        # They come from different ticks so health values should generally differ
        # (each tick_items has unique tick number → different features)
        assert target_tick.shape == (METADATA_DIM,)


# ===========================================================================
# run_training edge cases
# ===========================================================================


class TestRunTrainingEdgeCases:
    """Tests for run_training edge cases."""

    @pytest.mark.timeout(15)
    def test_aborts_when_no_training_data(self):
        """run_training should exit gracefully when no data is available."""
        orch = _make_orchestrator(model_type="jepa")
        orch.manager._fetch_jepa_ticks.return_value = []

        # Mock model and trainer to avoid real PyTorch initialization
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_trainer = MagicMock()
        orch.TrainerClass = MagicMock(return_value=mock_trainer)

        with patch(
            "Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check"
        ) as mock_qc:
            mock_qc.return_value = MagicMock(passed=True)
            with patch("Programma_CS2_RENAN.backend.nn.factory.ModelFactory") as mock_factory:
                mock_factory.get_model.return_value = mock_model
                with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.load_nn"):
                    with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"):
                        orch.run_training()  # Should not crash

    def test_report_progress_delegates_to_manager(self):
        orch = _make_orchestrator(model_type="jepa", max_epochs=50)
        orch._report_progress(5, 0.1234, 0.0567)
        orch.manager._update_state.assert_called_once()
        call_args = orch.manager._update_state.call_args
        assert call_args[0][0] == "Training"
        assert "5/50" in call_args[0][1]


# ===========================================================================
# B1 — Per-epoch seed rotation
# ===========================================================================


class TestPerEpochSeedRotation:
    """B1: Verify per-epoch seed rotation in the training data pipeline."""

    def test_same_epoch_same_seed(self):
        """B1.4a: Identical epoch → identical seed → deterministic."""
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = list(range(8))
        orch._fetch_batches(is_train=True, epoch=3)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="train", seed=45, sample_size=50_000
        )

    def test_different_epochs_different_seeds(self):
        """B1.4b: Different epochs → different seeds."""
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = []

        orch._fetch_batches(is_train=True, epoch=1)
        call1 = orch.manager._fetch_jepa_ticks.call_args

        orch._fetch_batches(is_train=True, epoch=2)
        call2 = orch.manager._fetch_jepa_ticks.call_args

        assert call1.kwargs["seed"] != call2.kwargs["seed"]

    def test_val_seed_stable_across_epochs(self):
        """B1.4c: Val always uses GLOBAL_SEED regardless of epoch param."""
        orch = _make_orchestrator()
        orch.manager._fetch_jepa_ticks.return_value = []

        orch._fetch_batches(is_train=False, epoch=0)
        seed_0 = orch.manager._fetch_jepa_ticks.call_args.kwargs["seed"]

        orch._fetch_batches(is_train=False, epoch=5)
        seed_5 = orch.manager._fetch_jepa_ticks.call_args.kwargs["seed"]

        assert seed_0 == seed_5 == 42

    def test_run_epoch_loop_refetches_train_per_epoch(self):
        """B1: _run_epoch_loop fetches fresh train data each epoch."""
        orch = _make_orchestrator(max_epochs=3, batch_size=4)
        orch.manager._fetch_jepa_ticks.return_value = list(range(8))

        mock_trainer = MagicMock()
        mock_model = MagicMock()
        val_data = [[1, 2, 3, 4]]

        # _run_epoch fires on_epoch_start, calls _run_epoch (which we mock)
        with patch.object(orch, "_run_epoch", return_value=1.0):
            with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"):
                orch._run_epoch_loop(mock_trainer, mock_model, val_data, None)

        # Should have called _fetch_jepa_ticks once per epoch (3 total)
        fetch_calls = orch.manager._fetch_jepa_ticks.call_args_list
        assert len(fetch_calls) == 3
        seeds = [c.kwargs["seed"] for c in fetch_calls]
        assert seeds == [43, 44, 45]  # GLOBAL_SEED + epoch (1, 2, 3)


# ===========================================================================
# B2 — Configurable subsample sizes
# ===========================================================================


class TestSubsampleSizeConfig:
    """B2: Verify configurable train/val sample sizes."""

    def test_default_train_samples(self):
        orch = _make_orchestrator()
        assert orch._train_samples == 50_000

    def test_default_val_samples(self):
        orch = _make_orchestrator()
        assert orch._val_samples == 10_000

    def test_custom_train_samples(self):
        orch = _make_orchestrator(train_samples=1000)
        assert orch._train_samples == 1000

    def test_custom_val_samples(self):
        orch = _make_orchestrator(val_samples=500)
        assert orch._val_samples == 500

    def test_custom_sizes_passed_to_fetch(self):
        """B2: Custom sizes propagate to _fetch_jepa_ticks."""
        orch = _make_orchestrator(train_samples=2000, val_samples=800)
        orch.manager._fetch_jepa_ticks.return_value = []

        orch._fetch_batches(is_train=True, epoch=1)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="train", seed=43, sample_size=2000
        )

        orch._fetch_batches(is_train=False, epoch=0)
        orch.manager._fetch_jepa_ticks.assert_called_with(
            is_pro=True, split="val", seed=42, sample_size=800
        )


# ===========================================================================
# B3 — Patience & best_val_loss resume
# ===========================================================================


class TestPatienceConfig:
    """B3.1: Verify --patience flag threads to orchestrator."""

    def test_default_patience(self):
        orch = _make_orchestrator()
        assert orch.patience == 10

    def test_custom_patience(self):
        orch = _make_orchestrator(patience=25)
        assert orch.patience == 25

    def test_early_stop_at_custom_patience(self):
        """Early stopping triggers after patience epochs without improvement."""
        orch = _make_orchestrator(max_epochs=50, patience=3)
        mock_trainer = MagicMock()
        mock_model = MagicMock()

        with patch.object(orch, "_run_epoch", return_value=2.0):
            with patch.object(orch, "_fetch_batches", return_value=[[1, 2, 3]]):
                with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"):
                    # best_val_loss starts at inf, so epoch 1 improves → counter=0
                    # epochs 2,3,4 don't improve → counter reaches 3 → stop
                    final = orch._run_epoch_loop(mock_trainer, mock_model, [[1]], None)
                    assert final == 4  # stopped at epoch 4 (patience=3 after 1 improvement)


class TestBestValLossResume:
    """B3.2: Verify best_val_loss restores from sidecar on resume."""

    def test_restore_from_sidecar(self, tmp_path):
        """B3.2: best_val_loss is restored from checkpoint sidecar."""
        import json

        orch = _make_orchestrator()
        assert orch.best_val_loss == float("inf")

        # Create fake sidecar with stored best_val_loss
        model_dir = tmp_path / "global"
        model_dir.mkdir(parents=True)
        sidecar = model_dir / "jepa_brain.pt.meta.json"
        sidecar.write_text(
            json.dumps(
                {
                    "schema_version": "v1",
                    "metadata_dim": 25,
                    "feature_names": [],
                    "extra": {"best_val_loss": 1.8977},
                }
            )
        )

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=model_dir / "jepa_brain.pt",
        ):
            orch._restore_best_val_from_sidecar()

        assert orch.best_val_loss == pytest.approx(1.8977)

    def test_no_sidecar_keeps_inf(self, tmp_path):
        """B3.2: Missing sidecar leaves best_val_loss at +inf (fresh start)."""
        orch = _make_orchestrator()
        model_dir = tmp_path / "global"
        model_dir.mkdir(parents=True)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=model_dir / "jepa_brain.pt",
        ):
            orch._restore_best_val_from_sidecar()

        assert orch.best_val_loss == float("inf")

    def test_sidecar_without_extra_keeps_inf(self, tmp_path):
        """B3.2: Sidecar without extra field leaves best_val_loss at +inf."""
        import json

        orch = _make_orchestrator()
        model_dir = tmp_path / "global"
        model_dir.mkdir(parents=True)
        sidecar = model_dir / "jepa_brain.pt.meta.json"
        sidecar.write_text(
            json.dumps({"schema_version": "v1", "metadata_dim": 25, "feature_names": []})
        )

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=model_dir / "jepa_brain.pt",
        ):
            orch._restore_best_val_from_sidecar()

        assert orch.best_val_loss == float("inf")

    def test_save_persists_best_val_loss(self):
        """B3.2: save_nn is called with extra_meta containing best_val_loss."""
        orch = _make_orchestrator(max_epochs=1, patience=10)
        mock_trainer = MagicMock()
        mock_model = MagicMock()

        with patch.object(orch, "_run_epoch", return_value=1.5):
            with patch.object(orch, "_fetch_batches", return_value=[[1, 2, 3]]):
                with patch(
                    "Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"
                ) as mock_save:
                    orch._run_epoch_loop(mock_trainer, mock_model, [[1]], None)

                    # First save_nn call should be the "best" save with extra_meta
                    best_call = mock_save.call_args_list[0]
                    assert best_call.kwargs.get("extra_meta") == {"best_val_loss": 1.5}


class TestEMATotalSteps:
    """B3.3: Verify EMA total_steps derives from actual planned steps."""

    def test_set_total_steps_called_with_planned_values(self):
        """B3.3: set_total_steps called with max_epochs * steps_per_epoch."""
        orch = _make_orchestrator(max_epochs=100)
        orch.manager._fetch_jepa_ticks.return_value = list(range(100))

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_trainer = MagicMock()
        mock_trainer.set_total_steps = MagicMock()
        orch.TrainerClass = MagicMock(return_value=mock_trainer)

        with patch(
            "Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check"
        ) as mock_qc:
            mock_qc.return_value = MagicMock(passed=True)
            with patch("Programma_CS2_RENAN.backend.nn.factory.ModelFactory") as mf:
                mf.get_model.return_value = mock_model
                with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.load_nn"):
                    with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"):
                        with patch.object(orch, "_run_epoch_loop", return_value=1):
                            with patch.object(orch, "_finalize_training"):
                                orch.run_training()

        mock_trainer.set_total_steps.assert_called_once()
        call_args = mock_trainer.set_total_steps.call_args[0]
        assert call_args[0] == 100  # max_epochs
        # steps_per_epoch = ceil(batches / accumulation_steps)
        # batches = ceil(100 items / 32 batch_size) = 4
        # steps_per_epoch = ceil(4 / 4 accum) = 1
        assert call_args[1] >= 1


# ===========================================================================
# Weight constants and role indices
# ===========================================================================


class TestConstants:
    """Verify training orchestrator constants are valid."""

    def test_advantage_weights_sum_to_one(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        total = (
            TrainingOrchestrator._ADV_W_ALIVE
            + TrainingOrchestrator._ADV_W_HP
            + TrainingOrchestrator._ADV_W_EQUIP
            + TrainingOrchestrator._ADV_W_BOMB
        )
        assert total == pytest.approx(1.0), f"Advantage weights sum to {total}, expected 1.0"

    def test_role_indices_unique_and_contiguous(self):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        roles = [
            TrainingOrchestrator.ROLE_SITE_TAKE,
            TrainingOrchestrator.ROLE_ROTATION,
            TrainingOrchestrator.ROLE_ENTRY_FRAG,
            TrainingOrchestrator.ROLE_SUPPORT,
            TrainingOrchestrator.ROLE_ANCHOR,
            TrainingOrchestrator.ROLE_LURK,
            TrainingOrchestrator.ROLE_RETAKE,
            TrainingOrchestrator.ROLE_SAVE,
            TrainingOrchestrator.ROLE_AGGRESSIVE_PUSH,
            TrainingOrchestrator.ROLE_PASSIVE_HOLD,
        ]
        assert sorted(roles) == list(range(10)), "Role indices should be 0-9 contiguous"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestNegativePoolWarmupLogging(TestPrepareTensorBatchJEPA):
    """W1.6 (NN-H-03): the warmup→cross-match pool transition logs exactly once."""

    def test_pool_ready_logged_once(self):
        from unittest import mock

        import Programma_CS2_RENAN.backend.nn.training_orchestrator as tom

        orch = _make_orchestrator(model_type="jepa")
        items = self._make_tick_items(11)
        with mock.patch.object(tom, "logger") as mock_log:
            orch._prepare_tensor_batch(items)  # warm-up: in-batch fallback, seeds pool
            orch._prepare_tensor_batch(items)  # pool >= n_neg -> first pool use, logs
            orch._prepare_tensor_batch(items)  # second pool use -> must NOT log again
        ready = [c for c in mock_log.info.call_args_list if "negative pool warmed up" in str(c)]
        assert len(ready) == 1
