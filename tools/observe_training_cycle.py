"""
Observed Training Cycle — End-to-End Pipeline Diagnostic

Tests the complete flow from Book-Coach-1.md diagram (lines 89-200):
  Acquisizione → Elaborazione → Addestramento → Osservatorio → Conoscenza

Usage:
    python tools/observe_training_cycle.py
"""

import logging
import os
import sys
import time
import traceback

# Venv guard
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ─── Centralized logging ──────────────────────────────────────────────
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger

logger = get_tool_logger("observe_training")

# Reduce noise from libraries
for noisy in ("urllib3", "matplotlib", "PIL", "sentence_transformers", "transformers", "filelock"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def section(title: str):
    """Print a visible section header."""
    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"{'='*72}\n")


def check(label: str, condition: bool, detail: str = ""):
    """Print a pass/fail check."""
    status = "PASS" if condition else "FAIL"
    icon = "✓" if condition else "✗"
    msg = f"  [{status}] {icon} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1: DATA DISCOVERY
# ════════════════════════════════════════════════════════════════════════════
def phase_1_data_discovery():
    """Verify ingested data is available in the database."""
    section("PHASE 1: DATA DISCOVERY (Acquisizione)")

    from sqlmodel import func, select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, PlayerTickState

    db = get_db_manager()
    results = {}

    with db.get_session() as session:
        # 1a. Total tick states
        total_ticks = session.exec(select(func.count(PlayerTickState.id))).one()
        check("PlayerTickState populated", total_ticks > 0, f"{total_ticks:,} ticks total")
        results["total_ticks"] = total_ticks

        # 1b. Ticks per demo
        from sqlalchemy import text

        demo_ticks = session.exec(
            text(
                "SELECT demo_name, COUNT(*) as cnt FROM playertickstate GROUP BY demo_name ORDER BY cnt DESC"
            )
        ).fetchall()
        print("\n  Ticks per demo:")
        for demo_name, cnt in demo_ticks:
            print(f"    {demo_name}: {cnt:,}")

        # 1c. Match stats with splits
        total_stats = session.exec(select(func.count(PlayerMatchStats.id))).one()
        check("PlayerMatchStats populated", total_stats > 0, f"{total_stats} match stats")

        # Check split distribution
        split_query = text(
            "SELECT dataset_split, COUNT(*) FROM playermatchstats WHERE is_pro=1 GROUP BY dataset_split"
        )
        splits = session.exec(split_query).fetchall()
        print("\n  Split distribution (is_pro=True):")
        train_count = 0
        for split_name, cnt in splits:
            print(f"    {split_name}: {cnt}")
            if split_name and split_name.upper() == "TRAIN":
                train_count = cnt
        results["train_count"] = train_count

        # 1d. Critical: check if TRAIN split has matching ticks
        train_demos = session.exec(
            select(PlayerMatchStats.demo_name).where(
                PlayerMatchStats.is_pro == True,
                PlayerMatchStats.dataset_split == "TRAIN",
            )
        ).all()
        train_demo_names = list(set(train_demos))
        print(f"\n  TRAIN demo names: {train_demo_names}")

        # Count ticks for TRAIN demos only
        if train_demo_names:
            placeholders = ",".join([":p" + str(i) for i in range(len(train_demo_names))])
            params = {f"p{i}": d for i, d in enumerate(train_demo_names)}
            train_tick_query = text(
                f"SELECT COUNT(*) FROM playertickstate WHERE demo_name IN ({placeholders})"
            )
            train_ticks = session.exec(train_tick_query, params=params).one()[0]
            check(
                "TRAIN split has tick data",
                train_ticks > 0,
                f"{train_ticks:,} ticks available for training",
            )
            results["train_ticks"] = train_ticks
        else:
            check("TRAIN split has tick data", False, "No TRAIN demos found!")
            results["train_ticks"] = 0

        # 1e. Check UNASSIGNED demos (pipeline gap)
        unassigned = session.exec(
            select(PlayerMatchStats.demo_name).where(PlayerMatchStats.dataset_split == "UNASSIGNED")
        ).all()
        if unassigned:
            print(f"\n  ⚠ UNASSIGNED demos (pipeline gap): {list(set(unassigned))}")

    results["demo_ticks"] = demo_ticks
    return results


# ════════════════════════════════════════════════════════════════════════════
# PHASE 2: FEATURE EXTRACTION (Elaborazione)
# ════════════════════════════════════════════════════════════════════════════
def phase_2_feature_extraction(demo_name: str):
    """Test FeatureExtractor on real tick data."""
    section("PHASE 2: FEATURE EXTRACTION (Elaborazione)")

    import numpy as np
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
        METADATA_DIM,
        FeatureExtractor,
    )
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerTickState

    db = get_db_manager()
    results = {}

    with db.get_session() as session:
        # Load a sample of ticks from the target demo
        ticks = session.exec(
            select(PlayerTickState).where(PlayerTickState.demo_name == demo_name).limit(100)
        ).all()

        check(
            "Ticks loaded for feature extraction",
            len(ticks) > 0,
            f"{len(ticks)} ticks from '{demo_name}'",
        )
        if not ticks:
            return results

        # Extract features
        t0 = time.time()
        try:
            features = FeatureExtractor.extract_batch(ticks)
            elapsed = time.time() - t0
            check(
                "FeatureExtractor.extract_batch() succeeded",
                True,
                f"Shape: {features.shape}, Time: {elapsed:.3f}s",
            )
            results["features_shape"] = features.shape
            results["features"] = features

            # Verify dimensions
            check(
                f"Feature dimension matches METADATA_DIM ({METADATA_DIM})",
                features.shape[1] == METADATA_DIM,
                f"Got {features.shape[1]}",
            )

            # Check for NaN/Inf
            has_nan = np.isnan(features).any()
            has_inf = np.isinf(features).any()
            check("No NaN in features", not has_nan)
            check("No Inf in features", not has_inf)

            # Feature statistics
            print(f"\n  Feature statistics (sample of {len(ticks)} ticks):")
            print(f"    Min:  {features.min():.4f}")
            print(f"    Max:  {features.max():.4f}")
            print(f"    Mean: {features.mean():.4f}")
            print(f"    Std:  {features.std():.4f}")

            # Check for all-zero columns (dead features)
            zero_cols = np.where(features.sum(axis=0) == 0)[0]
            if len(zero_cols) > 0:
                print(f"    ⚠ All-zero columns: {zero_cols}")
            else:
                print(f"    All {METADATA_DIM} features are active")

        except Exception as e:
            check("FeatureExtractor.extract_batch() succeeded", False, str(e))
            logger.exception("FeatureExtractor.extract_batch() failed")
            results["error"] = str(e)

    return results


# ════════════════════════════════════════════════════════════════════════════
# PHASE 3: MODEL INSTANTIATION (Addestramento — Setup)
# ════════════════════════════════════════════════════════════════════════════
def phase_3_model_instantiation():
    """Verify all model types can be instantiated correctly."""
    section("PHASE 3: MODEL INSTANTIATION (Addestramento — Setup)")

    from Programma_CS2_RENAN.backend.nn.config import get_device
    from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

    device = get_device()
    print(f"  Device: {device}")

    models = {}
    for model_type in ["jepa", "vl-jepa", "rap", "default"]:
        try:
            model = ModelFactory.get_model(model_type)
            param_count = sum(p.numel() for p in model.parameters())
            check(
                f"ModelFactory.get_model('{model_type}')",
                True,
                f"{param_count:,} parameters",
            )
            models[model_type] = model
        except Exception as e:
            check(f"ModelFactory.get_model('{model_type}')", False, str(e))
            logger.exception("ModelFactory.get_model('%s') failed", model_type)

    return models


# ════════════════════════════════════════════════════════════════════════════
# PHASE 4: JEPA TRAINING CYCLE (1 Epoch)
# ════════════════════════════════════════════════════════════════════════════
def phase_4_jepa_training():
    """Execute a single JEPA training epoch via TrainingOrchestrator."""
    section("PHASE 4: JEPA TRAINING (1 Epoch — Self-Supervised)")

    import torch

    from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
    from Programma_CS2_RENAN.backend.nn.config import get_device
    from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry
    from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

    device = get_device()
    results = {"success": False}

    # Step 1: Check prerequisites
    manager = CoachTrainingManager()
    prereq_ok, prereq_msg = manager.check_prerequisites()
    check("Prerequisites check", prereq_ok, prereq_msg)

    if not prereq_ok:
        print("\n  ⚠ Prerequisites failed — attempting training anyway with available data...")

    # Step 2: Setup Callbacks for observation
    callbacks = CallbackRegistry()

    class ObserverCallback:
        """Lightweight observer to capture training events."""

        def __init__(self):
            self.events = []
            self.losses = []

        def on_train_start(self, **kwargs):
            config = kwargs.get("config", {})
            print(f"  [CALLBACK] on_train_start: config={config}")
            self.events.append(("train_start", config))

        def on_epoch_start(self, **kwargs):
            epoch = kwargs.get("epoch", 0)
            print(f"  [CALLBACK] on_epoch_start: epoch={epoch}")
            self.events.append(("epoch_start", epoch))

        def on_batch_end(self, **kwargs):
            batch_idx = kwargs.get("batch_idx", 0)
            loss = kwargs.get("loss", 0.0)
            outputs = kwargs.get("outputs", {})
            self.losses.append(loss)
            if batch_idx < 5 or batch_idx % 50 == 0:
                print(f"  [CALLBACK] on_batch_end: batch={batch_idx}, loss={loss:.6f}")
            self.events.append(("batch_end", {"batch_idx": batch_idx, "loss": loss}))

        def on_epoch_end(self, **kwargs):
            epoch = kwargs.get("epoch", 0)
            train_loss = kwargs.get("train_loss", 0.0)
            val_loss = kwargs.get("val_loss", 0.0)
            print(
                f"  [CALLBACK] on_epoch_end: epoch={epoch}, train_loss={train_loss:.6f}, val_loss={val_loss:.6f}"
            )
            self.events.append(
                (
                    "epoch_end",
                    {
                        "epoch": epoch,
                        "train_loss": train_loss,
                        "val_loss": val_loss,
                    },
                )
            )

        def on_train_end(self, **kwargs):
            metrics = kwargs.get("final_metrics", {})
            print(f"  [CALLBACK] on_train_end: metrics={metrics}")
            self.events.append(("train_end", metrics))

    observer = ObserverCallback()
    callbacks.add(observer)

    # Step 3: Create Orchestrator
    orchestrator = TrainingOrchestrator(
        manager=manager,
        model_type="jepa",
        max_epochs=1,  # Single cycle
        patience=10,
        batch_size=32,
        callbacks=callbacks,
    )

    # Step 4: Run training
    print(f"\n  Starting JEPA training on {device}...")
    t0 = time.time()

    try:
        orchestrator.run_training()
        elapsed = time.time() - t0
        check("JEPA training completed", True, f"Elapsed: {elapsed:.2f}s")
        results["success"] = True
        results["elapsed"] = elapsed
        results["events"] = observer.events
        results["losses"] = observer.losses

        if observer.losses:
            print(f"\n  Training Summary:")
            print(f"    Batches processed: {len(observer.losses)}")
            print(f"    First batch loss:  {observer.losses[0]:.6f}")
            print(f"    Last batch loss:   {observer.losses[-1]:.6f}")
            print(f"    Mean loss:         {sum(observer.losses)/len(observer.losses):.6f}")
            print(f"    Min loss:          {min(observer.losses):.6f}")
            print(f"    Max loss:          {max(observer.losses):.6f}")
        else:
            print("\n  ⚠ No batch losses recorded — training may have been skipped")

    except Exception as e:
        elapsed = time.time() - t0
        check("JEPA training completed", False, f"Error after {elapsed:.2f}s: {e}")
        logger.exception("JEPA training failed after %.2fs", elapsed)
        results["error"] = str(e)

    return results


# ════════════════════════════════════════════════════════════════════════════
# PHASE 5: CHECKPOINT & OBSERVATORY (Osservatorio)
# ════════════════════════════════════════════════════════════════════════════
def phase_5_checkpoint_observatory():
    """Verify model was checkpointed and observatory logged."""
    section("PHASE 5: CHECKPOINT & OBSERVATORY (Osservatorio)")

    import glob
    from pathlib import Path

    results = {}

    # Check for saved models
    model_dirs = [
        Path(PROJECT_ROOT) / "Programma_CS2_RENAN" / "backend" / "nn" / "checkpoints",
        Path(PROJECT_ROOT) / "Programma_CS2_RENAN" / "backend" / "storage" / "models",
        Path(PROJECT_ROOT) / "models",
        Path(PROJECT_ROOT) / "Programma_CS2_RENAN" / "data" / "models",
    ]

    # Also search for .pt/.pth files
    pt_files = glob.glob(str(Path(PROJECT_ROOT) / "**" / "*.pt"), recursive=True)
    pth_files = glob.glob(str(Path(PROJECT_ROOT) / "**" / "*.pth"), recursive=True)
    all_model_files = [f for f in pt_files + pth_files if ".venv" not in f]

    if all_model_files:
        print("  Saved model files found:")
        for f in sorted(all_model_files, key=os.path.getmtime, reverse=True)[:10]:
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(f)))
            size = os.path.getsize(f) / 1024
            print(f"    {os.path.relpath(f, PROJECT_ROOT)} ({size:.1f} KB, {mtime})")
        check("Model checkpoint exists", True, f"{len(all_model_files)} model file(s)")
    else:
        check("Model checkpoint exists", False, "No .pt/.pth files found")

    # Check TensorBoard logs
    tb_dirs = glob.glob(str(Path(PROJECT_ROOT) / "**" / "runs" / "**"), recursive=True)
    tb_logs = [d for d in tb_dirs if os.path.isdir(d)]
    if tb_logs:
        print(f"\n  TensorBoard log dirs: {len(tb_logs)}")
        for d in tb_logs[:5]:
            print(f"    {os.path.relpath(d, PROJECT_ROOT)}")
        check("TensorBoard logs exist", True)
    else:
        print("\n  No TensorBoard logs found (may write on multi-epoch training)")
        check("TensorBoard logs exist", False, "Not generated in single-epoch cycle")

    return results


# ════════════════════════════════════════════════════════════════════════════
# PHASE 6: KNOWLEDGE CREATION (Conoscenza)
# ════════════════════════════════════════════════════════════════════════════
def phase_6_knowledge():
    """Check if the knowledge layer has any data."""
    section("PHASE 6: KNOWLEDGE STATE (Conoscenza)")

    from sqlmodel import func, select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager

    db = get_db_manager()

    with db.get_session() as session:
        from sqlalchemy import text

        # Experience Bank (COPER)
        try:
            exp_count = session.exec(text("SELECT COUNT(*) FROM coachingexperience")).one()
            check("Experience Bank (COPER)", exp_count > 0, f"{exp_count} experiences")
        except Exception:
            check("Experience Bank (COPER)", False, "Table not found")

        # Tactical Knowledge (RAG)
        try:
            rag_count = session.exec(text("SELECT COUNT(*) FROM tacticalknowledge")).one()
            check("RAG Knowledge Base", rag_count > 0, f"{rag_count} entries")
        except Exception:
            check("RAG Knowledge Base", False, "Table not found")

        # Coach State
        try:
            state = session.exec(
                text("SELECT status, detail, last_trained_sample_count FROM coachstate")
            ).one()
            print(f"\n  Coach State:")
            print(f"    Status: {state[0]}")
            print(f"    Detail: {state[1]}")
            print(f"    Trained samples: {state[2]}")
        except Exception:
            print("  Coach state not available")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║     CS2 Analyzer — Observed Training Cycle (Single Demo Test)      ║")
    print("║     Testing pipeline from Book-Coach-1.md diagram (L89-200)        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    start_time = time.time()

    # Phase 1: Data Discovery
    data_results = phase_1_data_discovery()

    # Phase 2: Feature Extraction (use a TRAIN demo)
    # Find the best available demo with TRAIN split
    target_demo = None
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    db = get_db_manager()
    with db.get_session() as session:
        train_demos = session.exec(
            select(PlayerMatchStats.demo_name).where(
                PlayerMatchStats.is_pro == True,
                PlayerMatchStats.dataset_split == "TRAIN",
            )
        ).all()
        # Find a TRAIN demo that also has tick data
        tick_demos = [d[0] for d in data_results.get("demo_ticks", [])]
        for td in train_demos:
            if td in tick_demos:
                target_demo = td
                break

    if target_demo:
        print(f"\n  Target demo for observation: {target_demo}")
    else:
        # Fallback: use whichever demo has the most ticks
        if data_results.get("demo_ticks"):
            target_demo = data_results["demo_ticks"][0][0]
            print(f"\n  ⚠ No TRAIN demo with ticks — falling back to: {target_demo}")
        else:
            print("\n  ✗ FATAL: No tick data available at all!")
            return

    feat_results = phase_2_feature_extraction(target_demo)

    # Phase 3: Model Instantiation
    models = phase_3_model_instantiation()

    # Phase 4: JEPA Training (1 epoch)
    train_results = phase_4_jepa_training()

    # Phase 5: Checkpoint & Observatory
    phase_5_checkpoint_observatory()

    # Phase 6: Knowledge State
    phase_6_knowledge()

    # ═══ FINAL REPORT ═══
    section("FINAL REPORT")
    total_time = time.time() - start_time
    print(f"  Total observation time: {total_time:.2f}s")
    print()

    if train_results.get("success"):
        print("  ✓ Pipeline executed a complete training cycle!")
        if train_results.get("losses"):
            print(f"    Batches: {len(train_results['losses'])}")
            print(
                f"    Loss range: [{min(train_results['losses']):.6f}, {max(train_results['losses']):.6f}]"
            )
    else:
        print("  ✗ Training cycle did NOT complete successfully")
        if "error" in train_results:
            print(f"    Error: {train_results['error']}")

    # Identify pipeline gaps
    print("\n  Pipeline Gap Analysis:")
    gaps = []
    if data_results.get("train_ticks", 0) == 0:
        gaps.append("No tick data available in TRAIN split — _fetch_jepa_ticks() returns empty")
    if not feat_results.get("features_shape"):
        gaps.append("Feature extraction failed — vectorizer cannot process tick data")
    if not train_results.get("success"):
        gaps.append("Training cycle failed — check logs above")

    if gaps:
        for g in gaps:
            print(f"    ✗ {g}")
    else:
        print("    ✓ No critical gaps detected!")


if __name__ == "__main__":
    main()
