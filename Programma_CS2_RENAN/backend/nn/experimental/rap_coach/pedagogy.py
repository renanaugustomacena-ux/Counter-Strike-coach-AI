import torch
import torch.nn as nn

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.experimental.rap_coach.pedagogy")


class RAPPedagogy(nn.Module):
    """
    Causal Feedback Layer (RL Layer 3 foundations).
    Pinpoints "Why it mattered" via Advantage-based attribution.
    """

    def __init__(self, hidden_dim):
        super().__init__()

        # Critic Head: Value estimation V(s)
        self.critic = nn.Sequential(nn.Linear(hidden_dim, 64), nn.ReLU(), nn.Linear(64, 1))

        # Skill-conditioned bias detector
        self.skill_adapter = nn.Linear(10, hidden_dim)  # 10 skill buckets

    def calculate_advantage_gap(self, value_pred, actual_outcome):
        """
        Delta A_t = Actual Return - Estimated Value
        Represents the coaching gap.
        """
        return actual_outcome - value_pred

    def forward(self, hidden_state, skill_vec=None):
        if skill_vec is not None:
            # Shift hidden state based on skill level bias (Layer 5 Formal Foundation)
            hidden_state = hidden_state + self.skill_adapter(skill_vec)

        value_v = self.critic(hidden_state)
        return value_v


class CausalAttributor(nn.Module):
    """
    Pedagogical Head: Translates latent gaps into human concepts.
    Maps (User State, Pro State) -> {Concept: Semantic Weight}
    """

    def __init__(self, hidden_dim):
        super().__init__()
        self.concepts = ["Positioning", "Crosshair Placement", "Aggression", "Utility", "Rotation"]
        # Context-aware concept relevance (Is this a positioning moment?)
        self.relevance_head = nn.Sequential(
            nn.Linear(hidden_dim, 32), nn.ReLU(), nn.Linear(32, len(self.concepts)), nn.Sigmoid()
        )

    def diagnose(self, hidden_state, optimal_pos_delta, optimal_view_delta=None):
        """
        Returns a dictionary of concept attributions.
        Args:
            hidden_state: Context vector [B, H]
            optimal_pos_delta: Recommended position shift [B, 3]
            optimal_view_delta: Recommended view angle shift [B, 2] (Optional)
        """
        # 1. Context Relevance (Neural)
        context_weights = self.relevance_head(hidden_state)  # [B, 5]

        # 2. Mechanical Deltas (Heuristic)
        # The model's output IS the gap.
        pos_delta = torch.norm(optimal_pos_delta, dim=-1, keepdim=True)  # [B, 1]

        if optimal_view_delta is not None:
            aim_delta = torch.norm(optimal_view_delta, dim=-1, keepdim=True)
        else:
            aim_delta = torch.zeros_like(pos_delta)

        # 3. Fuse Neural + Mechanical
        B = hidden_state.shape[0]
        mechanical_errors = torch.zeros(B, len(self.concepts), device=hidden_state.device)

        mechanical_errors[:, 0] = pos_delta.squeeze()  # Positioning
        mechanical_errors[:, 1] = aim_delta.squeeze()  # Aim
        mechanical_errors[:, 2] = pos_delta.squeeze() * 0.5  # Aggression (Proxy)
        mechanical_errors[:, 3] = self._detect_utility_need(hidden_state)  # Utility (Neural)
        mechanical_errors[:, 4] = pos_delta.squeeze() * 0.8  # Rotation (Proxy)

        attribution_scores = context_weights * mechanical_errors
        return attribution_scores

    def _detect_utility_need(self, hidden):
        """
        Heuristic for utility importance based on latent state.
        In modern CS2, utility need is high when equipment value is high but
        the player is in a 'wait' or 'hold' state (detected via low motion vectors).
        """
        # Metadata is at the end of the fused vector (dim perception_dim + METADATA_DIM)
        # We can extract a signal from the latent space.
        # For now, use a learned projection if available, or a simple norm.
        # This takes us away from 'placebo zeros'.
        util_signal = torch.sigmoid(hidden.mean(dim=-1))
        return util_signal  # [B] dynamic score instead of static zero
