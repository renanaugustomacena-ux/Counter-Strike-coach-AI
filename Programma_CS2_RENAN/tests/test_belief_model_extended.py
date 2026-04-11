"""
Tests for DB-integrated and edge-case paths of belief_model.py.

Covers gaps NOT addressed by test_analysis_engines_extended.py or test_game_theory.py:
  - extract_death_events_from_db() with mocked empty DB
  - auto_calibrate() partial column handling
  - DeathProbabilityEstimator.calibrate() AC-05 insufficient samples guard
  - Weapon lethality safety bounds after calibration
  - Threat decay NaN/Inf guard in polyfit path
  - get_death_estimator() thread-safety (identity across 2 threads)
  - BeliefState.threat_level() response to evidence changes
  - DeathProbabilityEstimator.estimate() output bounds under extreme inputs
"""

import pytest

pytestmark = pytest.mark.timeout(5)


class TestExtractDeathEventsEmptyDB:
    """DB-integrated extraction with mocked empty database."""

    def test_extract_death_events_empty_db(self, mock_db_manager, monkeypatch):
        """extract_death_events_from_db() returns empty DataFrame with correct
        columns when no RoundStats rows exist in the database.

        Unlike the test in test_game_theory.py (which hits the real DB or fails
        gracefully), this test injects mock_db_manager so the code path through
        get_db_manager -> get_session -> select(RoundStats) executes against a
        guaranteed-empty in-memory schema.
        """
        import pandas as pd

        from Programma_CS2_RENAN.backend.analysis import belief_model

        monkeypatch.setattr(
            "Programma_CS2_RENAN.backend.analysis.belief_model.get_db_manager",
            lambda: mock_db_manager,
        )

        # The function uses a lazy import of get_db_manager; patch it at the
        # call site inside extract_death_events_from_db. Since the function
        # does `from ... import get_db_manager` inside its body, we must also
        # ensure the patched name resolves correctly.
        df = belief_model.extract_death_events_from_db()

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["health", "died"]
        assert len(df) == 0


class TestAutoCalibratePartialColumns:
    """auto_calibrate() only calibrates what columns are present."""

    def test_auto_calibrate_partial_columns(self, monkeypatch):
        """auto_calibrate() gracefully handles a DataFrame that has only
        'health' and 'died' columns but lacks 'weapon_class' and
        'information_age'.  It should calibrate HP priors and skip the
        weapon lethality and threat decay branches without error.
        """
        import pandas as pd

        from Programma_CS2_RENAN.backend.analysis.belief_model import AdaptiveBeliefCalibrator

        calibrator = AdaptiveBeliefCalibrator()

        # Patch _save_snapshot to avoid touching the real DB
        monkeypatch.setattr(calibrator, "_save_snapshot", lambda summary, sample_count=0: None)

        # 200 samples with only health + died (no weapon_class, no information_age)
        df = pd.DataFrame(
            {
                "health": [90] * 100 + [30] * 100,
                "died": [False] * 80 + [True] * 20 + [True] * 90 + [False] * 10,
            }
        )

        summary = calibrator.auto_calibrate(df)

        # HP priors should be calibrated (>= MIN_SAMPLES)
        assert summary["hp_priors"], "HP priors should be non-empty"
        # Weapon lethality and threat decay must be empty/None (columns absent)
        assert summary["weapon_lethality"] == {}
        assert summary["threat_decay"] is None


class TestCalibrateInsufficientSamples:
    """AC-05: DeathProbabilityEstimator.calibrate() keeps default priors
    when sample count is below MIN_CALIBRATION_SAMPLES (30)."""

    def test_calibrate_insufficient_samples(self):
        """Providing fewer than 30 rows to calibrate() must leave
        _calibrated=False and priors unchanged.

        This tests the DeathProbabilityEstimator-level guard (30 samples),
        which is distinct from the AdaptiveBeliefCalibrator-level guard
        (100 samples) tested in test_game_theory.py.
        """
        import pandas as pd

        from Programma_CS2_RENAN.backend.analysis.belief_model import (
            _DEFAULT_PRIORS,
            DeathProbabilityEstimator,
        )

        est = DeathProbabilityEstimator()
        original_priors = dict(est.priors)

        # 20 samples — below MIN_CALIBRATION_SAMPLES (30)
        df = pd.DataFrame(
            {
                "health": [100] * 10 + [20] * 10,
                "died": [True] * 10 + [False] * 10,
            }
        )

        est.calibrate(df)

        assert est._calibrated is False
        assert est.priors == original_priors
        # Verify the originals actually match the module-level defaults
        assert est.priors["full"] == _DEFAULT_PRIORS["full"]
        assert est.priors["critical"] == _DEFAULT_PRIORS["critical"]


class TestWeaponLethalityBounded:
    """Calibrated weapon lethality values are clamped to safety bounds."""

    def test_weapon_lethality_bounded(self, monkeypatch):
        """calibrate_weapon_lethality() must return values within
        _LETHALITY_BOUNDS = (0.1, 3.0) even when the raw ratio would
        exceed those bounds.

        Constructs a DataFrame where one weapon class has an extremely
        high kill ratio relative to rifle to exercise the upper clamp.
        """
        import pandas as pd

        from Programma_CS2_RENAN.backend.analysis.belief_model import AdaptiveBeliefCalibrator

        calibrator = AdaptiveBeliefCalibrator()

        # 'awp' has 50 kills, 'rifle' has only 5 → raw ratio = 10.0
        # Should be clamped to _LETHALITY_BOUNDS[1] = 3.0
        # 'knife' has 10 kills, 'rifle' has 5 → raw ratio = 2.0 (within bounds)
        health_col = [90] * 200
        died_col = [True] * 65 + [False] * 135
        weapon_col = ["awp"] * 50 + ["rifle"] * 5 + ["knife"] * 10 + ["rifle"] * 135

        df = pd.DataFrame(
            {
                "health": health_col,
                "died": died_col,
                "weapon_class": weapon_col,
            }
        )

        result = calibrator.calibrate_weapon_lethality(df)

        for weapon_class, mult in result.items():
            assert (
                0.1 <= mult <= 3.0
            ), f"Weapon '{weapon_class}' multiplier {mult} outside safety bounds [0.1, 3.0]"


class TestThreatDecayNanGuard:
    """Non-finite polyfit result returns None (A-01 guard)."""

    def test_threat_decay_nan_guard(self, monkeypatch):
        """When np.polyfit returns NaN/Inf coefficients (degenerate input),
        calibrate_threat_decay() must return None rather than propagating
        a non-finite lambda into the BeliefState.

        Monkeypatches np.polyfit to return [NaN, NaN] to exercise the
        A-01 guard without relying on numerically unstable inputs.
        """
        import numpy as np
        import pandas as pd

        from Programma_CS2_RENAN.backend.analysis.belief_model import AdaptiveBeliefCalibrator

        calibrator = AdaptiveBeliefCalibrator()

        # Build data with enough rows and valid structure so the function
        # reaches the polyfit call (>= MIN_SAMPLES, >= 3 valid bins)
        rng = np.random.RandomState(42)
        n = 200
        df = pd.DataFrame(
            {
                "information_age": rng.uniform(0.0, 10.0, n),
                "died": rng.choice([True, False], n),
            }
        )

        # Force polyfit to return non-finite coefficients
        monkeypatch.setattr(np, "polyfit", lambda *a, **kw: np.array([np.nan, np.nan]))

        result = calibrator.calibrate_threat_decay(df)
        assert result is None, "Non-finite polyfit must yield None (A-01 guard)"


class TestGetDeathEstimatorSingleton:
    """Thread-safe singleton returns same instance from concurrent threads."""

    def test_get_death_estimator_singleton(self, monkeypatch):
        """get_death_estimator() must return the exact same object from
        two threads, verifying the double-checked locking pattern (P3-10).

        The module-level _death_estimator is reset to None before the test
        and restored after to avoid polluting other tests.
        """
        import threading

        import Programma_CS2_RENAN.backend.analysis.belief_model as bm

        # Reset the singleton so both threads race to create it
        original = bm._death_estimator
        monkeypatch.setattr(bm, "_death_estimator", None)

        results = [None, None]
        barrier = threading.Barrier(2)

        def _get(idx):
            barrier.wait()  # Synchronize start
            results[idx] = bm.get_death_estimator()

        t0 = threading.Thread(target=_get, args=(0,))
        t1 = threading.Thread(target=_get, args=(1,))
        t0.start()
        t1.start()
        t0.join(timeout=3)
        t1.join(timeout=3)

        assert results[0] is not None
        assert results[1] is not None
        assert results[0] is results[1], "Singleton must return identical object across threads"


class TestBeliefStateUpdateWithEvidence:
    """BeliefState.threat_level() responds correctly to evidence changes.

    Note: BeliefState is a dataclass without a dedicated update() method.
    'Updating with evidence' means constructing states with different
    field values and verifying threat_level() reflects the changes.
    """

    def test_belief_state_update_with_evidence(self):
        """threat_level() must increase when visible_enemies grows and
        must decrease when information_age increases (decay effect).
        Validates the core Bayesian evidence-response behaviour.
        """
        from Programma_CS2_RENAN.backend.analysis.belief_model import BeliefState

        # Baseline: no enemies
        baseline = BeliefState(visible_enemies=0, inferred_enemies=0, information_age=0.0)
        assert baseline.threat_level() == 0.0

        # Adding visible enemies increases threat
        with_visible = BeliefState(visible_enemies=3, inferred_enemies=0, information_age=0.0)
        assert with_visible.threat_level() > baseline.threat_level()

        # Adding inferred enemies (fresh info) increases threat beyond visible-only
        with_inferred = BeliefState(visible_enemies=3, inferred_enemies=2, information_age=0.0)
        assert with_inferred.threat_level() > with_visible.threat_level()

        # Aging the information decays inferred contribution
        with_aged = BeliefState(visible_enemies=3, inferred_enemies=2, information_age=50.0)
        assert with_aged.threat_level() < with_inferred.threat_level()
        # But visible enemies are unaffected by age
        assert with_aged.threat_level() >= with_visible.threat_level() - 1e-9


class TestDeathEstimatorEstimateBounded:
    """estimate() returns values in [0, 1] under extreme inputs."""

    def test_death_estimator_estimate_bounded(self):
        """Verify estimate() output stays in [0.0, 1.0] across a range of
        extreme belief states, health values, armor states, and weapon classes.
        Tests combinations that push log-odds toward +/- infinity.
        """
        from Programma_CS2_RENAN.backend.analysis.belief_model import (
            BeliefState,
            DeathProbabilityEstimator,
        )

        est = DeathProbabilityEstimator()

        extreme_cases = [
            # (belief, hp, armor, weapon_class)
            # Maximum threat
            (
                BeliefState(
                    visible_enemies=5,
                    inferred_enemies=5,
                    information_age=0.0,
                    positional_exposure=1.0,
                ),
                1,
                False,
                "awp",
            ),
            # Minimum threat
            (
                BeliefState(
                    visible_enemies=0,
                    inferred_enemies=0,
                    information_age=1000.0,
                    positional_exposure=0.0,
                ),
                100,
                True,
                "knife",
            ),
            # Zero HP edge
            (
                BeliefState(
                    visible_enemies=3,
                    inferred_enemies=0,
                    information_age=0.0,
                    positional_exposure=0.5,
                ),
                0,
                True,
                "rifle",
            ),
            # Unknown weapon
            (
                BeliefState(
                    visible_enemies=2,
                    inferred_enemies=1,
                    information_age=5.0,
                    positional_exposure=0.8,
                ),
                50,
                False,
                "unknown",
            ),
            # Negative HP (defensive — should not crash)
            (
                BeliefState(
                    visible_enemies=1,
                    inferred_enemies=0,
                    information_age=0.0,
                    positional_exposure=0.0,
                ),
                -10,
                True,
                "smg",
            ),
            # Very large HP (unrealistic but should not crash)
            (
                BeliefState(
                    visible_enemies=0,
                    inferred_enemies=0,
                    information_age=0.0,
                    positional_exposure=0.0,
                ),
                999,
                False,
                "pistol",
            ),
        ]

        for belief, hp, armor, weapon in extreme_cases:
            prob = est.estimate(belief, player_hp=hp, armor=armor, weapon_class=weapon)
            assert 0.0 <= prob <= 1.0, (
                f"estimate() returned {prob} for hp={hp}, armor={armor}, "
                f"weapon={weapon}, visible={belief.visible_enemies}"
            )
