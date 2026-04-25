"""
Maturity Observatory — Layer 3 of the Coach Introspection Observatory.

Translates raw neural signals into human-interpretable maturity states:
    DOUBT      → Model is uncertain, beliefs noisy, experts not specializing
    CRISIS     → Model was confident but lost it (overfitting, data shift)
    LEARNING   → Model actively forming beliefs, experts differentiating
    CONVICTION → Strong, consistent beliefs across batches
    MATURE     → Converged, ready for production inference

Signals tracked:
    belief_entropy     — Shannon entropy of 64-dim belief vector (lower = surer)
    gate_specialization — 1 - mean_gate_activation (higher = more specialized)
    concept_focus      — 1 - entropy of concept distribution (lower entropy = focused)
    value_accuracy     — 1 - normalized prediction error (higher = better calibration)
    role_stability     — consistency of role predictions across batches

Usage:
    from Programma_CS2_RENAN.backend.nn.maturity_observatory import MaturityObservatory

    observatory = MaturityObservatory(tb_writer=writer)
    # ... pass to CallbackRegistry ...
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import torch
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.nn.training_callbacks import TrainingCallback
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.maturity")

# Maturity state thresholds
DOUBT_THRESHOLD = 0.3
LEARNING_UPPER = 0.6
CONVICTION_THRESHOLD = 0.6
CONVICTION_STABILITY = 0.05  # std over 10 epochs
MATURE_THRESHOLD = 0.75
MATURE_EPOCHS = 20
CRISIS_DROP_PCT = 0.20  # 20% drop from rolling max within 5 epochs

# Concept-temperature saturation thresholds (Phase 0 hygiene, PRE-6).
# Per CS2_Coach_Modernization_Report.pdf §8.3:
#   "Add a saturation alarm to the training callbacks: if concept_temperature
#    is within 5% of either boundary for ten consecutive epochs, log a warning
#    and investigate concept-prototype collapse via the activation histogram."
# The temperature is clamped to [0.01, 1.0] in jepa_model.py at lines 932 and
# 1000. We define "near a boundary" as within 5% of the full clamp range.
CONCEPT_TEMP_LOWER_BOUND = 0.01
CONCEPT_TEMP_UPPER_BOUND = 1.0
CONCEPT_TEMP_SATURATION_FRACTION = 0.05
CONCEPT_TEMP_SATURATION_PATIENCE = 10


@dataclass
class MaturitySnapshot:
    """Point-in-time maturity assessment of the coach."""

    epoch: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Individual maturity signals (0.0 = immature, 1.0 = mature)
    belief_entropy: float = 1.0
    gate_specialization: float = 0.0
    concept_focus: float = 0.0
    value_accuracy: float = 0.0
    role_stability: float = 0.0

    # Composite scores
    conviction_index: float = 0.0
    maturity_score: float = 0.0

    # Classification
    state: str = "doubt"

    # PRE-6: Concept-temperature monitoring (Pillar I / Section 8.3 of the
    # modernization report). Saturated → either boundary; alarm fires after
    # CONCEPT_TEMP_SATURATION_PATIENCE consecutive saturated epochs.
    concept_temperature: Optional[float] = None
    concept_temperature_saturated: bool = False
    concept_temperature_saturation_warning: bool = False


class MaturityObservatory(TrainingCallback):
    """
    Tracks coach maturation through training epochs by computing a composite
    conviction index from internal neural signals and classifying the model
    into one of five maturity states.
    """

    # Conviction index component weights
    WEIGHTS = {
        "belief_entropy": 0.25,
        "gate_specialization": 0.25,
        "concept_focus": 0.20,
        "value_accuracy": 0.20,
        "role_stability": 0.10,
    }

    # EMA smoothing for maturity score
    EMA_ALPHA = 0.3

    def __init__(self, tb_writer=None):
        self.history: List[MaturitySnapshot] = []
        self._writer = tb_writer
        self._ema_score = 0.0
        self._prev_val_loss: Optional[float] = None
        self._initial_val_loss: Optional[float] = None
        # PRE-6 saturation streak counter (consecutive epochs where the
        # concept_temperature is within 5% of either clamp boundary).
        self._concept_temp_saturation_streak: int = 0
        # One-shot latch so we don't spam the alarm log every epoch after
        # the threshold is crossed.
        self._concept_temp_warning_logged: bool = False

    # ── Lifecycle ────────────────────────────────────────────────────

    def on_epoch_end(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
        model,
        **kwargs,
    ) -> None:
        snapshot = self._compute_snapshot(epoch, val_loss, model)
        self.history.append(snapshot)

        logger.info(
            "Maturity [epoch %d]: state=%s conviction=%.3f "
            "(belief_H=%.3f gate_spec=%.3f concept_F=%.3f val_acc=%.3f)",
            epoch,
            snapshot.state,
            snapshot.conviction_index,
            snapshot.belief_entropy,
            snapshot.gate_specialization,
            snapshot.concept_focus,
            snapshot.value_accuracy,
        )

        self._log_to_tensorboard(snapshot)

    # ── Signal Extraction ────────────────────────────────────────────

    def _compute_snapshot(self, epoch: int, val_loss: float, model) -> MaturitySnapshot:
        snap = MaturitySnapshot(epoch=epoch)

        # 1. Belief Entropy
        belief = getattr(model, "_last_belief_batch", None)
        if belief is not None and isinstance(belief, torch.Tensor):
            snap.belief_entropy = self._compute_belief_entropy(belief)

        # 2. Gate Specialization
        snap.gate_specialization = self._compute_gate_specialization(model)

        # 3. Concept Focus
        snap.concept_focus = self._compute_concept_focus(model)

        # 4. Value Accuracy (proxy: val_loss relative improvement)
        snap.value_accuracy = self._compute_value_accuracy(val_loss)

        # 5. Role Stability (proxy: conviction consistency over recent epochs)
        snap.role_stability = self._compute_role_stability()

        # 6. PRE-6: concept_temperature saturation tracking. Returns the
        # current clamped value plus whether it sits inside either 5%-band.
        # Updates the consecutive-saturation streak and may flip the
        # warning latch on the snapshot.
        self._update_concept_temperature_saturation(snap, model)

        # Composite scores
        snap.conviction_index = self._compute_conviction_index(snap)

        # EMA smoothed maturity score
        self._ema_score = (
            self.EMA_ALPHA * snap.conviction_index + (1 - self.EMA_ALPHA) * self._ema_score
        )
        snap.maturity_score = self._ema_score

        # State classification
        snap.state = self._classify_state()

        return snap

    @staticmethod
    def _compute_belief_entropy(belief: torch.Tensor) -> float:
        """Shannon entropy of belief vector, normalized to [0, 1]."""
        with torch.no_grad():
            # Average over batch dimension, softmax to get probability distribution
            avg_belief = belief.mean(dim=0) if belief.dim() > 1 else belief
            probs = F.softmax(avg_belief.float(), dim=-1)
            entropy = -(probs * probs.clamp(min=1e-8).log()).sum()
            max_entropy = math.log(max(probs.shape[-1], 2))
            return float((entropy / max_entropy).clamp(0, 1).item())

    @staticmethod
    def _compute_gate_specialization(model) -> float:
        """1 - mean_gate_activation. Higher = more specialized experts."""
        strategy = getattr(model, "strategy", None)
        if strategy is None:
            return 0.0
        superposition = getattr(strategy, "superposition", None)
        if superposition is None:
            return 0.0
        stats_fn = getattr(superposition, "get_gate_statistics", None)
        if stats_fn is None:
            return 0.0
        stats = stats_fn()
        if "error" in stats:
            return 0.0
        return max(0.0, 1.0 - stats.get("mean_activation", 1.0))

    @staticmethod
    def _compute_concept_focus(model) -> float:
        """1 - normalized entropy of concept probability distribution."""
        concept_embs = getattr(model, "concept_embeddings", None)
        if concept_embs is None:
            return 0.0
        with torch.no_grad():
            norms = concept_embs.weight.data.norm(dim=1)
            probs = F.softmax(norms, dim=0)
            entropy = -(probs * probs.clamp(min=1e-8).log()).sum()
            max_entropy = math.log(max(probs.shape[0], 2))
            norm_entropy = float((entropy / max_entropy).item())
            return max(0.0, 1.0 - norm_entropy)

    def _compute_value_accuracy(self, val_loss: float) -> float:
        """Normalized val_loss improvement from initial loss."""
        if self._initial_val_loss is None:
            self._initial_val_loss = val_loss
        self._prev_val_loss = val_loss

        if self._initial_val_loss <= 0:
            return 0.5

        # Ratio of improvement: 1.0 when val_loss → 0, 0.0 when no improvement
        improvement = 1.0 - (val_loss / self._initial_val_loss)
        return float(max(0.0, min(1.0, improvement)))

    def _update_concept_temperature_saturation(self, snap: MaturitySnapshot, model) -> None:
        """Inspect ``model.concept_temperature`` and update saturation state.

        Per CS2_Coach_Modernization_Report.pdf §8.3, the concept_temperature
        on VLJEPACoachingModel is a learned scalar clamped to
        [CONCEPT_TEMP_LOWER_BOUND, CONCEPT_TEMP_UPPER_BOUND] (currently
        [0.01, 1.0] in jepa_model.py). At convergence, saturation against
        either boundary indicates a degenerate concept space:

          - lower-saturation → forced-binary classification
          - upper-saturation → uniform / non-discriminative concepts

        We define "near a boundary" as within
        ``CONCEPT_TEMP_SATURATION_FRACTION * (upper - lower)`` of either
        edge. After ``CONCEPT_TEMP_SATURATION_PATIENCE`` consecutive
        saturated epochs the warning latch flips and a one-shot
        ``logger.error`` fires; subsequent saturated epochs do not
        re-spam. A healthy epoch resets the streak (and re-arms the latch
        for future events).
        """
        temp_param = getattr(model, "concept_temperature", None)
        if temp_param is None:
            # Not a VL-JEPA model — leave fields at defaults (None / False).
            return

        with torch.no_grad():
            # Match the live clamp applied at jepa_model.py:932 so the
            # observatory sees the same value the loss does.
            value = float(
                temp_param.detach()
                .clamp(min=CONCEPT_TEMP_LOWER_BOUND, max=CONCEPT_TEMP_UPPER_BOUND)
                .item()
            )

        snap.concept_temperature = value

        band = CONCEPT_TEMP_SATURATION_FRACTION * (
            CONCEPT_TEMP_UPPER_BOUND - CONCEPT_TEMP_LOWER_BOUND
        )
        is_saturated = (
            value <= CONCEPT_TEMP_LOWER_BOUND + band or value >= CONCEPT_TEMP_UPPER_BOUND - band
        )
        snap.concept_temperature_saturated = is_saturated

        if is_saturated:
            self._concept_temp_saturation_streak += 1
        else:
            self._concept_temp_saturation_streak = 0
            # Re-arm the latch so a fresh saturation episode logs again.
            self._concept_temp_warning_logged = False

        if self._concept_temp_saturation_streak >= CONCEPT_TEMP_SATURATION_PATIENCE:
            snap.concept_temperature_saturation_warning = True
            if not self._concept_temp_warning_logged:
                edge = (
                    "lower (binary collapse)"
                    if value <= CONCEPT_TEMP_LOWER_BOUND + band
                    else "upper (uniform / non-discriminative)"
                )
                logger.error(
                    "WARN_CONCEPT_TEMPERATURE_SATURATED: concept_temperature="
                    "%.4f saturated against %s for %d consecutive epochs. "
                    "Investigate concept-prototype collapse via the activation "
                    "histogram already available in the Observatory.",
                    value,
                    edge,
                    self._concept_temp_saturation_streak,
                )
                self._concept_temp_warning_logged = True

    def _compute_role_stability(self) -> float:
        """Consistency of conviction index over recent epochs."""
        if len(self.history) < 3:
            return 0.0
        recent = [s.conviction_index for s in self.history[-10:]]
        if len(recent) < 2:
            return 0.0
        std = torch.tensor(recent).std().item()
        # Low std = high stability
        return float(max(0.0, 1.0 - std * 5))  # scale: std=0.2 → stability=0

    def _compute_conviction_index(self, snap: MaturitySnapshot) -> float:
        """Weighted composite of maturity signals."""
        return (
            self.WEIGHTS["belief_entropy"] * (1 - snap.belief_entropy)
            + self.WEIGHTS["gate_specialization"] * snap.gate_specialization
            + self.WEIGHTS["concept_focus"] * snap.concept_focus
            + self.WEIGHTS["value_accuracy"] * snap.value_accuracy
            + self.WEIGHTS["role_stability"] * snap.role_stability
        )

    # ── State Machine ────────────────────────────────────────────────

    def _classify_state(self) -> str:
        """
        Classify current maturity state from recent history.

        States:
            DOUBT:      conviction < 0.3, decreasing trend
            CRISIS:     conviction drops >20% from rolling max in 5 epochs
            LEARNING:   conviction 0.3-0.6, increasing trend
            CONVICTION: conviction > 0.6, stable (std < 0.05 over 10 epochs)
            MATURE:     conviction > 0.75, stable for 20+ epochs,
                        value_accuracy > 0.7, gate_specialization > 0.5
        """
        if len(self.history) < 2:
            return "doubt"

        recent = self.history[-5:]
        current = recent[-1]
        conv = current.conviction_index

        # Check for CRISIS: sharp drop from recent max
        recent_max = max(s.conviction_index for s in self.history[-10:])
        if recent_max > 0.3 and conv < recent_max * (1 - CRISIS_DROP_PCT):
            return "crisis"

        # Check for MATURE
        if (
            conv > MATURE_THRESHOLD
            and len(self.history) >= MATURE_EPOCHS
            and current.value_accuracy > 0.7
            and current.gate_specialization > 0.5
        ):
            long_recent = [s.conviction_index for s in self.history[-MATURE_EPOCHS:]]
            if torch.tensor(long_recent).std().item() < CONVICTION_STABILITY:
                return "mature"

        # Check for CONVICTION
        if conv > CONVICTION_THRESHOLD:
            if len(self.history) >= 10:
                recent_conv = [s.conviction_index for s in self.history[-10:]]
                if torch.tensor(recent_conv).std().item() < CONVICTION_STABILITY:
                    return "conviction"
            return "learning"  # High but not yet stable → still learning

        # Check for LEARNING (increasing trend)
        if conv > DOUBT_THRESHOLD:
            trend = [s.conviction_index for s in recent]
            if len(trend) >= 2 and trend[-1] >= trend[0]:
                return "learning"

        return "doubt"

    # ── TensorBoard Integration ──────────────────────────────────────

    def _log_to_tensorboard(self, snap: MaturitySnapshot) -> None:
        if self._writer is None:
            return

        epoch = snap.epoch
        self._writer.add_scalar("maturity/belief_entropy", snap.belief_entropy, epoch)
        self._writer.add_scalar("maturity/gate_specialization", snap.gate_specialization, epoch)
        self._writer.add_scalar("maturity/concept_focus", snap.concept_focus, epoch)
        self._writer.add_scalar("maturity/value_accuracy", snap.value_accuracy, epoch)
        self._writer.add_scalar("maturity/role_stability", snap.role_stability, epoch)
        self._writer.add_scalar("maturity/conviction_index", snap.conviction_index, epoch)
        self._writer.add_scalar("maturity/maturity_score", snap.maturity_score, epoch)
        self._writer.add_text("maturity/state", snap.state, epoch)

    # ── Public API ───────────────────────────────────────────────────

    @property
    def current_state(self) -> str:
        """Current maturity state label."""
        return self.history[-1].state if self.history else "unknown"

    @property
    def current_conviction(self) -> float:
        """Current conviction index."""
        return self.history[-1].conviction_index if self.history else 0.0

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Export maturity timeline for external consumption."""
        return [
            {
                "epoch": s.epoch,
                "state": s.state,
                "conviction_index": round(s.conviction_index, 4),
                "maturity_score": round(s.maturity_score, 4),
                "belief_entropy": round(s.belief_entropy, 4),
                "gate_specialization": round(s.gate_specialization, 4),
            }
            for s in self.history
        ]
