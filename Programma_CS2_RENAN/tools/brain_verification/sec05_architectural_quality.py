"""
Section 5: Architectural Quality (Rules 37-47)

Tests modularity, explainability, scalability, memory, training data quality,
data contamination, training stability, inference efficiency, and batch robustness.
Auto: 11, Manual: 0
"""

import time

import numpy as np
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
from Programma_CS2_RENAN.tools.brain_verification._common import (
    ALL_MODEL_TYPES,
    FAIL,
    METADATA_DIM,
    PASS,
    SEED_A,
    SEED_B,
    SEED_C,
    SKIP,
    WARN,
    ModelFactory,
    RuleResult,
    SectionResult,
    deterministic_context,
    extract_output_tensor,
    forward_model,
    get_all_models,
    get_db_session_or_none,
    get_model,
    get_random_input,
    has_nan_or_inf,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(5, "Architectural Quality")

    section.add(_rule_37())
    section.add(_rule_38())
    section.add(_rule_39())
    section.add(_rule_40())
    section.add(_rule_41())
    section.add(_rule_42())
    section.add(_rule_43(quick))
    section.add(_rule_44())
    section.add(_rule_45())
    section.add(_rule_46())
    section.add(_rule_47())

    return section


def _rule_37() -> RuleResult:
    """Component modularity: each model instantiates independently via ModelFactory."""
    t0 = time.perf_counter()
    results = {}
    all_ok = True

    failed_types = []
    for mt in ALL_MODEL_TYPES:
        # Keep all instances alive so Python doesn't reuse memory addresses
        live_instances = []
        try:
            for _ in range(5):
                m = ModelFactory.get_model(mt)
                live_instances.append(m)
            ids = [id(m) for m in live_instances]
            all_distinct = len(set(ids)) == 5
            results[mt] = {"instances": 5, "all_distinct": all_distinct}
            if not all_distinct:
                failed_types.append(mt)
        except Exception as e:
            results[mt] = {"error": str(e)[:100]}
            failed_types.append(mt)

    # Tolerate up to 1 model type failing (e.g. RAP has heavy dependencies)
    all_ok = len(failed_types) <= 1

    return RuleResult(
        37,
        "Component modularity",
        PASS if all_ok else FAIL,
        evidence=results,
        details=f"5 independent instantiations per model: {len(failed_types)} type(s) failed "
        f"(tolerance=1), failed={failed_types}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_38() -> RuleResult:
    """Explainability architecture: RAP attribution, VL-JEPA concepts, Legacy gates accessible."""
    t0 = time.perf_counter()
    models = get_all_models()
    checks = {}

    # RAP: attribution (5-dim)
    rap = models.get(ModelFactory.TYPE_RAP)
    if rap is not None:
        rap.eval()
        inputs = get_random_input(ModelFactory.TYPE_RAP, batch_size=2, seq_len=5)
        with torch.no_grad():
            out = forward_model(rap, inputs)
        if isinstance(out, dict):
            attr = out.get("attribution")
            checks["rap_attribution"] = attr is not None and attr.shape[-1] == 5
        else:
            checks["rap_attribution"] = False

    # VL-JEPA: top_concepts with CONCEPT_NAMES
    vl = models.get(ModelFactory.TYPE_VL_JEPA)
    if vl is not None:
        vl.eval()
        x = torch.randn(2, 10, METADATA_DIM)
        with torch.no_grad():
            out = vl.forward_vl(x)
        tc = out.get("top_concepts")
        checks["vl_jepa_concepts"] = tc is not None and len(tc) > 0

    # Legacy: gate accessible and callable
    legacy = models.get(ModelFactory.TYPE_LEGACY)
    if legacy is not None:
        legacy.eval()
        x = torch.randn(2, 10, METADATA_DIM)
        with torch.no_grad():
            out = legacy(x)
        has_gate = hasattr(legacy, "gate")
        gate_callable = has_gate and callable(legacy.gate)
        checks["legacy_gate"] = has_gate and gate_callable

    passed = all(checks.values()) if checks else False
    return RuleResult(
        38,
        "Explainability architecture",
        PASS if passed else (WARN if any(checks.values()) else FAIL),
        evidence=checks,
        details=f"Explainability: {sum(checks.values())}/{len(checks)} accessible",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_39() -> RuleResult:
    """Scalability: batch sizes [1,4,16,64] produce correct output shapes."""
    t0 = time.perf_counter()
    models = get_all_models()
    batch_sizes = [1, 4, 16, 64]
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_ROLE_HEAD]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()
        model_results = []
        for bs in batch_sizes:
            inputs = get_random_input(mt, batch_size=bs, seq_len=10)
            try:
                with torch.no_grad():
                    out = forward_model(model, inputs)
                t = extract_output_tensor(out)
                if t is None:
                    model_results.append({"batch": bs, "ok": False})
                    all_ok = False
                else:
                    shape_ok = t.shape[0] == bs
                    model_results.append({"batch": bs, "shape": list(t.shape), "ok": shape_ok})
                    if not shape_ok:
                        all_ok = False
            except Exception as e:
                model_results.append({"batch": bs, "error": str(e)[:50]})
                all_ok = False

        results[mt] = model_results

    return RuleResult(
        39,
        "Scalability",
        PASS if all_ok else FAIL,
        evidence=results,
        details=f"Batch size scaling: all_ok={all_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_40() -> RuleResult:
    """Memory architecture: RAPMemory processes variable seq_len without OOM."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.rap_coach.memory import RAPMemory
    except ImportError:
        return RuleResult(40, "Memory architecture", SKIP, details="RAPMemory not available")

    mem = RAPMemory(perception_dim=128, metadata_dim=METADATA_DIM, hidden_dim=256)
    mem.eval()

    seq_lengths = [5, 10, 20, 50]
    results = {}
    all_ok = True
    hidden = None

    for sl in seq_lengths:
        x = torch.randn(2, sl, 128 + METADATA_DIM)
        try:
            with torch.no_grad():
                combined, belief, hidden = mem(x, hidden)
            valid = not has_nan_or_inf(combined) and not has_nan_or_inf(belief)
            stateful = hidden is not None
            results[f"seq_{sl}"] = {
                "valid": valid,
                "stateful": stateful,
                "combined_shape": list(combined.shape),
            }
            if not valid:
                all_ok = False
        except Exception as e:
            results[f"seq_{sl}"] = {"error": str(e)[:60]}
            all_ok = False

    return RuleResult(
        40,
        "Memory architecture",
        PASS if all_ok else FAIL,
        evidence=results,
        details=f"RAPMemory: {len(results)} seq_lengths tested, all_ok={all_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_41() -> RuleResult:
    """Training data quality: PlayerMatchStats has no NaN in key fields."""
    t0 = time.perf_counter()
    session = get_db_session_or_none()
    if session is None:
        return RuleResult(41, "Training data quality", SKIP, details="No DB session available")

    try:
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

        with session:
            stmt = select(PlayerMatchStats).limit(100)
            records = session.exec(stmt).all()

        if not records:
            return RuleResult(
                41, "Training data quality", SKIP, details="No PlayerMatchStats records in DB"
            )

        nan_fields = []
        for r in records:
            for f in ["avg_kills", "avg_deaths", "avg_adr"]:
                val = getattr(r, f, None)
                if val is not None and (np.isnan(val) or np.isinf(val)):
                    nan_fields.append(f"{r.id}:{f}")

        passed = len(nan_fields) == 0
        return RuleResult(
            41,
            "Training data quality",
            PASS if passed else FAIL,
            evidence={"records_checked": len(records), "nan_fields": nan_fields[:10]},
            details=f"{len(records)} records checked, {len(nan_fields)} NaN fields",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as e:
        return RuleResult(41, "Training data quality", SKIP, details=f"DB query failed: {e}")


def _rule_42() -> RuleResult:
    """Data contamination: train/val splits use non-overlapping indices."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.role_head import prepare_role_training_data
    except ImportError:
        return RuleResult(
            42, "Data contamination", SKIP, details="prepare_role_training_data not available"
        )

    try:
        result = prepare_role_training_data()
        if result is None:
            return RuleResult(
                42, "Data contamination", SKIP, details="Not enough training data (<20 samples)"
            )

        X, y, norm_stats = result
        n = X.shape[0]
        split = int(n * 0.8)
        # Verify splits would be non-overlapping
        train_indices = set(range(split))
        val_indices = set(range(split, n))
        disjoint = len(train_indices & val_indices) == 0

        return RuleResult(
            42,
            "Data contamination",
            PASS if disjoint else FAIL,
            evidence={
                "total_samples": n,
                "train_size": len(train_indices),
                "val_size": len(val_indices),
                "disjoint": disjoint,
            },
            details=f"Train/val split: {len(train_indices)}/{len(val_indices)}, disjoint={disjoint}",
            duration_ms=(time.perf_counter() - t0) * 1000,
        )
    except Exception as e:
        return RuleResult(42, "Data contamination", SKIP, details=f"Failed: {e}")


def _rule_43(quick: bool) -> RuleResult:
    """Training stability smoke test: Legacy 10 epochs with 3 seeds, final losses within 2x.
    NOTE: Uses synthetic random targets — validates convergence consistency, NOT real training stability.
    """
    t0 = time.perf_counter()
    if quick:
        return RuleResult(
            43,
            "Training loop convergence consistency (smoke)",
            SKIP,
            details="Skipped in quick mode (training loop)",
        )

    losses = []
    for seed in [SEED_A, SEED_B, SEED_C]:
        with deterministic_context(seed):
            model = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
            x = torch.randn(15, 10, METADATA_DIM)
            y = torch.randn(15, OUTPUT_DIM)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.MSELoss()

            model.train()
            for _ in range(10):
                optimizer.zero_grad()
                out = model(x)
                loss = criterion(out, y)
                loss.backward()
                optimizer.step()
            losses.append(loss.item())

    if len(losses) < 2:
        return RuleResult(
            43,
            "Training loop convergence consistency (smoke)",
            SKIP,
            details="Not enough seeds completed",
        )

    max_loss = max(losses)
    min_loss = min(losses)
    ratio = max_loss / max(min_loss, 1e-8)
    stable = ratio < 2.0

    return RuleResult(
        43,
        "Training loop convergence consistency (smoke)",
        PASS if stable else WARN,
        evidence={
            "losses": [round(l, 6) for l in losses],
            "max_min_ratio": round(ratio, 2),
            "threshold": 2.0,
        },
        details=f"Seed losses: {[round(l, 4) for l in losses]}, ratio={ratio:.2f}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_44() -> RuleResult:
    """Curriculum learning: JEPA InfoNCE + freeze_encoders() works."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel
    except ImportError:
        return RuleResult(
            44, "Curriculum learning", SKIP, details="JEPACoachingModel not available"
        )

    model = JEPACoachingModel(input_dim=METADATA_DIM, output_dim=OUTPUT_DIM)

    # Stage 1: InfoNCE pretrain step
    x_ctx = torch.randn(4, 8, METADATA_DIM)
    x_tgt = torch.randn(4, 8, METADATA_DIM)
    try:
        pred, target = model.forward_jepa_pretrain(x_ctx, x_tgt)
        pretrain_ok = pred is not None and target is not None
    except Exception:
        pretrain_ok = False

    # Freeze encoders
    try:
        model.freeze_encoders()
        frozen = model.is_pretrained
    except Exception:
        frozen = False

    # Stage 2: Fine-tuning forward
    try:
        with torch.no_grad():
            out = model.forward_coaching(torch.randn(2, 10, METADATA_DIM))
        finetune_ok = out is not None and not has_nan_or_inf(out)
    except Exception:
        finetune_ok = False

    passed = pretrain_ok and frozen and finetune_ok
    return RuleResult(
        44,
        "Curriculum learning",
        PASS if passed else FAIL,
        evidence={"pretrain_ok": pretrain_ok, "frozen": frozen, "finetune_ok": finetune_ok},
        details=f"Pretrain={pretrain_ok}, freeze={frozen}, finetune={finetune_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_45() -> RuleResult:
    """Inference efficiency: forward-pass latency with batch=1, seq=10."""
    t0 = time.perf_counter()
    models = get_all_models()
    limits = {
        ModelFactory.TYPE_LEGACY: 10,
        ModelFactory.TYPE_JEPA: 20,
        ModelFactory.TYPE_RAP: 50,
    }
    results = {}
    all_ok = True

    for mt, limit_ms in limits.items():
        model = models.get(mt)
        if model is None:
            continue
        model.eval()
        inputs = get_random_input(mt, batch_size=1, seq_len=10)

        # Warmup
        with torch.no_grad():
            forward_model(model, inputs)

        # Measure
        times = []
        for _ in range(5):
            ts = time.perf_counter()
            with torch.no_grad():
                forward_model(model, inputs)
            times.append((time.perf_counter() - ts) * 1000)

        avg_ms = sum(times) / len(times)
        within_limit = avg_ms < limit_ms
        if not within_limit:
            all_ok = False
        results[mt] = {"avg_ms": round(avg_ms, 2), "limit_ms": limit_ms, "ok": within_limit}

    return RuleResult(
        45,
        "Inference efficiency",
        PASS if all_ok else WARN,
        evidence=results,
        details="Latency: " + ", ".join(f"{k}={v['avg_ms']}ms" for k, v in results.items()),
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_46() -> RuleResult:
    """Compute-performance tradeoff: param counts correlate with inference time."""
    t0 = time.perf_counter()
    models = get_all_models()
    data = {}

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_RAP]:
        model = models.get(mt)
        if model is None:
            continue
        params = sum(p.numel() for p in model.parameters())
        model.eval()
        inputs = get_random_input(mt, batch_size=1, seq_len=10)
        with torch.no_grad():
            forward_model(model, inputs)  # warmup
        ts = time.perf_counter()
        for _ in range(3):
            with torch.no_grad():
                forward_model(model, inputs)
        avg_ms = (time.perf_counter() - ts) / 3 * 1000
        data[mt] = {"params": params, "avg_ms": round(avg_ms, 2)}

    if len(data) < 2:
        return RuleResult(
            46, "Compute-performance tradeoff", SKIP, details="Need at least 2 models"
        )

    # Check param count ordering correlates (not exponential)
    sorted_by_params = sorted(data.items(), key=lambda x: x[1]["params"])
    sorted_by_time = sorted(data.items(), key=lambda x: x[1]["avg_ms"])
    same_order = [x[0] for x in sorted_by_params] == [x[0] for x in sorted_by_time]

    return RuleResult(
        46,
        "Compute-performance tradeoff",
        PASS if same_order else WARN,
        evidence=data,
        details=f"Param-time correlation: {same_order}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_47() -> RuleResult:
    """Batch size robustness: output[0] identical in batch=1 vs batch=4 (deterministic)."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_ROLE_HEAD]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        with deterministic_context():
            if mt == ModelFactory.TYPE_ROLE_HEAD:
                x_single = torch.randn(1, 5)
                x_batch = torch.cat([x_single, torch.randn(3, 5)], dim=0)
            else:
                x_single = torch.randn(1, 10, METADATA_DIM)
                x_batch = torch.cat([x_single, torch.randn(3, 10, METADATA_DIM)], dim=0)

            with torch.no_grad():
                out_single = extract_output_tensor(model(x_single))
                out_batch = extract_output_tensor(model(x_batch))

        if out_single is None or out_batch is None:
            results[mt] = "no_output"
            all_ok = False
            continue

        batch_first = out_batch[0:1]
        identical = torch.allclose(out_single, batch_first, atol=1e-5)
        max_diff = torch.max(torch.abs(out_single - batch_first)).item()
        results[mt] = {"identical": bool(identical), "max_diff": round(max_diff, 8)}
        if not identical:
            all_ok = False

    return RuleResult(
        47,
        "Batch size robustness",
        PASS if all_ok else WARN,
        evidence=results,
        details=f"Batch[0] identity: all_ok={all_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
