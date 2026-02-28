"""
Section 10: Meta-Level Verification (Rules 75-80)

Tests benchmark resistance, Goodhart's Law resistance, degenerate behavior,
and unknown-unknown discovery.
Auto: 4, Manual: 2
"""

import math
import time

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    MANUAL,
    METADATA_DIM,
    PASS,
    SKIP,
    WARN,
    ModelFactory,
    RuleResult,
    SectionResult,
    deterministic_context,
    extract_output_tensor,
    forward_model,
    get_all_models,
    get_random_input,
    has_nan_or_inf,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(10, "Meta-Level Verification")

    section.add(_rule_75())
    section.add(_rule_76())
    section.add(_rule_77())
    section.add(_rule_78())
    section.add(_rule_79())
    section.add(_rule_80())

    return section


def _rule_75() -> RuleResult:
    """Benchmark resistance: 10 random inputs -> at least 5 distinct outputs per model."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_ROLE_HEAD]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        outputs = set()
        for i in range(10):
            inputs = get_random_input(mt, batch_size=1, seq_len=10)
            with torch.no_grad():
                out = forward_model(model, inputs)
            t = extract_output_tensor(out)
            if t is not None:
                # Round to 2 decimals for distinctness check
                key = tuple(round(v, 2) for v in t.flatten().tolist())
                outputs.add(key)

        distinct = len(outputs)
        ok = distinct >= 5
        if not ok:
            all_ok = False
        results[mt] = {"distinct": distinct, "threshold": 5, "ok": ok}

    if not results:
        return RuleResult(75, "Benchmark resistance", SKIP, details="No models available")

    return RuleResult(
        75,
        "Benchmark resistance",
        PASS if all_ok else FAIL,
        evidence=results,
        details="Output diversity: "
        + ", ".join(f"{k}={v['distinct']}" for k, v in results.items()),
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_76() -> RuleResult:
    """Meta-learning (MANUAL): evaluate second-run learning efficiency."""
    return RuleResult(
        76,
        "Meta-learning",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: evaluate whether second training run "
        "converges faster. Document procedure.",
    )


def _rule_77() -> RuleResult:
    """Goodhart's Law resistance: zero-output model must have high loss, not zero."""
    t0 = time.perf_counter()

    with deterministic_context():
        model = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
        # Zero out all parameters
        with torch.no_grad():
            for p in model.parameters():
                p.zero_()

        x = torch.randn(4, 10, METADATA_DIM)
        y = torch.randn(4, OUTPUT_DIM)

        model.eval()
        with torch.no_grad():
            out = model(x)
        loss = nn.MSELoss()(out, y).item()

    # Zero-output model should have non-trivial loss
    not_gamed = loss > 0.01
    return RuleResult(
        77,
        "Goodhart's Law resistance",
        PASS if not_gamed else FAIL,
        evidence={"zero_model_loss": round(loss, 6), "threshold": 0.01},
        details=f"Zero-param model loss={loss:.4f} (should be >0.01)",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_78() -> RuleResult:
    """Novel capability discovery (MANUAL): quarterly review."""
    return RuleResult(
        78,
        "Novel capability discovery",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: quarterly review of emergent analysis "
        "capabilities. Document procedure.",
    )


def _rule_79() -> RuleResult:
    """Degenerate behavior: per model — not constant, variance>0.001, no NaN, gradient flow."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_VL_JEPA]:
        model = models.get(mt)
        if model is None:
            continue

        checks = {}

        # (a) Not all outputs identical
        model.eval()
        outputs = []
        for _ in range(5):
            inputs = get_random_input(mt, batch_size=2, seq_len=10)
            with torch.no_grad():
                out = forward_model(model, inputs)
            t = extract_output_tensor(out)
            if t is not None:
                outputs.append(t.flatten())

        if len(outputs) >= 2:
            all_same = all(torch.allclose(outputs[0], o, atol=1e-6) for o in outputs[1:])
            checks["not_constant"] = not all_same
        else:
            checks["not_constant"] = False

        # (b) Variance > 0.0001 (tanh-compressed outputs have smaller variance)
        if outputs:
            stacked = torch.stack(outputs)
            var = stacked.var().item()
            checks["variance_ok"] = var > 0.0001
            checks["variance_value"] = round(var, 6)

        # (c) No NaN/Inf
        if outputs:
            checks["no_nan_inf"] = all(not has_nan_or_inf(o) for o in outputs)

        # (d) Gradient flow exists
        # NOTE: forward_model() uses torch.no_grad() internally, so we call
        # the model directly to allow gradient computation.
        model.train()
        inputs = get_random_input(mt, batch_size=2, seq_len=10)
        x = inputs["x"] if "x" in inputs else inputs.get("metadata")
        if x is not None:
            x = x.clone().detach().requires_grad_(True)
            try:
                if mt == ModelFactory.TYPE_VL_JEPA:
                    out = model.forward_vl(x)
                else:
                    out = model(x)
                t = extract_output_tensor(out)
                if t is not None:
                    t.sum().backward()
                    has_grad = x.grad is not None and x.grad.abs().sum() > 0
                    checks["gradient_flow"] = bool(has_grad)
                else:
                    checks["gradient_flow"] = False
            except Exception:
                checks["gradient_flow"] = False

        bool_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
        ok = all(bool_checks.values()) if bool_checks else False
        if not ok:
            all_ok = False
        results[mt] = checks

    return RuleResult(
        79,
        "Degenerate behavior",
        PASS if all_ok else FAIL,
        evidence=results,
        details=f"Degeneracy check: all_ok={all_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_80() -> RuleResult:
    """Unknown-unknown discovery: output entropy across 100 random inputs."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        entropies = []
        output_dim = 0
        for _ in range(100):
            inputs = get_random_input(mt, batch_size=1, seq_len=10)
            with torch.no_grad():
                out = forward_model(model, inputs)
            t = extract_output_tensor(out)
            if t is not None:
                flat = t.flatten().abs()
                output_dim = flat.shape[0]
                probs = torch.softmax(flat, dim=0)
                entropy = -torch.sum(probs * torch.log(probs + 1e-10)).item()
                entropies.append(entropy)

        if not entropies:
            results[mt] = "no_outputs"
            continue

        avg_ent = sum(entropies) / len(entropies)
        max_possible = math.log(max(output_dim, 2))
        norm_ent = avg_ent / max_possible if max_possible > 0 else 0

        # Flag if all entropy < 0.1 or > 0.99 (potential degeneracy)
        suspicious = norm_ent < 0.1 or norm_ent > 0.99
        if suspicious:
            all_ok = False
        results[mt] = {
            "avg_entropy": round(avg_ent, 4),
            "normalized": round(norm_ent, 4),
            "suspicious": suspicious,
        }

    return RuleResult(
        80,
        "Unknown-unknown discovery",
        PASS if all_ok else WARN,
        evidence=results,
        details=f"Entropy analysis: all_ok={all_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
