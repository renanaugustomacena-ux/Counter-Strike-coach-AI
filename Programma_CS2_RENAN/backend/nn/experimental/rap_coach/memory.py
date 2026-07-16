import torch
import torch.nn as nn

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.experimental.rap_coach.memory")

# RAP memory layer requires ncps (LTC neurons) and hflayers (Hopfield associative memory).
# These are niche academic libraries — make them optional so the rest of the codebase
# can import without crashing when they're not installed (USE_RAP_MODEL=False default).
try:
    from hflayers import HopfieldLayer
    from ncps.torch import LTC
    from ncps.wirings import AutoNCP

    _RAP_DEPS_AVAILABLE = True
except ImportError:
    LTC = None
    AutoNCP = None
    HopfieldLayer = None
    _RAP_DEPS_AVAILABLE = False


class RAPMemory(nn.Module):
    """
    Recurrent Belief State Module (Generation 2: Liquid Mind).
    Upgraded from LSTM to Liquid Time-Constant (LTC) + Hopfield Associative Memory.

    Resolves POMDP partial observability via Bayesian filtering in latent space,
    with continuous-time handling (LTC) and long-term pattern recall (Hopfield).
    """

    def __init__(self, perception_dim, metadata_dim, hidden_dim=256):
        if not _RAP_DEPS_AVAILABLE:
            raise ImportError(
                "RAP memory layer requires 'ncps' and 'hflayers' packages. "
                "Install with: pip install ncps hflayers"
            )
        super().__init__()

        input_dim = perception_dim + metadata_dim

        # 1. Liquid Time-Constant (LTC) Layer
        # Models continuous-time dynamics (variable frame rates, "pace" of the game)
        # We use AutoNCP wiring to create a sparse, brain-like connectivity.
        # RAP-AUDIT-07: AutoNCP output ratio 0.3 (per Lechner et al. 2020 recommendation).
        # Previous 0.5 ratio (output_size=256 of 512 units) allocated 50% to motor neurons,
        # leaving too few inter/command neurons for processing. With 0.3 ratio:
        #   Motor: 154 (30%), Command: 143 (28%), Inter: 215 (42%)
        # vs old: Motor: 256 (50%), Command: 102 (20%), Inter: 154 (30%)
        # NOTE: changing this invalidates existing checkpoints — version-gated loading required.
        ncp_units = hidden_dim * 2  # 512 total neurons
        ncp_output = int(ncp_units * 0.3)  # 154 motor neurons (recommended ratio)
        # NN-45 + NN-MEM-02: Seed both numpy and torch RNGs for deterministic,
        # checkpoint-portable NCP wiring. AutoNCP uses numpy internally, but
        # downstream LTC init may use torch — save/restore both to isolate side effects.
        import numpy as np

        np_rng_state = np.random.get_state()
        torch_rng_state = torch.random.get_rng_state()
        np.random.seed(42)
        torch.manual_seed(42)
        try:
            self.wiring = AutoNCP(units=ncp_units, output_size=ncp_output)
        finally:
            np.random.set_state(np_rng_state)
            torch.random.set_rng_state(torch_rng_state)
        self.ltc = LTC(input_dim, self.wiring, batch_first=True)

        # RAP-LTC-FIX (2026-05-06): work around an ncps shape bug in
        # `LTCCell._ode_solver`. When `LTC.forward` is called with a
        # `timespans` tensor of shape (B, T), the per-step slice
        # `timespans[:, t].squeeze()` (ltc.py:178) collapses to shape (B,).
        # Then `_ode_solver` does `cm / (elapsed_time / ode_unfolds)` where
        # `cm` is shape (state_size,) = (512,) for our config. Division of
        # (state_size,) by (B,) does not broadcast unless state_size==B,
        # so any batch with ncp_units != batch_size raises a RuntimeError
        # ("tensor a (512) must match tensor b (10) at non-singleton dim 0").
        # Reproduces on ncps==1.0.1 and ncps==0.0.7 — not a version skew.
        #
        # Fix: wrap the cell's `_ode_solver` to unsqueeze 1-D elapsed_time
        # to shape (B, 1), so cm broadcasts to (B, state_size) — which is
        # what the ODE math needs (per-batch per-feature time constant).
        # See docs/rap_training_known_issue_2026-05-05.md for the trace
        # and reasoning.
        _original_ode_solver = self.ltc.rnn_cell._ode_solver

        def _patched_ode_solver(inputs, state, elapsed_time):
            if torch.is_tensor(elapsed_time) and elapsed_time.dim() == 1:
                elapsed_time = elapsed_time.unsqueeze(-1)  # (B,) -> (B, 1)
            return _original_ode_solver(inputs, state, elapsed_time)

        self.ltc.rnn_cell._ode_solver = _patched_ode_solver

        # RAP-AUDIT-07: Project LTC output (154-dim) back to hidden_dim (256) to
        # maintain the downstream contract. All layers after memory expect 256-dim.
        self.ltc_projection = nn.Linear(ncp_output, hidden_dim)

        # 2. Hopfield Layer (Associative Memory)
        # RAP-AUDIT-03: Uses HopfieldLayer (NOT Hopfield) for learnable prototype storage.
        # Hopfield(single_tensor) performs SELF-ATTENTION (input=query=key=value).
        # HopfieldLayer has persistent nn.Parameter `lookup_weights` — these are the
        # "Prototype Rounds" that survive between batches and are shaped by backprop.
        # 32 prototypes × 256-dim = 8,192 parameters (negligible vs model total).
        # Per Ramsauer et al. (ICLR 2021), storage capacity is O(exp(d)) for d-dim patterns.
        # NN-MEM-01: Track whether Hopfield has been trained (via checkpoint load or
        # gradient updates). Until trained, forward() bypasses associative recall.
        # RAP-M-04: Require ≥2 training forward passes before activating Hopfield,
        # so at least one backward+step has shaped the stored patterns.
        self._hopfield_trained = False
        self._training_forward_count = 0
        # SA-11: HopfieldLayer is None when hflayers not installed, but the
        # _RAP_DEPS_AVAILABLE guard at __init__ entry (line 33) raises ImportError
        # before this line is reachable. PyCharm can't see this control flow.
        self.hopfield = HopfieldLayer(  # type: ignore[misc]
            input_size=hidden_dim,
            output_size=hidden_dim,
            num_heads=4,
            quantity=32,  # 32 learnable prototype patterns
            trainable=True,  # Prototypes updated via backprop
        )

        # 3. State Reconstruction Head (The Belief State)
        # Predicts latent properties like "Enemy Strategy" or "Rotation Phase"
        self.belief_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),  # Better gradient flow than ReLU
            nn.Linear(hidden_dim, 64),  # Belief vector size
        )
        logger.debug(
            "RAPMemory initialized: input=%d, hidden=%d, ncp_units=%d, ncp_output=%d, "
            "hopfield_heads=4, hopfield_prototypes=32",
            input_dim,
            hidden_dim,
            ncp_units,
            ncp_output,
        )

    def forward(self, x, hidden=None, timespans=None):
        """
        Processes sequential observation features.

        Args:
            x: Input tensor (batch, seq_len, input_dim)
            hidden: Optional initial hidden state from previous forward call
            timespans: Optional (batch, seq_len) tensor of inter-tick time intervals
                in seconds. RAP-AUDIT-05: Without timespans, the LTC treats every
                tick interval as 1.0s, losing the continuous-time advantage over LSTM.
                With real timespans, the ODE solver adapts membrane capacitance:
                cm_t = cm / (elapsed_time / ode_unfolds), enabling proper temporal
                dynamics across different tick rates (64 vs 128) and pauses.
        """
        # Liquid Flow: Handle temporal dynamics with optional real-time intervals
        ltc_out, hidden = self.ltc(x, hidden, timespans=timespans)
        # RAP-AUDIT-07: Project from NCP output (154) to hidden_dim (256)
        ltc_out = self.ltc_projection(ltc_out)

        # Associative Recall: Retrieve tactical prototypes
        # NN-MEM-01: Skip Hopfield if not yet trained — random prototypes produce
        # near-uniform attention that adds noise rather than signal.
        if self._hopfield_trained:
            mem_out = self.hopfield(ltc_out)
        else:
            mem_out = torch.zeros_like(ltc_out)

        # Residual Combination: Dynamics + Memory
        combined_state = ltc_out + mem_out

        # We use the full sequence for training, but the last tick for decision
        belief = self.belief_head(combined_state)

        # NN-MEM-01 + RAP-M-04 (R4 MED, 2026-07-16): the gate used to count
        # FORWARD passes (>=2), but with gradient accumulation the optimizer
        # steps only every accumulation_steps batches — Hopfield activated
        # before any weight update had shaped the stored patterns (which are
        # random-init; initialize_prototypes has no callers). Activation is
        # now driven by notify_optimizer_step(), called by the trainer right
        # after a real optimizer step. Forward counting remains only as
        # telemetry.
        if self.training and not self._hopfield_trained:
            self._training_forward_count += 1

        return combined_state, belief, hidden

    def notify_optimizer_step(self) -> None:
        """NN-MEM-01: activate the Hopfield memory after the first REAL
        optimizer step (called by the trainer post-``scaler.step``)."""
        if not self._hopfield_trained:
            self._hopfield_trained = True
            logger.debug(
                "NN-MEM-01: Hopfield activated after first optimizer step "
                "(%d training forwards seen)",
                self._training_forward_count,
            )

    @torch.no_grad()
    def initialize_prototypes(self, embeddings: torch.Tensor) -> None:
        """Phase 5B: Initialize Hopfield prototypes from K-means centroids.

        Reduces warmup time from random initialization. Call after first
        epoch of LTC output has been collected.
        """
        K = 32
        N = embeddings.shape[0]
        if N < K:
            logger.debug("Too few embeddings (%d) for %d prototypes", N, K)
            return
        indices = torch.linspace(0, N - 1, K).long().to(embeddings.device)
        centroids = embeddings[indices].clone()
        for _ in range(10):
            dists = torch.cdist(embeddings, centroids)
            assignments = dists.argmin(dim=1)
            for k in range(K):
                mask = assignments == k
                if mask.any():
                    centroids[k] = embeddings[mask].mean(dim=0)
        for name, param in self.hopfield.named_parameters():
            if param.shape[-1] == centroids.shape[-1] and param.shape[0] == K:
                param.data.copy_(centroids)
                self._hopfield_trained = True
                logger.info("Phase 5B: Hopfield prototypes initialized from %d samples", N)
                return
        logger.debug("Phase 5B: No matching Hopfield prototype parameter found")

    def load_state_dict(self, state_dict, strict=True, assign=False):
        """Override to mark Hopfield as trained when loading a checkpoint."""
        result = super().load_state_dict(state_dict, strict=strict, assign=assign)
        self._hopfield_trained = True
        logger.debug("NN-MEM-01: Hopfield marked as trained via checkpoint load")
        return result


class RAPMemoryLite(nn.Module):
    """
    Lightweight memory layer using standard PyTorch LSTM.
    Drop-in replacement for RAPMemory when ncps/hflayers are unavailable.

    Same contract:
      Input:  x [B, T, perception_dim + metadata_dim]  (153)
      Output: (combined_state [B, T, 256], belief [B, T, 64], hidden)
    """

    def __init__(self, perception_dim, metadata_dim, hidden_dim=256):
        super().__init__()
        input_dim = perception_dim + metadata_dim  # 128 + 25 = 153

        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)

        self.belief_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, 64),
        )

        logger.debug(
            "RAPMemoryLite initialized: input=%d, hidden=%d (LSTM-based)",
            input_dim,
            hidden_dim,
        )

    def forward(self, x, hidden=None, timespans=None):
        """
        Processes sequential observation features.
        x shape: (batch, seq_len, input_dim)
        timespans: ignored (LSTM has no continuous-time dynamics), accepted for interface parity.
        """
        lstm_out, hidden = self.lstm(x, hidden)
        belief = self.belief_head(lstm_out)
        return lstm_out, belief, hidden
