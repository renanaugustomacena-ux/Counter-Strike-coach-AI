"""JEPA v2 trainer (Parte III §5.3, C-9, A-13).

AdamW with per-step cosine schedule + linear warmup, bf16 autocast
(no GradScaler), grad clipping. Checkpoints encoder via
``persistence.save_nn``.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Dict, Optional

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.config import amp_autocast, set_global_seed
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.losses import jepa_v2_loss
from Programma_CS2_RENAN.backend.nn.jepa_v2.predictor import PredictorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.projector import ProjectorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.sigreg import SIGReg
from Programma_CS2_RENAN.backend.nn.jepa_v2.telemetry import AbortSignal, Telemetry

if TYPE_CHECKING:
    from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import WindowSampler

log = logging.getLogger(__name__)


def cosine_lr(step: int, cfg: JepaV2Config) -> float:
    """Per-step cosine schedule with linear warmup (C-9, A-13).

    ``lr_min + 0.5*(lr_max-lr_min)*(1+cos(π*(step-warmup)/(steps-warmup)))``
    """
    if step < cfg.warmup_steps:
        return cfg.lr_min + (cfg.lr_max - cfg.lr_min) * step / max(cfg.warmup_steps, 1)
    progress = (step - cfg.warmup_steps) / max(cfg.steps - cfg.warmup_steps, 1)
    return cfg.lr_min + 0.5 * (cfg.lr_max - cfg.lr_min) * (1.0 + math.cos(math.pi * progress))


class JepaV2Trainer:
    """JEPA v2 training loop (Parte III §5.3).

    Args:
        cfg: JepaV2Config.
        device: torch device (pass explicitly, do not call get_device).
        telemetry: optional Telemetry instance for collapse monitoring.
        run_dir: optional directory for TensorBoard logs.
    """

    def __init__(
        self,
        cfg: JepaV2Config,
        device: torch.device,
        telemetry: Optional[Telemetry] = None,
        run_dir: Optional[str] = None,
    ) -> None:
        self.cfg = cfg
        self.device = device
        self.telemetry = telemetry
        self.run_dir = run_dir

        cfg.validate()

        self.encoder = EncoderV2(cfg).to(device)
        self.projector = ProjectorV2(cfg).to(device)
        self.predictor = PredictorV2(cfg).to(device)
        self.sigreg = SIGReg(
            knots=cfg.sigreg_knots,
            num_proj=cfg.sigreg_num_proj,
            t_max=cfg.sigreg_t_max,
        ).to(device)

        params = (
            list(self.encoder.parameters())
            + list(self.projector.parameters())
            + list(self.predictor.parameters())
        )
        self.optimizer = torch.optim.AdamW(
            params,
            lr=cfg.lr_max,
            betas=cfg.betas,
            weight_decay=cfg.weight_decay,
        )

        self.step: int = 0
        self._ever_evaluated: bool = False
        self._writer = None
        if run_dir is not None:
            try:
                from torch.utils.tensorboard import SummaryWriter

                self._writer = SummaryWriter(run_dir)
            except ImportError:
                log.warning("tensorboard not available, skipping TB logging")

    def _set_lr(self, lr: float) -> None:
        for pg in self.optimizer.param_groups:
            pg["lr"] = lr

    def train_step(self, x_num: torch.Tensor, x_cat: torch.Tensor) -> Dict[str, float]:
        """Execute one training step. Returns loss info dict."""
        self.encoder.train()
        self.projector.train()
        self.predictor.train()

        x_num = x_num.to(self.device)
        x_cat = x_cat.to(self.device)

        lr = cosine_lr(self.step, self.cfg)
        self._set_lr(lr)

        self.optimizer.zero_grad(set_to_none=True)

        with amp_autocast():
            z, taps = self.encoder(x_num, x_cat, return_taps=True)
            loss, info = jepa_v2_loss(
                z,
                taps,
                self.predictor,
                self.projector,
                self.cfg,
                self.sigreg,
                self.step,
            )

        loss.backward()
        grad_norm = nn.utils.clip_grad_norm_(
            list(self.encoder.parameters())
            + list(self.projector.parameters())
            + list(self.predictor.parameters()),
            self.cfg.grad_clip,
        )
        self.optimizer.step()

        info["lr"] = lr
        info["grad_norm"] = float(grad_norm)

        if self._writer is not None:
            for k, v in info.items():
                self._writer.add_scalar(f"train/{k}", v, self.step)

        self.step += 1
        return info

    def save_encoder_checkpoint(
        self,
        version: str = "jepa_v2_encoder",
        schema_meta: Optional[Dict] = None,
    ) -> None:
        """Save encoder-only checkpoint via persistence.save_nn."""
        from Programma_CS2_RENAN.backend.nn import persistence

        persistence.save_nn(
            self.encoder,
            version,
            extra_meta={"step": self.step},
            schema_meta=schema_meta,
        )
        log.info("Saved encoder checkpoint '%s' at step %d", version, self.step)

    def save_full_checkpoint(
        self,
        version: str = "jepa_v2_full",
        schema_meta: Optional[Dict] = None,
    ) -> None:
        """Save encoder+projector+predictor as ModuleDict via persistence.save_nn.

        Optimizer state is NOT saved — too large for the v1 persistence API.
        """
        bundle = nn.ModuleDict(
            {
                "encoder": self.encoder,
                "projector": self.projector,
                "predictor": self.predictor,
            }
        )
        from Programma_CS2_RENAN.backend.nn import persistence

        persistence.save_nn(
            bundle,
            version,
            extra_meta={"step": self.step},
            schema_meta=schema_meta,
        )
        log.info("Saved full checkpoint '%s' at step %d", version, self.step)

    def load_full_checkpoint(self, version: str = "jepa_v2_full") -> bool:
        """Attempt to load a full checkpoint for resume.

        Returns True if a checkpoint was loaded, False otherwise.
        Optimizer moments are NOT restored (logged as WARNING).
        """
        from Programma_CS2_RENAN.backend.nn import persistence

        bundle = nn.ModuleDict(
            {
                "encoder": self.encoder,
                "projector": self.projector,
                "predictor": self.predictor,
            }
        )
        try:
            persistence.load_nn(version, bundle)
            bundle["encoder"].train()
            bundle["projector"].train()
            bundle["predictor"].train()
        except FileNotFoundError:
            return False

        extra = self._read_sidecar_extra(version)
        if extra and "step" in extra:
            self.step = int(extra["step"])

        log.warning(
            "Resumed from '%s' at step %d. Optimizer moments NOT restored — "
            "LR schedule continues from step %d.",
            version,
            self.step,
            self.step,
        )
        return True

    @staticmethod
    def _read_sidecar_extra(version: str) -> Optional[dict]:
        """Read the 'extra' field from a checkpoint sidecar."""
        import json

        from Programma_CS2_RENAN.backend.nn import persistence

        path = persistence.get_model_path(version)
        sidecar = path.with_suffix(".pt.meta.json")
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text())
                return meta.get("extra", {})
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _build_schema_meta(self) -> Dict:
        """Build schema_meta from CS2_V2 (single source of truth)."""
        from Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2 import CS2_V2

        return {
            "schema_version": "v2",
            "schema_id": CS2_V2.schema_id,
            "schema_fingerprint": CS2_V2.fingerprint(),
            "numeric_dim": CS2_V2.numeric_dim,
            "categorical_vocab_sizes": list(CS2_V2.categorical_vocab_sizes),
        }

    def run(
        self,
        sampler: WindowSampler,
        schema_meta: Optional[Dict] = None,
    ) -> bool:
        """Run the full training loop. Returns True on success, False on abort."""
        set_global_seed(self.cfg.seed)
        if schema_meta is None:
            schema_meta = self._build_schema_meta()

        log.info("Starting JEPA v2 training: %d steps, device=%s", self.cfg.steps, self.device)

        data_iter = iter(sampler)

        try:
            while self.step < self.cfg.steps:
                x_num, x_cat, _meta = next(data_iter)
                info = self.train_step(x_num, x_cat)

                if self.step % 100 == 0 or self.step == 1:
                    log.info(
                        "step=%d loss=%.4f L_next=%.4f lr=%.2e",
                        self.step,
                        info["loss"],
                        info["L_next"],
                        info["lr"],
                    )

                if (
                    self.telemetry is not None
                    and self.cfg.probe_every > 0
                    and self.step % self.cfg.probe_every == 0
                    and self.step > 0
                ):
                    self._ever_evaluated = True
                    result = self.telemetry.evaluate(self.step, self.encoder, self.device)
                    if result.is_best:
                        self.save_encoder_checkpoint(schema_meta=schema_meta)

                    self.save_full_checkpoint(schema_meta=schema_meta)

        except AbortSignal as e:
            log.error("Training aborted: %s", e)
            return False

        if not self._ever_evaluated:
            self.save_encoder_checkpoint(schema_meta=schema_meta)
        self.save_full_checkpoint(schema_meta=schema_meta)

        if self._writer is not None:
            self._writer.flush()
            self._writer.close()

        log.info("JEPA v2 training complete at step %d", self.step)
        return True
