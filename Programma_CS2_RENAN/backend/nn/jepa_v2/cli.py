"""CLI entry point for JEPA v2 pre-training (Parte III §5.4).

``run_jepa_v2(args)`` is called by ``run_full_training_cycle.py`` when
``--model-type jepa_v2`` is passed.  ``main()`` enables standalone
``python -m Programma_CS2_RENAN.backend.nn.jepa_v2.cli`` invocation.
"""

from __future__ import annotations

import argparse
import logging
from typing import Any

log = logging.getLogger(__name__)


def run_jepa_v2(args: Any) -> bool:
    """Run JEPA v2 pre-training. Returns True on success, False on abort.

    Args:
        args: namespace with at least ``seed`` (optional int), ``no_tensorboard``
              (bool), and ``tb_logdir`` (optional str).
    """
    import dataclasses

    from Programma_CS2_RENAN.backend.nn.config import get_device, set_global_seed
    from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
    from Programma_CS2_RENAN.backend.nn.jepa_v2.sampler import (
        ShardIndex,
        WindowSampler,
        probe_batch,
    )
    from Programma_CS2_RENAN.backend.nn.jepa_v2.telemetry import Telemetry
    from Programma_CS2_RENAN.backend.nn.jepa_v2.trainer import JepaV2Trainer
    from Programma_CS2_RENAN.core.config import get_setting

    cfg = JepaV2Config()
    if getattr(args, "dry_run", False):
        cfg = dataclasses.replace(cfg, steps=60, probe_every=20)
        log.info("dry_run: capped steps=%d probe_every=%d", cfg.steps, cfg.probe_every)
    cfg.validate()

    seed = getattr(args, "seed", None) or cfg.seed
    set_global_seed(seed)

    device = get_device()

    data_dir = get_setting("JEPA_V2_DATA_DIR", "/data/PROIECT/cs2_v2")
    log.info("JEPA v2 data dir: %s", data_dir)

    train_index = ShardIndex(data_dir, "train")
    val_index = ShardIndex(data_dir, "val")

    train_sampler = WindowSampler(train_index, cfg, "train", seed=seed)

    probe_x_num, probe_x_cat, probe_meta, probe_labels = probe_batch(
        val_index,
        cfg,
        seed=seed + 1,
    )
    probe_demos = [m["demo"] for m in probe_meta]

    run_dir = None
    writer = None
    if not getattr(args, "no_tensorboard", False):
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import build_run_dir

        run_dir = getattr(args, "tb_logdir", None) or build_run_dir("jepa_v2")
        try:
            from torch.utils.tensorboard import SummaryWriter

            writer = SummaryWriter(run_dir)
        except ImportError:
            pass

    telemetry = Telemetry(
        cfg=cfg,
        probe_x_num=probe_x_num,
        probe_x_cat=probe_x_cat,
        probe_labels=probe_labels,
        probe_demos=probe_demos,
        writer=writer,
    )

    trainer = JepaV2Trainer(
        cfg=cfg,
        device=device,
        telemetry=telemetry,
        run_dir=run_dir,
    )

    resumed = trainer.load_full_checkpoint()
    if resumed:
        log.info("Resumed from step %d", trainer.step)

    success = trainer.run(train_sampler)

    if writer is not None:
        writer.flush()
        writer.close()

    return success


def main() -> None:
    """Standalone entry point: ``python -m Programma_CS2_RENAN.backend.nn.jepa_v2.cli``."""
    parser = argparse.ArgumentParser(description="JEPA v2 pre-training")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-tensorboard", action="store_true")
    parser.add_argument("--tb-logdir", type=str, default=None)
    args = parser.parse_args()
    success = run_jepa_v2(args)
    raise SystemExit(0 if success else 3)


if __name__ == "__main__":
    main()
