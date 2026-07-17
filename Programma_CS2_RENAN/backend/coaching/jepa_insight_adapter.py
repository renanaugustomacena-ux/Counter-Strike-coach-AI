"""F1.1 (W5.1): JEPA → coaching-insight adapter — the integration-gap closer.

Turns the JEPA coaching head's raw output vector into axis-mapped,
maturity-gated insight candidates that the coaching chain can surface.
This is the seam the completion programme designed for F1: additive,
setting-gated (USE_JEPA_MODEL), byte-identical behaviour when off.

NO-WALLHACK (F1.3): the adapter consumes ONLY the player's own tick window
— the 25-dim POV-derived feature contract (P-X-01). No enemy ground-truth
columns exist in that contract; nothing here can leak information the
player could not have observed.

Output-range note (verify end-to-end in ST-1b — TASKS#64): the coaching
head ends in sigmoid ([0,1], WR-52) while ``_calculate_deltas`` clips its
training targets to [-1,1]; the historical record disagrees on which came
first (LOSS-02 vs WR-52). Defensively, 0.5 is treated as the neutral point
and outputs are remapped to signed deltas via ``2*(out-0.5)``; magnitudes
below _MIN_MAGNITUDE are discarded as noise either way.

Maturity gating mirrors the established confidence ladder: in ``doubt`` /
``crisis`` the JEPA contributes hedged OBSERVATIONS (0.5x confidence, one
candidate); ``learning`` speaks with 0.8x confidence (two); ``conviction``
/ ``mature`` speak plainly (1.0x, three).
"""

from dataclasses import dataclass
from typing import List, Sequence

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.jepa_insight_adapter")

# The coaching head predicts adjustment deltas for the FIRST OUTPUT_DIM (10)
# features of the 25-dim contract (TARGET_INDICES = range(OUTPUT_DIM)).
_TARGET_FEATURES = (
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
)

# feature → focus_area, using the vocabulary the analysis engines already
# emit (analysis_orchestrator CoachingInsight rows) so downstream grouping,
# UI filters and dedup treat JEPA insights as first-class citizens.
_FEATURE_AXIS = {
    "health": "survival",
    "armor": "economy",
    "has_helmet": "economy",
    "has_defuser": "economy",
    "equipment_value": "economy",
    "is_crouching": "movement",
    "is_scoped": "movement",
    "is_blinded": "utility",
    "enemies_visible": "positioning",
    "pos_x": "positioning",
}

# (increase-message, decrease-message) per feature. Wording follows the
# tutor-mode conventions: concrete, actionable, no fabricated numbers.
_FEATURE_MESSAGES = {
    "health": (
        "keep more health through mid-round — fewer risky duels early",
        "trade health more aggressively when the round demands map control",
    ),
    "armor": (
        "buy armor more consistently on viable rounds",
        "consider lighter buys when the economy needs a reset",
    ),
    "has_helmet": (
        "prioritize the helmet upgrade against rifle rounds",
        "helmet can be skipped on true eco rounds",
    ),
    "has_defuser": (
        "pick up a defuse kit more often on CT buy rounds",
        "kit spending can yield to utility on tight buys",
    ),
    "equipment_value": (
        "invest more fully when the team commits to a buy",
        "avoid over-investing on rounds the economy can't sustain",
    ),
    "is_crouching": (
        "use crouch-peeks more for stability on holds",
        "crouch less in open duels — it slows escapes",
    ),
    "is_scoped": (
        "hold scoped angles longer where sightlines reward it",
        "avoid tunnel-vision from over-scoping in close quarters",
    ),
    "is_blinded": (
        "",  # a model asking for MORE blindness is noise — dropped below
        "turn from flashes earlier and vary entry timings to eat fewer blinds",
    ),
    "enemies_visible": (
        "take more information peeks — you engage with too little intel",
        "reduce exposure — you are visible to more enemies than the duel needs",
    ),
    "pos_x": (
        "adjust default positioning toward the contested side of the map",
        "adjust default positioning away from over-extended spots",
    ),
}

# Signed-delta magnitude below which an adjustment is treated as noise.
_MIN_MAGNITUDE = 0.1

# maturity state → (confidence multiplier, max candidates, hedged tone)
_MATURITY_LADDER = {
    "doubt": (0.5, 1, True),
    "crisis": (0.5, 1, True),
    "learning": (0.8, 2, False),
    "conviction": (1.0, 3, False),
    "mature": (1.0, 3, False),
}


@dataclass(frozen=True)
class InsightCandidate:
    """One JEPA-sourced coaching suggestion, ready for the insight chain."""

    axis: str  # focus_area vocabulary (positioning/economy/…)
    message: str
    confidence: float  # maturity-scaled |delta|, in [0, 1]
    feature: str  # originating target feature
    delta: float  # signed remapped output, in [-1, 1]
    source: str = "jepa"


def deltas_to_insights(
    outputs: Sequence[float],
    maturity_state: str = "doubt",
) -> List[InsightCandidate]:
    """Map the coaching head's raw outputs to insight candidates.

    Pure function — no model, no DB, no settings. ``outputs`` are the raw
    sigmoid activations (first OUTPUT_DIM entries used); 0.5 is neutral.
    """
    conf_mult, cap, hedged = _MATURITY_LADDER.get(
        str(maturity_state).lower(), _MATURITY_LADDER["doubt"]
    )

    scored = []
    for i, feature in enumerate(_TARGET_FEATURES):
        if i >= len(outputs):
            break
        delta = 2.0 * (float(outputs[i]) - 0.5)
        if abs(delta) < _MIN_MAGNITUDE:
            continue
        inc_msg, dec_msg = _FEATURE_MESSAGES[feature]
        message = inc_msg if delta > 0 else dec_msg
        if not message:  # semantically-void direction (e.g. "be blinded more")
            continue
        scored.append((abs(delta), delta, feature, message))

    scored.sort(key=lambda t: t[0], reverse=True)

    insights: List[InsightCandidate] = []
    for magnitude, delta, feature, message in scored[:cap]:
        text = f"Observation: {message}" if hedged else message.capitalize()
        insights.append(
            InsightCandidate(
                axis=_FEATURE_AXIS[feature],
                message=text,
                confidence=round(min(1.0, magnitude * conf_mult), 4),
                feature=feature,
                delta=round(delta, 4),
            )
        )
    return insights


_MODEL_CACHE: dict = {}


def load_jepa_for_insights():
    """Load the production JEPA checkpoint once, or None (26-HYB-01 rules).

    Same discipline as the Hybrid fix: a model exists only if trained
    weights actually load (sidecar-verified via persistence.load_nn);
    FileNotFoundError / StaleCheckpointError degrade loudly to None.
    """
    if "model" in _MODEL_CACHE:
        return _MODEL_CACHE["model"]

    from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
    from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError, load_nn

    try:
        model = ModelFactory.get_model(ModelFactory.TYPE_JEPA)
        load_nn(ModelFactory.get_checkpoint_name(ModelFactory.TYPE_JEPA), model)
        model.eval()
        logger.info("F1: JEPA insight adapter armed with trained checkpoint")
        _MODEL_CACHE["model"] = model
    except FileNotFoundError:
        logger.warning("F1: no trained JEPA checkpoint — insight adapter disabled")
        _MODEL_CACHE["model"] = None
    except StaleCheckpointError as e:
        logger.warning("F1: stale JEPA checkpoint (%s) — insight adapter disabled", e)
        _MODEL_CACHE["model"] = None
    except Exception as e:
        logger.error("F1: JEPA insight adapter load failed: %s", e, exc_info=True)
        _MODEL_CACHE["model"] = None
    return _MODEL_CACHE["model"]


def generate_jepa_insights(
    tick_window,
    maturity_state: str = "doubt",
) -> List[InsightCandidate]:
    """End-to-end: player tick window → JEPA → insight candidates.

    Setting-gated (USE_JEPA_MODEL, default off — flag-off behaviour is
    byte-identical to today, F1.2). ``tick_window`` is a [T, 25] or
    [1, T, 25] array/tensor of the player's OWN ticks (NO-WALLHACK).
    Every failure degrades to an empty list, logged.
    """
    from Programma_CS2_RENAN.core.config import get_setting

    if not get_setting("USE_JEPA_MODEL", default=False):
        return []

    model = load_jepa_for_insights()
    if model is None:
        return []

    try:
        import torch

        x = torch.as_tensor(tick_window, dtype=torch.float32)
        if x.ndim == 2:
            x = x.unsqueeze(0)
        with torch.no_grad():
            outputs = model.forward_coaching(x)
        return deltas_to_insights(outputs.squeeze(0).tolist(), maturity_state)
    except Exception as e:
        logger.error("F1: JEPA insight generation failed: %s", e, exc_info=True)
        return []
