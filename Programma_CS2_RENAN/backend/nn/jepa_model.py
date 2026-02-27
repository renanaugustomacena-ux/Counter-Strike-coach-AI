"""
JEPA-Enhanced Coaching Model

Joint-Embedding Predictive Architecture for CS2 coaching.
This is an ADDITIVE feature that coexists with the existing AdvancedCoachNN.

Architecture:
    Stage 1: JEPA Pre-training (self-supervised on pro demos)
    Stage 2: LSTM Fine-tuning (supervised on user data)

References:
    - GEMINI.md: Energy-Based Models, Temporal Prediction
    - GEMINI.md: VL-JEPA Selective Decoding
    - Yann LeCun's JEPA paper (2023)
"""

from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class JEPAEncoder(nn.Module):
    """
    Vision Transformer-style encoder for match state embeddings.

    Adheres to GEMINI.md principles:
    - LayerNorm for gradient stability
    - GELU activation (smooth, differentiable)
    - Residual connections
    """

    def __init__(self, input_dim: int, latent_dim: int = 256):
        super().__init__()

        self.projection = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(512, latent_dim),
            nn.LayerNorm(latent_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode match state to latent space.

        Args:
            x: Match features [batch, seq_len, input_dim]

        Returns:
            Latent embeddings [batch, seq_len, latent_dim]
        """
        return self.projection(x)


class JEPAPredictor(nn.Module):
    """
    Predicts target embeddings from context embeddings.

    This is the core of JEPA: predict in latent space, not observation space.
    """

    def __init__(self, latent_dim: int = 256):
        super().__init__()

        self.predictor = nn.Sequential(
            nn.Linear(latent_dim, latent_dim * 2),
            nn.LayerNorm(latent_dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(latent_dim * 2, latent_dim),
        )

    def forward(self, context_embedding: torch.Tensor) -> torch.Tensor:
        """
        Predict future state embedding from current context.

        Args:
            context_embedding: Context latent [batch, latent_dim]

        Returns:
            Predicted target embedding [batch, latent_dim]
        """
        return self.predictor(context_embedding)


class JEPACoachingModel(nn.Module):
    """
    Hybrid JEPA-LSTM model for CS2 coaching.

    This is a NEW model that does NOT replace AdvancedCoachNN.
    Both models can coexist and be selected via config.

    Training Pipeline:
        1. Pre-train JEPA on pro demos (self-supervised)
        2. Freeze encoders
        3. Fine-tune LSTM on user data (supervised)
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        latent_dim: int = 256,
        hidden_dim: int = 128,
        num_experts: int = 3,
    ):
        super().__init__()

        # JEPA Components (for pre-training)
        self.context_encoder = JEPAEncoder(input_dim, latent_dim)
        self.target_encoder = JEPAEncoder(input_dim, latent_dim)
        self.predictor = JEPAPredictor(latent_dim)

        # LSTM Coaching Head (similar to existing AdvancedCoachNN)
        self.lstm = nn.LSTM(latent_dim, hidden_dim, batch_first=True, num_layers=2, dropout=0.2)

        # Mixture of Experts (existing architecture)
        self.experts = nn.ModuleList(
            [self._create_expert(hidden_dim, output_dim) for _ in range(num_experts)]
        )

        self.gate = nn.Sequential(nn.Linear(hidden_dim, num_experts), nn.Softmax(dim=-1))

        self.latent_dim = latent_dim
        self.is_pretrained = False

    def forward(self, x: torch.Tensor, role_id: Optional[int] = None) -> torch.Tensor:
        """
        Default forward pass (calls coaching inference).

        Args:
            x: Match features [batch, seq_len, input_dim]
            role_id: Optional role bias for MoE gating

        Returns:
            Coaching predictions [batch, output_dim]
        """
        return self.forward_coaching(x, role_id)

    def _create_expert(self, h_dim: int, o_dim: int) -> nn.Module:
        """Create expert network (same as AdvancedCoachNN)."""
        return nn.Sequential(nn.Linear(h_dim, h_dim), nn.ReLU(), nn.Linear(h_dim, o_dim))

    def forward_jepa_pretrain(
        self, x_context: torch.Tensor, x_target: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        JEPA pre-training forward pass.

        Args:
            x_context: Context window [batch, context_len, input_dim]
            x_target: Target window [batch, target_len, input_dim]

        Returns:
            (predicted_embedding, target_embedding)
        """
        # Encode context and target
        s_context = self.context_encoder(x_context)
        s_target = self.target_encoder(x_target)

        # Average pool over sequence
        s_context_pooled = s_context.mean(dim=1)
        s_target_pooled = s_target.mean(dim=1)

        # Predict target embedding from context
        s_target_pred = self.predictor(s_context_pooled)

        return s_target_pred, s_target_pooled

    def forward_coaching(self, x: torch.Tensor, role_id: Optional[int] = None) -> torch.Tensor:
        """
        Coaching inference (after pre-training).

        Args:
            x: Match features [batch, seq_len, input_dim]
            role_id: Optional role bias for MoE gating

        Returns:
            Coaching predictions [batch, output_dim]
        """
        # Encode to latent space (frozen after pre-training)
        with torch.no_grad() if self.is_pretrained else torch.enable_grad():
            embeddings = self.context_encoder(x)

        # LSTM processing
        lstm_out, _ = self.lstm(embeddings)
        last_hidden = lstm_out[:, -1, :]

        # MoE gating
        gate_weights = self.gate(last_hidden)

        if role_id is not None:
            gate_weights = self._apply_role_bias(gate_weights, role_id)

        # Compute expert outputs
        expert_outputs = torch.stack([expert(last_hidden) for expert in self.experts], dim=1)

        # Weighted combination
        output = torch.sum(expert_outputs * gate_weights.unsqueeze(-1), dim=1)

        return torch.tanh(output)

    def forward_selective(
        self,
        x: torch.Tensor,
        prev_embedding: Optional[torch.Tensor] = None,
        threshold: float = 0.05,
        role_id: Optional[int] = None,
    ) -> Tuple[Optional[torch.Tensor], torch.Tensor, bool]:
        """
        Inference with Selective Decoding (VL-JEPA optimization).

        Adheres to GEMINI.md:
        - "VL-JEPA natively supports selective decoding that reduces the number of decoding operations"
        - "Decoding happens only due to significant change in the predicted embedding stream"

        Args:
            x: Input features [batch, seq_len, input_dim]
            prev_embedding: Latent embedding from previous step [batch, seq_len, latent_dim]
            threshold: Cosine distance threshold (0.0 - 2.0) to trigger decoding
            role_id: Optional role bias for MoE

        Returns:
            (prediction, current_embedding, did_decode)
            prediction is None if did_decode is False.
        """
        # 1. Encode to latent space (Lightweight X-Encoder)
        with torch.no_grad() if self.is_pretrained else torch.enable_grad():
            curr_embedding = self.context_encoder(x)

        # 2. Check for significant change (Selective Decoding)
        should_decode = True
        if prev_embedding is not None:
            # Pool to get global state vector (s_context_pooled)
            curr_pooled = curr_embedding.mean(dim=1)
            prev_pooled = prev_embedding.mean(dim=1)

            # Cosine distance: 1 - similarity
            # High similarity (approx 1.0) -> Low distance (approx 0.0)
            similarity = F.cosine_similarity(curr_pooled, prev_pooled, dim=-1)
            distance = 1.0 - similarity

            # If distance is small, state hasn't changed enough to warrant re-decoding
            # We use .all() because we are in batch mode, but typically inference is batch=1
            # For batch > 1, we decode if ANY sample changed significantly, or handle individually.
            # Here we assume batch processing: if average distance < threshold, skip.
            if distance.mean().item() < threshold:
                should_decode = False

        # 3. Decode if necessary (Heavy Predictor/Decoder)
        prediction = None
        if should_decode:
            # LSTM processing (Temporal Modeling)
            lstm_out, _ = self.lstm(curr_embedding)
            last_hidden = lstm_out[:, -1, :]

            # MoE gating
            gate_weights = self.gate(last_hidden)

            if role_id is not None:
                gate_weights = self._apply_role_bias(gate_weights, role_id)

            # Expert execution
            expert_outputs = torch.stack([expert(last_hidden) for expert in self.experts], dim=1)

            # Weighted combination
            output = torch.sum(expert_outputs * gate_weights.unsqueeze(-1), dim=1)
            prediction = torch.tanh(output)

        return prediction, curr_embedding, should_decode

    def _apply_role_bias(self, gate_weights: torch.Tensor, role_id: int) -> torch.Tensor:
        """Apply role bias to gating (same as AdvancedCoachNN)."""
        role_id = max(0, min(int(role_id), len(self.experts) - 1))

        role_bias = torch.zeros_like(gate_weights)
        role_bias[:, role_id] = 1.0

        return (gate_weights + role_bias) / 2.0

    def freeze_encoders(self):
        """Freeze JEPA encoders after pre-training."""
        for param in self.context_encoder.parameters():
            param.requires_grad = False
        for param in self.target_encoder.parameters():
            param.requires_grad = False

        self.is_pretrained = True

    def unfreeze_encoders(self):
        """Unfreeze encoders for end-to-end fine-tuning."""
        for param in self.context_encoder.parameters():
            param.requires_grad = True
        for param in self.target_encoder.parameters():
            param.requires_grad = True

        self.is_pretrained = False

    def update_target_encoder(self, momentum: float = 0.996):
        """
        EMA update for target encoder (I-JEPA / BYOL style).

        target_weights = momentum * target_weights + (1 - momentum) * context_weights

        Args:
            momentum: EMA decay rate (typically 0.99 - 0.999)
        """
        with torch.no_grad():
            for param_q, param_k in zip(
                self.context_encoder.parameters(), self.target_encoder.parameters()
            ):
                param_k.data = param_k.data * momentum + param_q.data * (1.0 - momentum)


def jepa_contrastive_loss(
    pred: torch.Tensor, target: torch.Tensor, negatives: torch.Tensor, temperature: float = 0.07
) -> torch.Tensor:
    """
    InfoNCE contrastive loss for JEPA pre-training.

    From GEMINI.md: Energy-Based Models
    E(x, y) = ||s_x(x) - s_y(y)||²

    Args:
        pred: Predicted embeddings [batch, latent_dim]
        target: Target embeddings [batch, latent_dim]
        negatives: Negative samples [batch, num_negatives, latent_dim]
        temperature: Softmax temperature

    Returns:
        Contrastive loss scalar
    """
    # Normalize embeddings
    pred = F.normalize(pred, dim=-1)
    target = F.normalize(target, dim=-1)
    negatives = F.normalize(negatives, dim=-1)

    # Positive similarity
    pos_sim = (pred * target).sum(dim=-1) / temperature

    # Negative similarities
    neg_sim = torch.bmm(negatives, pred.unsqueeze(-1)).squeeze(-1) / temperature

    # InfoNCE: -log(exp(pos) / (exp(pos) + sum(exp(neg))))
    logits = torch.cat([pos_sim.unsqueeze(1), neg_sim], dim=1)
    labels = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)

    return F.cross_entropy(logits, labels)


# ═══════════════════════════════════════════════════════════════════════
# VL-JEPA: Coaching Concept Alignment (Proposal 8)
#
# Extends JEPACoachingModel with a concept alignment head that maps
# latent embeddings to interpretable coaching concept activations.
# Inspired by Meta FAIR's VL-JEPA (2026) vision-language alignment.
# ═══════════════════════════════════════════════════════════════════════

from dataclasses import dataclass
from typing import Dict, List

NUM_COACHING_CONCEPTS = 16


@dataclass(frozen=True)
class CoachingConcept:
    """An interpretable coaching concept with its taxonomy metadata."""

    id: int
    name: str
    dimension: str
    description: str


COACHING_CONCEPTS: List[CoachingConcept] = [
    # Positioning (0-2)
    CoachingConcept(
        0,
        "positioning_aggressive",
        "positioning",
        "Player takes close-range fights and pushes angles",
    ),
    CoachingConcept(
        1, "positioning_passive", "positioning", "Player holds long-range angles and avoids contact"
    ),
    CoachingConcept(
        2,
        "positioning_exposed",
        "positioning",
        "Player is in a vulnerable position with high death probability",
    ),
    # Utility (3-4)
    CoachingConcept(
        3,
        "utility_effective",
        "utility",
        "Utility usage creates significant information or area denial advantage",
    ),
    CoachingConcept(
        4, "utility_wasteful", "utility", "Utility is unused at death or deployed with low impact"
    ),
    # Decision (5-6, 11-12)
    CoachingConcept(
        5, "economy_efficient", "decision", "Equipment value aligns with round type expectations"
    ),
    CoachingConcept(
        6,
        "economy_wasteful",
        "decision",
        "Force-buying into unfavorable rounds or dying with expensive gear",
    ),
    # Engagement (7-10)
    CoachingConcept(
        7,
        "engagement_favorable",
        "engagement",
        "Taking fights with HP, position, or numbers advantage",
    ),
    CoachingConcept(
        8,
        "engagement_unfavorable",
        "engagement",
        "Taking fights while outnumbered, low HP, or poorly positioned",
    ),
    CoachingConcept(
        9,
        "trade_responsive",
        "engagement",
        "Quickly trading teammate deaths, good team coordination",
    ),
    CoachingConcept(
        10, "trade_isolated", "engagement", "Dying without trades, playing too far from teammates"
    ),
    # Decision continued
    CoachingConcept(
        11, "rotation_fast", "decision", "Quick positional rotation after receiving information"
    ),
    CoachingConcept(
        12, "information_gathered", "decision", "Good intel gathering, multiple enemies spotted"
    ),
    # Psychology (13-15)
    CoachingConcept(
        13, "momentum_leveraged", "psychology", "Capitalizing on hot streaks with confident plays"
    ),
    CoachingConcept(
        14, "clutch_composed", "psychology", "Calm decision-making in 1vN clutch situations"
    ),
    CoachingConcept(
        15,
        "aggression_calibrated",
        "psychology",
        "Aggression level appropriately matches the situation",
    ),
]

CONCEPT_NAMES = [c.name for c in COACHING_CONCEPTS]


class ConceptLabeler:
    """
    Generates soft coaching concept labels from the 25-dim feature vector.

    Uses heuristic rules derived from the same features the model sees,
    producing [NUM_COACHING_CONCEPTS] soft labels in [0, 1] per tick.
    Multi-label: a tick can activate multiple concepts simultaneously.

    Feature index reference (from FeatureExtractor, METADATA_DIM=25):
        0: health/100,   1: armor/100,    2: has_helmet,     3: has_defuser,
        4: equip/10000,  5: is_crouching, 6: is_scoped,      7: is_blinded,
        8: enemies_vis,  9: pos_x/4096,  10: pos_y/4096,    11: pos_z/1024,
       12: view_x_sin,  13: view_x_cos,  14: view_y/90,     15: z_penalty,
       16: kast_est,    17: map_id,      18: round_phase,
       19: weapon_class, 20: time_in_round/115, 21: bomb_planted,
       22: teammates_alive/4, 23: enemies_alive/5, 24: team_economy/16000
    """

    # Feature indices — original 19
    _HP = 0
    _ARMOR = 1
    _HELMET = 2
    _EQUIP = 4
    _CROUCHING = 5
    _SCOPED = 6
    _BLINDED = 7
    _ENEMIES_VIS = 8
    _KAST = 16
    _ROUND_PHASE = 18
    # Feature indices — new 6 added when METADATA_DIM was upgraded 19 → 25
    _WEAPON_CLASS = 19    # Normalised weapon class (e.g. AWP=0.9, rifle=0.7, pistol=0.3)
    _TIME_IN_ROUND = 20   # Elapsed round time / 115 s
    _BOMB_PLANTED = 21    # 0/1 flag
    _TEAMMATES_ALIVE = 22  # alive_ct_or_t / 4.0
    _ENEMIES_ALIVE = 23   # alive_opponents / 5.0
    _TEAM_ECONOMY = 24    # team equip value / 16000

    def label_tick(self, features: torch.Tensor) -> torch.Tensor:
        """
        Generate soft concept labels from a single tick's 25-dim features.

        Args:
            features: [25] tensor of normalized features (METADATA_DIM=25).

        Returns:
            [NUM_COACHING_CONCEPTS] soft labels in [0, 1].
        """
        labels = torch.zeros(NUM_COACHING_CONCEPTS)

        # Original 19 features
        hp = features[self._HP].item()
        armor = features[self._ARMOR].item()
        equip = features[self._EQUIP].item()
        crouching = features[self._CROUCHING].item()
        scoped = features[self._SCOPED].item()
        blinded = features[self._BLINDED].item()
        enemies_vis = features[self._ENEMIES_VIS].item()
        kast = features[self._KAST].item()
        round_phase = features[self._ROUND_PHASE].item()
        # New 6 features (indices 19-24, zero when not available from DB-only tick)
        weapon_class = features[self._WEAPON_CLASS].item() if features.shape[0] > 19 else 0.0
        time_in_round = features[self._TIME_IN_ROUND].item() if features.shape[0] > 20 else 0.0
        bomb_planted = features[self._BOMB_PLANTED].item() if features.shape[0] > 21 else 0.0
        teammates = features[self._TEAMMATES_ALIVE].item() if features.shape[0] > 22 else 1.0
        enemies = features[self._ENEMIES_ALIVE].item() if features.shape[0] > 23 else 1.0
        team_econ = features[self._TEAM_ECONOMY].item() if features.shape[0] > 24 else 0.0

        # 0: positioning_aggressive — not crouching, not scoped, seeing enemies
        if crouching <= 0.5 and scoped <= 0.5 and enemies_vis > 0.4:
            labels[0] = min(0.5 + enemies_vis, 1.0)

        # 1: positioning_passive — crouching or scoped, holding angle
        if crouching > 0.5 or scoped > 0.5:
            labels[1] = 0.6 + 0.2 * scoped + 0.2 * crouching

        # 2: positioning_exposed — low HP, enemies visible, not in cover;
        # late-round bomb pressure amplifies exposure (bomb_planted=1.0)
        if hp < 0.4 and enemies_vis > 0.2:
            labels[2] = (1.0 - hp) * 0.8 + enemies_vis * 0.2 + bomb_planted * 0.1

        # 3: utility_effective — enemies visible after utility (proxy: many enemies seen)
        if enemies_vis > 0.6:
            labels[3] = min(enemies_vis, 1.0)

        # 4: utility_wasteful — blinded (own flash?) or low KAST with no visible enemies
        if blinded > 0.5:
            labels[4] = 0.6
        elif enemies_vis < 0.1 and kast < 0.3:
            labels[4] = 0.4

        # 5: economy_efficient — equip matches round phase; also check team_econ alignment
        if round_phase < 0.2:  # pistol
            labels[5] = 0.7 if equip < 0.15 else 0.3
        elif round_phase > 0.8:  # full buy
            labels[5] = 0.7 if equip > 0.3 else 0.3
        else:
            labels[5] = 0.5
        # Boost if team economy is also aligned (consistent eco or buy)
        if team_econ > 0.0:
            labels[5] = min(labels[5].item() + 0.1 * team_econ, 1.0)

        # 6: economy_wasteful — high equip in eco/pistol or low equip in full buy
        if round_phase < 0.2 and equip > 0.3:
            labels[6] = 0.7
        elif round_phase > 0.8 and equip < 0.15:
            labels[6] = 0.6

        # 7: engagement_favorable — high HP + armor + enemies visible;
        # numerical advantage (more teammates than enemies) amplifies signal
        if hp > 0.7 and armor > 0.5 and enemies_vis > 0.2:
            advantage = max(0.0, teammates - enemies)
            labels[7] = hp * 0.4 + armor * 0.3 + enemies_vis * 0.2 + advantage * 0.1

        # 8: engagement_unfavorable — low HP or blinded with enemies;
        # numerical disadvantage worsens it
        if hp < 0.3 and enemies_vis > 0.2:
            outnumbered = max(0.0, enemies - teammates)
            labels[8] = (1.0 - hp) * 0.6 + enemies_vis * 0.3 + outnumbered * 0.1
        elif blinded > 0.5 and enemies_vis > 0.2:
            labels[8] = 0.7

        # 9: trade_responsive — high KAST (proxy for team play)
        if kast > 0.7:
            labels[9] = kast

        # 10: trade_isolated — low KAST
        if kast < 0.3:
            labels[10] = 1.0 - kast

        # 11: rotation_fast — mobile player (not crouching/scoped);
        # early round with time remaining = higher rotation signal
        if crouching <= 0.5 and scoped <= 0.5:
            labels[11] = 0.4 + (1.0 - time_in_round) * 0.2

        # 12: information_gathered — many enemies visible
        if enemies_vis > 0.4:
            labels[12] = min(enemies_vis * 1.5, 1.0)

        # 13: momentum_leveraged — high KAST + full buy (confident play);
        # AWP-class weapon (weapon_class ≈ 0.9) with buy rounds boosts signal
        if kast > 0.6 and round_phase > 0.6:
            awp_bonus = 0.1 if weapon_class > 0.8 else 0.0
            labels[13] = kast * 0.6 + round_phase * 0.4 + awp_bonus

        # 14: clutch_composed — few enemies visible, player alive, post-bomb-plant
        # bomb_planted context is now available
        if hp > 0.3 and enemies_vis > 0.2 and enemies_vis < 0.5:
            labels[14] = 0.4 + bomb_planted * 0.2

        # 15: aggression_calibrated — HP matches engagement level
        if hp > 0.6 and enemies_vis > 0.3:
            labels[15] = 0.5 + hp * 0.3
        elif hp < 0.3 and enemies_vis < 0.1:
            labels[15] = 0.5  # passive when hurt = calibrated

        return labels

    def label_batch(self, features_batch: torch.Tensor) -> torch.Tensor:
        """
        Generate concept labels for a batch of ticks.

        Args:
            features_batch: [batch, 25] or [batch, seq_len, 25]

        Returns:
            [batch, NUM_COACHING_CONCEPTS] soft labels (averaged over seq if 3D).
        """
        if features_batch.dim() == 3:
            # Average labels across sequence
            batch_size, seq_len, _ = features_batch.shape
            all_labels = torch.zeros(batch_size, NUM_COACHING_CONCEPTS)
            for b in range(batch_size):
                seq_labels = torch.stack(
                    [self.label_tick(features_batch[b, t]) for t in range(seq_len)]
                )
                all_labels[b] = seq_labels.mean(dim=0)
            return all_labels
        else:
            return torch.stack(
                [self.label_tick(features_batch[i]) for i in range(features_batch.size(0))]
            )


class VLJEPACoachingModel(JEPACoachingModel):
    """
    Vision-Language aligned JEPA with coaching concept grounding.

    Extends JEPACoachingModel with a concept alignment head that maps
    latent embeddings to interpretable coaching concept activations.
    All parent forward paths (forward, forward_coaching, forward_selective,
    forward_jepa_pretrain) are preserved unchanged via inheritance.

    New path: forward_vl() returns concept probabilities alongside
    standard coaching output.
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        latent_dim: int = 256,
        hidden_dim: int = 128,
        num_experts: int = 3,
        num_concepts: int = NUM_COACHING_CONCEPTS,
    ):
        super().__init__(input_dim, output_dim, latent_dim, hidden_dim, num_experts)

        self.num_concepts = num_concepts

        # Learnable concept prototype embeddings
        self.concept_embeddings = nn.Embedding(num_concepts, latent_dim)

        # Alignment head: projects encoder output into concept-aligned space
        self.concept_projector = nn.Sequential(
            nn.Linear(latent_dim, latent_dim),
            nn.GELU(),
            nn.Linear(latent_dim, latent_dim),
        )

        # Learned temperature for concept similarity scaling
        self.concept_temperature = nn.Parameter(torch.tensor(0.07))

    def forward_vl(
        self,
        x: torch.Tensor,
        role_id: Optional[int] = None,
    ) -> Dict:
        """
        VL-JEPA forward pass with coaching concept alignment.

        Args:
            x: Match features [batch, seq_len, input_dim]
            role_id: Optional role bias for MoE gating

        Returns:
            Dict with keys:
                concept_probs: [batch, num_concepts] softmax probabilities
                concept_logits: [batch, num_concepts] raw similarity scores
                top_concepts: List of (concept_name, probability) tuples for batch[0]
                coaching_output: [batch, output_dim] standard coaching prediction
                latent: [batch, latent_dim] pooled encoder embedding
        """
        # 1. Encode to latent space
        with torch.no_grad() if self.is_pretrained else torch.enable_grad():
            embeddings = self.context_encoder(x)

        # 2. Pool over sequence → [batch, latent_dim]
        latent = embeddings.mean(dim=1)

        # 3. Project into concept-aligned space
        projected = self.concept_projector(latent)
        projected = F.normalize(projected, dim=-1)

        # 4. Compute similarity against all concept embeddings
        concept_embs = self.concept_embeddings.weight  # [num_concepts, latent_dim]
        concept_embs_norm = F.normalize(concept_embs, dim=-1)

        # Cosine similarity: [batch, num_concepts]
        concept_logits = torch.mm(projected, concept_embs_norm.t())

        # 5. Scale by learned temperature
        temp = self.concept_temperature.clamp(min=0.01, max=1.0)
        concept_logits_scaled = concept_logits / temp
        concept_probs = F.softmax(concept_logits_scaled, dim=-1)

        # 6. Standard coaching output via parent
        coaching_output = self.forward_coaching(x, role_id)

        # 7. Decode top concepts for interpretability
        top_concepts = self._decode_top_concepts(concept_probs, k=3)

        return {
            "concept_probs": concept_probs,
            "concept_logits": concept_logits,
            "top_concepts": top_concepts,
            "coaching_output": coaching_output,
            "latent": latent,
        }

    def _decode_top_concepts(
        self,
        probs: torch.Tensor,
        k: int = 3,
    ) -> List[tuple]:
        """
        Decode top-k coaching concepts from probability distribution.

        Args:
            probs: [batch, num_concepts] concept probabilities
            k: Number of top concepts to return

        Returns:
            List of (concept_name, probability) for the first sample in batch.
        """
        k = min(k, self.num_concepts)
        top_k = torch.topk(probs[0], k, dim=-1)
        return [
            (CONCEPT_NAMES[idx.item()], prob.item())
            for idx, prob in zip(top_k.indices, top_k.values)
        ]

    def get_concept_activations(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        """
        Lightweight concept-only forward (no coaching head, no LSTM).

        Args:
            x: Match features [batch, seq_len, input_dim]

        Returns:
            [batch, num_concepts] concept probabilities
        """
        with torch.no_grad():
            embeddings = self.context_encoder(x)
            latent = embeddings.mean(dim=1)
            projected = self.concept_projector(latent)
            projected = F.normalize(projected, dim=-1)

            concept_embs = F.normalize(self.concept_embeddings.weight, dim=-1)
            logits = torch.mm(projected, concept_embs.t())
            temp = self.concept_temperature.clamp(min=0.01, max=1.0)
            return F.softmax(logits / temp, dim=-1)


def vl_jepa_concept_loss(
    concept_logits: torch.Tensor,
    concept_labels: torch.Tensor,
    concept_embeddings: torch.Tensor,
    alpha: float = 0.5,
    beta: float = 0.1,
) -> tuple:
    """
    VL-JEPA concept alignment loss with diversity regularization.

    Args:
        concept_logits: [batch, num_concepts] raw similarity scores (pre-softmax)
        concept_labels: [batch, num_concepts] soft heuristic labels in [0, 1]
        concept_embeddings: [num_concepts, latent_dim] concept embedding weights
        alpha: Weight for concept alignment loss
        beta: Weight for diversity regularization

    Returns:
        (total_loss, concept_loss, diversity_loss) tuple
    """
    # Multi-label BCE: each concept is independently activated
    concept_loss = F.binary_cross_entropy_with_logits(concept_logits, concept_labels)

    # VICReg-inspired diversity: prevent concept embedding collapse
    # Each concept embedding should have high variance across the latent dim
    # std across concepts for each dimension → penalize low std
    emb_norm = F.normalize(concept_embeddings, dim=-1)
    std_per_dim = emb_norm.std(dim=0)  # [latent_dim]
    diversity_loss = -std_per_dim.mean()  # Higher std = lower loss

    total = alpha * concept_loss + beta * diversity_loss

    return total, concept_loss, diversity_loss


if __name__ == "__main__":
    # Self-test
    from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

    print("=== JEPA Model Test ===\n")

    # Model initialization
    model = JEPACoachingModel(
        input_dim=METADATA_DIM, output_dim=METADATA_DIM, latent_dim=128, hidden_dim=64
    )

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(
        f"Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}\n"
    )

    # Test JEPA pre-training
    batch_size = 4
    context_len = 10
    target_len = 10

    x_context = torch.randn(batch_size, context_len, METADATA_DIM)
    x_target = torch.randn(batch_size, target_len, METADATA_DIM)

    pred, target = model.forward_jepa_pretrain(x_context, x_target)
    print(f"JEPA pre-train output: pred={pred.shape}, target={target.shape}")

    # Test coaching inference
    x_test = torch.randn(batch_size, 15, METADATA_DIM)
    output = model.forward_coaching(x_test)
    print(f"Coaching output: {output.shape}\n")

    # Test Selective Decoding
    print("Testing Selective Decoding...")
    pred1, emb1, decoded1 = model.forward_selective(x_test)
    print(f"Step 1: Decoded={decoded1}")

    # Small change
    x_test_small = x_test + 0.001 * torch.randn_like(x_test)
    pred2, emb2, decoded2 = model.forward_selective(
        x_test_small, prev_embedding=emb1, threshold=0.1
    )
    print(f"Step 2 (Small change): Decoded={decoded2}")

    # Large change
    x_test_large = x_test + 1.0 * torch.randn_like(x_test)
    pred3, emb3, decoded3 = model.forward_selective(
        x_test_large, prev_embedding=emb1, threshold=0.1
    )
    print(f"Step 3 (Large change): Decoded={decoded3}")

    print("[OK] JEPA model test passed")
