"""F-0030 regression: classify() must refuse stats dicts that carry none
of the role-vocabulary keys instead of fabricating a confident role.

The live path fed MATCH_AGGREGATE-shaped dicts (kd_ratio present, all
five role-signal families absent): every affinity scored 0 except the
IGL balanced-KD bonus, and normalization turned that single feature into
"IGL (100% confidence)"."""

from unittest.mock import MagicMock

from Programma_CS2_RENAN.backend.analysis.role_classifier import RoleClassifier
from Programma_CS2_RENAN.core.app_types import PlayerRole


def _warm_classifier() -> RoleClassifier:
    rc = RoleClassifier.__new__(RoleClassifier)
    store = MagicMock()
    store.is_cold_start.return_value = False
    store.get_threshold.return_value = None
    rc.threshold_store = store
    return rc


def test_aggregate_dict_with_balanced_kd_is_refused():
    """THE F-0030 shape: kd_ratio 1.0, zero vocabulary keys → 0.0, no role."""
    rc = _warm_classifier()
    role, confidence, _profile = rc.classify(
        {"kd_ratio": 1.0, "avg_adr": 80.0, "avg_kast": 0.72, "rating": 1.05}
    )
    assert confidence == 0.0
    assert role == PlayerRole.FLEX


def test_empty_dict_is_refused():
    rc = _warm_classifier()
    _role, confidence, _profile = rc.classify({})
    assert confidence == 0.0


def test_vocabulary_dict_still_classifies():
    """Real role vocabulary present → the guard must NOT block scoring."""
    rc = _warm_classifier()
    role, confidence, _profile = rc.classify(
        {
            "awp_kills": 18,
            "total_kills": 22,
            "entry_frags": 1,
            "rounds_played": 24,
            "assists": 2,
            "rounds_survived": 12,
            "solo_kills": 3,
            "kd_ratio": 1.4,
        }
    )
    assert confidence > 0.0, "vocabulary-bearing dict must be scored"
