"""
Win Probability Predictor

Predicts round win probability from current game state.
Uses neural network trained on pro demo data.

Features:
- Real-time probability updates
- Economy-aware predictions
- Player advantage modeling
- Time remaining factor

Adheres to GEMINI.md principles:
- Clean architecture
- Explicit state management
- GPU-friendly operations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.win_probability")

WIN_PROB_PREDICTOR_INPUT_DIM = 12


@dataclass
class GameState:
    """
    Current game state for win probability prediction.

    Attributes:
        team_economy: Team's total economy ($)
        enemy_economy: Enemy team's economy ($)
        alive_players: Number of alive teammates (0-5)
        enemy_alive: Number of alive enemies (0-5)
        utility_remaining: Number of utility items remaining
        map_control_pct: Percentage of map controlled (0-1)
        time_remaining: Seconds remaining in round
        bomb_planted: Whether bomb is planted
        is_ct: Whether team is CT side
    """

    team_economy: int
    enemy_economy: int
    alive_players: int
    enemy_alive: int
    utility_remaining: int = 0
    map_control_pct: float = 0.5
    time_remaining: int = 115
    bomb_planted: bool = False
    is_ct: bool = True


class WinProbabilityNN(nn.Module):
    """
    Neural network for real-time round win probability prediction.

    Architecture:
    - Input: 12 normalized game state features
    - Hidden: 64 → 32 neurons with ReLU + Dropout
    - Output: Sigmoid (probability 0-1)

    NOTE: This is the production predictor model. For the offline training
    model (9 raw features, 32/16 hidden dims), see
    backend/nn/win_probability_trainer.py::WinProbabilityTrainerNN.
    Do NOT cross-load checkpoints between them.

    From Phase 1B Roadmap:
    Target accuracy: 72%+ on test set
    """

    def __init__(self, input_dim: int = WIN_PROB_PREDICTOR_INPUT_DIM, hidden_dim: int = 64):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Xavier initialization for stable training."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Game state features [batch, 12]

        Returns:
            Win probability [batch, 1]
        """
        return self.network(x)


class WinProbabilityPredictor:
    """
    Win probability prediction engine.

    Uses neural network for prediction with rule-based fallbacks.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = WinProbabilityNN()
        self._checkpoint_loaded = False

        if model_path:
            try:
                checkpoint = torch.load(model_path, weights_only=True)
                # A-12: Validate checkpoint dimensions before loading.
                # Trainer model (9-dim) checkpoints are incompatible with
                # predictor (12-dim) — they are separate architectures.
                first_layer_key = "network.0.weight"
                if first_layer_key in checkpoint:
                    ckpt_dim = checkpoint[first_layer_key].shape[1]
                    if ckpt_dim != WIN_PROB_PREDICTOR_INPUT_DIM:
                        raise ValueError(
                            f"A-12: Checkpoint input_dim={ckpt_dim} != "
                            f"predictor input_dim={WIN_PROB_PREDICTOR_INPUT_DIM}. "
                            f"Cannot load trainer checkpoint into predictor."
                        )
                self.model.load_state_dict(checkpoint)
                self._checkpoint_loaded = True
                logger.info("Loaded win probability model from %s", model_path)
            except Exception as e:
                logger.warning("Could not load model: %s. Using heuristic.", e)

        if not self._checkpoint_loaded:
            # W-02: Escalate to error-level so untrained inference is clearly visible
            # in logs. Callers can check _checkpoint_loaded to gate predictions.
            logger.error(
                "W-02: No checkpoint loaded — predictions use random weights. "
                "Heuristic adjustments will dominate. Train or provide a model_path."
            )

        self.model.eval()

    def predict(self, game_state: GameState) -> Tuple[float, str]:
        """
        Predict win probability from game state.

        Args:
            game_state: Current game state

        Returns:
            (probability, explanation)
        """
        # Extract features
        features = self._extract_features(game_state)

        # Predict with neural network
        with torch.no_grad():
            x = torch.FloatTensor(features).unsqueeze(0)
            prob = self.model(x).item()

        # Apply heuristic adjustments
        prob = self._apply_heuristics(prob, game_state)

        # Generate explanation
        explanation = self._generate_explanation(prob, game_state)

        return prob, explanation

    def _extract_features(self, state: GameState) -> np.ndarray:
        """Extract normalized features from game state."""
        return np.array(
            [
                # Economy (normalized to 16000 max)
                state.team_economy / 16000,
                state.enemy_economy / 16000,
                (state.team_economy - state.enemy_economy) / 16000,
                # Player counts (normalized to 5)
                state.alive_players / 5,
                state.enemy_alive / 5,
                (state.alive_players - state.enemy_alive) / 5,
                # W-03: Utility normalized to 5 (CS2 max: 2 smokes + 2 flashes + 1 HE)
                state.utility_remaining / 5,
                # Map control
                state.map_control_pct,
                # Time (normalized to 115s)
                state.time_remaining / 115,
                # Binary features
                1.0 if state.bomb_planted else 0.0,
                1.0 if state.is_ct else 0.0,
                # Derived: Expected equipment value ratio
                min(state.team_economy / max(state.enemy_economy, 1), 2) / 2,
            ],
            dtype=np.float32,
        )

    def _apply_heuristics(self, prob: float, state: GameState) -> float:
        """Apply rule-based adjustments to probability."""
        # Deterministic boundary checks FIRST — before any probabilistic adjustments
        if state.alive_players == 0:
            return 0.0
        if state.enemy_alive == 0:
            return 1.0

        # Player advantage is highly predictive
        player_diff = state.alive_players - state.enemy_alive

        if player_diff >= 3:
            prob = max(prob, 0.85)
        elif player_diff <= -3:
            prob = min(prob, 0.15)

        # W-01: Bomb planted adjustments — additive to stay within [0, 1]
        # at every intermediate step (no transient overflow).
        if state.bomb_planted:
            if not state.is_ct:
                prob = min(prob + 0.10, 1.0)  # T advantage
            else:
                prob = max(prob - 0.10, 0.0)  # CT disadvantage

        # Economy heuristics (Fallback for untrained models)
        econ_diff = state.team_economy - state.enemy_economy
        if econ_diff > 8000:
            prob = max(prob, 0.65)
        elif econ_diff < -8000:
            prob = min(prob, 0.35)

        return max(0, min(1, prob))

    def _generate_explanation(self, prob: float, state: GameState) -> str:
        """Generate human-readable explanation."""
        if prob > 0.70:
            return f"Favorable position ({prob:.0%})"
        elif prob > 0.50:
            return f"Slight advantage ({prob:.0%})"
        elif prob > 0.30:
            return f"Slight disadvantage ({prob:.0%})"
        else:
            return f"Unfavorable position ({prob:.0%})"

    def predict_from_dict(self, state_dict: Dict) -> Tuple[float, str]:
        """Predict from dictionary (convenience method)."""
        game_state = GameState(
            team_economy=state_dict.get("team_economy", 4000),
            enemy_economy=state_dict.get("enemy_economy", 4000),
            alive_players=state_dict.get("alive_players", 5),
            enemy_alive=state_dict.get("enemy_alive", 5),
            utility_remaining=state_dict.get("utility_remaining", 0),
            map_control_pct=state_dict.get("map_control_pct", 0.5),
            time_remaining=state_dict.get("time_remaining", 115),
            bomb_planted=state_dict.get("bomb_planted", False),
            is_ct=state_dict.get("is_ct", True),
        )
        return self.predict(game_state)


def get_win_predictor() -> WinProbabilityPredictor:
    """Factory function for win predictor."""
    return WinProbabilityPredictor()


# ---------------------------------------------------------------------------
# KT-07: Elo Rating System with Recency Weighting
# ---------------------------------------------------------------------------
# Per-player Elo computed from match history with exponential recency decay.
# Elo differential is provided as supplementary context to the win
# probability model without altering the core 12-feature architecture.
#
# References:
#   - Elo, A. E. (1978). The Rating of Chessplayers, Past and Present.
#   - Glickman, M. E. (1999). Parameter estimation in large dynamic
#     paired comparison experiments. Applied Statistics, 48(3), 377–394.
#   - Herbrich, R. et al. (2006). TrueSkill (NeurIPS) — for the
#     recency-weighting adaptation.
# ---------------------------------------------------------------------------

# Default Elo constants
_ELO_INITIAL: float = 1500.0
_ELO_K_FACTOR: float = 32.0
_ELO_RECENCY_HALF_LIFE: int = 20  # matches


@dataclass
class MatchResult:
    """A single match result for Elo computation.

    Attributes:
        opponent_elo: Opponent's Elo rating at the time of the match.
        won: Whether the player won the match.
        match_index: Chronological index (0 = oldest). Used for recency
            weighting; higher index = more recent.
    """

    opponent_elo: float
    won: bool
    match_index: int = 0


class EloRatingCalculator:
    """Per-player Elo rating calculator with exponential recency weighting.

    The standard Elo update is:

        new_elo = old_elo + K * w * (S - E)

    where:
        - S = actual score (1 for win, 0 for loss)
        - E = expected score = 1 / (1 + 10^((opp_elo - elo) / 400))
        - K = base K-factor
        - w = recency weight = 2^((match_index - N + 1) / half_life)

    Recency weighting ensures recent matches contribute more to the
    final rating.  The half-life parameter controls decay speed:
    a match *half_life* games ago contributes half the K-factor of
    the most recent match.

    References:
        Elo, A. E. (1978). The Rating of Chessplayers, Past and Present.
        Glickman, M. E. (1999). Parameter estimation in large dynamic
        paired comparison experiments.

    Args:
        initial_elo: Starting Elo for players with no history.
        k_factor: Base K-factor controlling update magnitude.
        recency_half_life: Number of matches for recency weight to halve.
    """

    def __init__(
        self,
        initial_elo: float = _ELO_INITIAL,
        k_factor: float = _ELO_K_FACTOR,
        recency_half_life: int = _ELO_RECENCY_HALF_LIFE,
    ):
        self.initial_elo = initial_elo
        self.k_factor = k_factor
        self.recency_half_life = max(recency_half_life, 1)

    def compute_elo(self, match_history: List[MatchResult]) -> float:
        """Compute Elo rating from chronologically ordered match history.

        Args:
            match_history: List of ``MatchResult`` objects ordered from
                oldest (index 0) to newest.  If empty, returns
                ``initial_elo``.

        Returns:
            Final Elo rating as a float.
        """
        if not match_history:
            logger.debug("Empty match history — returning initial Elo %.1f", self.initial_elo)
            return self.initial_elo

        n = len(match_history)
        elo = self.initial_elo

        for result in match_history:
            # Expected score (logistic curve)
            expected = 1.0 / (1.0 + 10.0 ** ((result.opponent_elo - elo) / 400.0))
            actual = 1.0 if result.won else 0.0

            # Recency weight: most recent match (index n-1) gets weight 1.0,
            # a match half_life games earlier gets weight 0.5, etc.
            recency_exponent = (result.match_index - (n - 1)) / self.recency_half_life
            recency_weight = float(np.power(2.0, recency_exponent))

            elo += self.k_factor * recency_weight * (actual - expected)

        logger.debug(
            "Elo computed: %d matches, final=%.1f (initial=%.1f)",
            n,
            elo,
            self.initial_elo,
        )
        return float(elo)

    def compute_elo_differential(
        self,
        team_histories: List[List[MatchResult]],
        enemy_histories: List[List[MatchResult]],
    ) -> float:
        """Compute Elo differential between two teams.

        The differential is the difference of team-average Elo ratings:

            diff = mean(team_elos) - mean(enemy_elos)

        Normalized by 400 (one Elo "class") so the output is roughly in
        [-3, +3] for practical purposes and can be fed directly as a
        supplementary feature.

        Args:
            team_histories: List of match histories, one per team player.
            enemy_histories: List of match histories, one per enemy player.

        Returns:
            Normalized Elo differential (float).  Positive favors the team.
        """
        team_elos = (
            [self.compute_elo(h) for h in team_histories] if team_histories else [self.initial_elo]
        )
        enemy_elos = (
            [self.compute_elo(h) for h in enemy_histories]
            if enemy_histories
            else [self.initial_elo]
        )

        team_avg = float(np.mean(team_elos))
        enemy_avg = float(np.mean(enemy_elos))
        differential = (team_avg - enemy_avg) / 400.0

        logger.debug(
            "Elo differential: team_avg=%.1f enemy_avg=%.1f diff=%.3f",
            team_avg,
            enemy_avg,
            differential,
        )
        return differential

    @staticmethod
    def elo_win_probability(elo_a: float, elo_b: float) -> float:
        """Expected win probability of player/team A vs B from Elo ratings.

        Uses the standard logistic Elo formula:

            P(A wins) = 1 / (1 + 10^((elo_b - elo_a) / 400))

        Args:
            elo_a: Elo rating of player/team A.
            elo_b: Elo rating of player/team B.

        Returns:
            Win probability for A in [0, 1].
        """
        return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


class EloAugmentedPredictor:
    """Win probability predictor augmented with Elo differential context.

    Wraps the existing ``WinProbabilityPredictor`` and optionally blends
    its output with an Elo-based prior.  The core 12-feature model is
    **unchanged** — Elo serves as a supplementary Bayesian adjustment:

        final_prob = (1 - alpha) * nn_prob + alpha * elo_prob

    where ``alpha`` controls the Elo influence (default 0.15).

    This preserves backward compatibility: when no Elo data is available,
    the predictor falls back to the standard 12-feature model.

    Args:
        base_predictor: Existing ``WinProbabilityPredictor`` instance.
            If None, creates a new one.
        elo_calculator: ``EloRatingCalculator`` instance.  If None,
            creates one with default parameters.
        elo_blend_alpha: Blending weight for Elo prior (0 = ignore Elo,
            1 = only Elo).  Default 0.15.
    """

    def __init__(
        self,
        base_predictor: Optional[WinProbabilityPredictor] = None,
        elo_calculator: Optional[EloRatingCalculator] = None,
        elo_blend_alpha: float = 0.15,
    ):
        self.base_predictor = base_predictor or WinProbabilityPredictor()
        self.elo_calculator = elo_calculator or EloRatingCalculator()
        self.elo_blend_alpha = np.clip(elo_blend_alpha, 0.0, 1.0)

    def predict_with_elo(
        self,
        game_state: GameState,
        team_elo: float,
        enemy_elo: float,
    ) -> Tuple[float, str]:
        """Predict win probability with Elo-augmented blending.

        Args:
            game_state: Current in-round game state.
            team_elo: Average Elo of the player's team.
            enemy_elo: Average Elo of the enemy team.

        Returns:
            (probability, explanation) tuple.
        """
        # Base prediction from 12-feature model
        base_prob, base_explanation = self.base_predictor.predict(game_state)

        # Elo-based prior
        elo_prob = EloRatingCalculator.elo_win_probability(team_elo, enemy_elo)

        # Bayesian blend
        alpha = float(self.elo_blend_alpha)
        final_prob = (1.0 - alpha) * base_prob + alpha * elo_prob
        final_prob = float(np.clip(final_prob, 0.0, 1.0))

        elo_diff = (team_elo - enemy_elo) / 400.0
        explanation = f"{base_explanation} | Elo diff={elo_diff:+.2f}, " f"blend={final_prob:.0%}"

        logger.debug(
            "EloAugmented: base=%.3f elo_prior=%.3f alpha=%.2f final=%.3f",
            base_prob,
            elo_prob,
            alpha,
            final_prob,
        )

        return final_prob, explanation

    def predict(self, game_state: GameState) -> Tuple[float, str]:
        """Fallback: predict without Elo (delegates to base predictor).

        Maintains interface compatibility with ``WinProbabilityPredictor``.
        """
        return self.base_predictor.predict(game_state)


if __name__ == "__main__":
    # Self-test
    logger.info("=== Win Probability Predictor Test ===\n")

    predictor = WinProbabilityPredictor()

    # Test scenarios
    scenarios = [
        {
            "name": "Even match",
            "state": GameState(
                team_economy=4500, enemy_economy=4500, alive_players=5, enemy_alive=5
            ),
        },
        {
            "name": "Man advantage (4v2)",
            "state": GameState(
                team_economy=4000, enemy_economy=3000, alive_players=4, enemy_alive=2
            ),
        },
        {
            "name": "Economy disadvantage",
            "state": GameState(
                team_economy=2000, enemy_economy=8000, alive_players=5, enemy_alive=5
            ),
        },
        {
            "name": "Bomb planted (T side)",
            "state": GameState(
                team_economy=4000,
                enemy_economy=4000,
                alive_players=3,
                enemy_alive=3,
                bomb_planted=True,
                is_ct=False,
            ),
        },
    ]

    for scenario in scenarios:
        prob, explanation = predictor.predict(scenario["state"])
        logger.info("%s: %.1f%% - %s", scenario["name"], prob * 100, explanation)
