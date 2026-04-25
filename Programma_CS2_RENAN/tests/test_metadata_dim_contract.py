"""ContractGuard for METADATA_DIM=25 (P-X-01).

Per CLAUDE.md and the modernization report (Section 9), METADATA_DIM is
referenced across ~331 modules and is the single binding contract between
the feature pipeline and every neural network input layer (JEPA encoder,
RAP perception layer, AdvancedCoachNN, VL-JEPA concept head, role heads).

A change to METADATA_DIM, or to the order of FEATURE_NAMES, is a structural
break with:
  - all serialized model checkpoints (input_dim mismatch),
  - the EMA target encoder shadow params,
  - the JEPA pre-training data tensors (shape mismatch on load),
  - the per-axis position loss (Pillar III: σ_z reads map_id by index).

This test FAILS if any of those invariants drift. A deliberate change to
the dimension must be accompanied — in the same commit — by:
  (a) an update to EXPECTED_METADATA_DIM / EXPECTED_FEATURE_NAMES below,
  (b) a migration_manifest_<ts>.md at the repo root documenting the
      retraining plan and downstream impact,
  (c) an Alembic migration if the change touches stored tensors.

The test is intentionally rigid. A passing CI run on this file is the
last line of defense before the contract drifts silently.
"""

from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
    FEATURE_NAMES,
    METADATA_DIM,
)

# Hard-pinned canonical contract — see vectorizer.py:151-181 and the
# `Feature Order` docstring at vectorizer.py:194-219.
EXPECTED_METADATA_DIM = 25

EXPECTED_FEATURE_NAMES: tuple = (
    "health",
    "armor",
    "has_helmet",
    "has_defuser",
    "equipment_value",
    "is_crouching",
    "is_scoped",
    "is_blinded",
    "enemies_visible",
    "pos_x",
    "pos_y",
    "pos_z",
    "view_yaw_sin",
    "view_yaw_cos",
    "view_pitch",
    "z_penalty",
    "kast_estimate",
    "map_id",
    "round_phase",
    "weapon_class",
    "time_in_round",
    "bomb_planted",
    "teammates_alive",
    "enemies_alive",
    "team_economy",
)


def test_metadata_dim_is_25():
    """The contract dim is exactly 25; any change is a structural break."""
    assert METADATA_DIM == EXPECTED_METADATA_DIM, (
        f"METADATA_DIM drifted from {EXPECTED_METADATA_DIM} to {METADATA_DIM}. "
        "Update EXPECTED_METADATA_DIM in this test and ship a "
        "migration_manifest_<ts>.md describing the retraining plan."
    )


def test_feature_names_length_matches_dim():
    """FEATURE_NAMES tuple length must equal METADATA_DIM (P-X-01)."""
    assert len(FEATURE_NAMES) == METADATA_DIM, (
        f"FEATURE_NAMES has {len(FEATURE_NAMES)} entries; "
        f"METADATA_DIM={METADATA_DIM}. The vectorizer.py:178 assert should "
        "have caught this at import time — investigate."
    )


def test_feature_names_canonical_order():
    """Feature order is positional: downstream code reads features by index.

    Reordering breaks every trained checkpoint and any code path that does
    ``vec[i]`` rather than ``vec[FEATURE_NAMES.index('name')]``.
    """
    assert FEATURE_NAMES == EXPECTED_FEATURE_NAMES, (
        f"FEATURE_NAMES order drifted.\n"
        f"  expected: {EXPECTED_FEATURE_NAMES}\n"
        f"  got:      {FEATURE_NAMES}\n"
        "Update EXPECTED_FEATURE_NAMES, ship a migration manifest, and "
        "retrain — every persisted model and tick-state row is keyed on "
        "this order."
    )


def test_map_id_at_index_17():
    """map_id index is load-bearing for Pillar III's per-axis position loss.

    Per CS2_Coach_Modernization_Report.pdf §5.3 and §8.4, the proposed
    σ_z(map_id) gate reads ``feature_vec[17]`` directly. Moving map_id
    breaks the per-map verticality prior without raising any error at
    training time — silent corruption.
    """
    assert FEATURE_NAMES[17] == "map_id", (
        f"map_id is at index {FEATURE_NAMES.index('map_id')}, "
        "expected 17. Per-axis position loss in rap_coach/trainer.py reads "
        "feature_vec[17] for the σ_z gate."
    )


def test_no_duplicate_feature_names():
    """Defensive: a duplicate would still pass the length check but break
    any name-based lookup downstream.
    """
    assert len(set(FEATURE_NAMES)) == len(FEATURE_NAMES), (
        f"Duplicate names in FEATURE_NAMES: "
        f"{[n for n in FEATURE_NAMES if FEATURE_NAMES.count(n) > 1]}"
    )
