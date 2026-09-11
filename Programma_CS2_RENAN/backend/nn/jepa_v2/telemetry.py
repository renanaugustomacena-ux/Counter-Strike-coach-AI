"""Telemetry for JEPA v2 training (Parte III §5.1, A-14/A-15/A-16).

``Telemetry.evaluate(step)`` computes collapse metrics, SIGReg diagnostics,
probe AUROCs, and applies abort logic.  Best-checkpoint criterion is mean
probe AUROC.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

import numpy as np
import torch

from Programma_CS2_RENAN.backend.nn.collapse_metrics import compute_collapse_metrics
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.probes import group_kfold_probe, rankme

if TYPE_CHECKING:
    from torch.utils.tensorboard import SummaryWriter


log = logging.getLogger(__name__)


class AbortSignal(Exception):
    """Raised when collapse is detected on two consecutive evaluations (A-14)."""


@dataclass
class EvalResult:
    """Snapshot from a single ``Telemetry.evaluate`` call."""

    step: int
    collapse_metrics: Dict[str, float]
    probe_aurocs: Dict[str, float]
    mean_auroc: float
    rankme: float
    is_best: bool


class Telemetry:
    """Collapse monitor and probe evaluator for JEPA v2 (Parte III §5.1).

    Args:
        cfg: JepaV2Config.
        probe_x_num: (N, W, 21) fixed validation windows.
        probe_x_cat: (N, W, 3) fixed validation windows.
        probe_labels: label_name -> float array (NaN = missing).
        probe_demos: demo name per window (for GroupKFold groups).
        writer: optional TensorBoard SummaryWriter.
    """

    def __init__(
        self,
        cfg: JepaV2Config,
        probe_x_num: torch.Tensor,
        probe_x_cat: torch.Tensor,
        probe_labels: Dict[str, np.ndarray],
        probe_demos: List[str],
        writer: Optional[SummaryWriter] = None,
    ) -> None:
        self.cfg = cfg
        self.probe_x_num = probe_x_num
        self.probe_x_cat = probe_x_cat
        self.probe_labels = probe_labels
        self.probe_demos = np.array(probe_demos)
        self.writer = writer

        self.best_auroc: float = -1.0
        self.history: List[EvalResult] = []
        self._consecutive_alarm: int = 0

    @torch.no_grad()
    def evaluate(
        self,
        step: int,
        encoder: torch.nn.Module,
        device: torch.device,
    ) -> EvalResult:
        """Run collapse check + probes.  Raises AbortSignal on collapse (A-14)."""
        encoder.eval()

        x_num = self.probe_x_num.to(device)
        x_cat = self.probe_x_cat.to(device)

        z = encoder(x_num, x_cat)
        z_pooled = z.mean(dim=1)
        z_np = z_pooled.cpu().float().numpy()

        cm = compute_collapse_metrics(z_pooled)
        rm = rankme(z_np)

        probe_aurocs: Dict[str, float] = {}
        for label_name, label_arr in self.probe_labels.items():
            mask = ~np.isnan(label_arr)
            y = label_arr[mask]
            if len(y) < 10 or y.min() == y.max():
                continue
            n_classes = len(np.unique(y))
            if n_classes != 2:
                continue

            z_masked = z_np[mask]
            demos_masked = self.probe_demos[mask]
            unique_demos = np.unique(demos_masked)
            if len(unique_demos) < 5:
                continue

            result = group_kfold_probe(z_masked, y, demos_masked, seed=self.cfg.seed)
            probe_aurocs[label_name] = result.auroc_mean

        if not probe_aurocs:
            log.warning("No probe labels passed filters at step %d — mean_auroc=0.0", step)
        mean_auroc = float(np.mean(list(probe_aurocs.values()))) if probe_aurocs else 0.0
        is_best = mean_auroc > self.best_auroc
        if is_best:
            self.best_auroc = mean_auroc

        er = EvalResult(
            step=step,
            collapse_metrics=cm,
            probe_aurocs=probe_aurocs,
            mean_auroc=mean_auroc,
            rankme=rm,
            is_best=is_best,
        )
        self.history.append(er)

        alarm = (
            cm["effective_rank"] < self.cfg.abort_rankme_below
            or cm["std_min"] < self.cfg.abort_std_min_below
        )

        if alarm:
            self._consecutive_alarm += 1
            log.warning(
                "Collapse alarm %d/2 at step %d: eff_rank=%.2f std_min=%.4e",
                self._consecutive_alarm,
                step,
                cm["effective_rank"],
                cm["std_min"],
            )
        else:
            self._consecutive_alarm = 0

        if self.writer is not None:
            self._log_tb(step, cm, probe_aurocs, mean_auroc, rm)

        log.info(
            "Eval step=%d: mean_auroc=%.4f rankme=%.2f eff_rank=%.2f best=%s",
            step,
            mean_auroc,
            rm,
            cm["effective_rank"],
            is_best,
        )

        encoder.train()

        if self._consecutive_alarm >= 2:
            raise AbortSignal(
                f"Collapse detected at step {step}: effective_rank={cm['effective_rank']:.2f}, "
                f"std_min={cm['std_min']:.4e} — two consecutive alarms."
            )

        return er

    def _log_tb(
        self,
        step: int,
        cm: Dict[str, float],
        aurocs: Dict[str, float],
        mean_auroc: float,
        rm: float,
    ) -> None:
        w = self.writer
        if w is None:
            return
        for k, v in cm.items():
            w.add_scalar(f"collapse/{k}", v, step)
        w.add_scalar("probe/rankme", rm, step)
        w.add_scalar("probe/mean_auroc", mean_auroc, step)
        for k, v in aurocs.items():
            w.add_scalar(f"probe/{k}", v, step)
        w.flush()
