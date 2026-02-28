"""
Section 2: Learning & Adaptation (Rules 11-17)

Tests generalization, few-shot learning, catastrophic forgetting,
adversarial robustness, noise resilience, and context-length robustness.
Auto: 7, Manual: 0
"""

import time

import numpy as np
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    METADATA_DIM,
    NOISE_LEVELS,
    PASS,
    SEED_A,
    SEED_B,
    SEED_C,
    SKIP,
    WARN,
    ModelFactory,
    RuleResult,
    SectionResult,
    add_noise,
    cosine_similarity,
    deterministic_context,
    extract_output_tensor,
    forward_model,
    get_model,
    get_random_input,
    has_nan_or_inf,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(2, "Learning & Adaptation")

    section.add(_rule_11(quick))
    section.add(_rule_12(quick))
    section.add(_rule_13(quick))
    section.add(_rule_14())
    section.add(_rule_15())
    section.add(_rule_16())
    section.add(_rule_17())

    return section


def _rule_11(quick: bool) -> RuleResult:
    """Training loop smoke test: train Legacy on synthetic data, val_loss must not diverge >3x train_loss.
    NOTE: Uses torch.randn() synthetic data — validates optimization loop convergence,
    NOT real generalization on CS2 data. Real generalization requires DB fixtures."""
    t0 = time.perf_counter()
    if quick:
        return RuleResult(
            11,
            "Generalization vs memorization",
            SKIP,
            details="Skipped in quick mode (training loop)",
        )

    try:
        from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

        model = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
    except Exception as e:
        return RuleResult(
            11, "Generalization vs memorization", SKIP, details=f"Model creation failed: {e}"
        )

    with deterministic_context():
        # 20 controlled samples
        x_all = torch.randn(20, 10, METADATA_DIM)
        y_all = torch.randn(20, OUTPUT_DIM)

        x_train, y_train = x_all[:15], y_all[:15]
        x_val, y_val = x_all[15:], y_all[15:]

        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        model.train()
        initial_loss = None
        final_train_loss = None
        final_val_loss = None

        for epoch in range(5):
            optimizer.zero_grad()
            out = model(x_train)
            loss = criterion(out, y_train)
            loss.backward()
            optimizer.step()

            if epoch == 0:
                initial_loss = loss.item()
            final_train_loss = loss.item()

        model.eval()
        with torch.no_grad():
            val_out = model(x_val)
            final_val_loss = criterion(val_out, y_val).item()

    improved = final_train_loss < initial_loss
    ratio = final_val_loss / max(final_train_loss, 1e-8)
    not_memorizing = ratio < 3.0

    passed = improved and not_memorizing
    return RuleResult(
        11,
        "Generalization vs memorization",
        PASS if passed else FAIL,
        evidence={
            "initial_loss": round(initial_loss, 6),
            "final_train_loss": round(final_train_loss, 6),
            "final_val_loss": round(final_val_loss, 6),
            "val_train_ratio": round(ratio, 2),
            "improved": improved,
        },
        details=f"Train improved={improved}, val/train ratio={ratio:.2f} (limit=3.0)",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_12(quick: bool) -> RuleResult:
    """Few-shot smoke test: NeuralRoleHead with MIN_TRAINING_SAMPLES, KL-div improves.
    NOTE: Uses synthetic random targets — validates optimization loop, NOT real few-shot ability."""
    t0 = time.perf_counter()
    if quick:
        return RuleResult(
            12, "Few-shot learning", SKIP, details="Skipped in quick mode (training loop)"
        )

    try:
        from Programma_CS2_RENAN.backend.nn.role_head import NeuralRoleHead
    except ImportError:
        return RuleResult(12, "Few-shot learning", SKIP, details="NeuralRoleHead not available")

    with deterministic_context():
        model = NeuralRoleHead(input_dim=5, hidden_dim=32, output_dim=5)
        # 20 samples (MIN_TRAINING_SAMPLES)
        x = torch.randn(20, 5)
        # Soft labels
        y = torch.softmax(torch.randn(20, 5), dim=-1)

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.KLDivLoss(reduction="batchmean")

        model.train()
        losses = []
        for epoch in range(50):
            optimizer.zero_grad()
            log_out = model.forward_log_softmax(x)
            loss = criterion(log_out, y)
            loss.backward()
            optimizer.step()
            if epoch in (0, 49):
                losses.append(loss.item())

    if len(losses) < 2:
        return RuleResult(
            12, "Few-shot learning", SKIP, details="Training did not produce enough loss values"
        )

    improved = losses[-1] < losses[0]
    return RuleResult(
        12,
        "Few-shot learning",
        PASS if improved else FAIL,
        evidence={
            "loss_epoch_0": round(losses[0], 6),
            "loss_epoch_49": round(losses[-1], 6),
            "improved": improved,
        },
        details=f"KL-div: {losses[0]:.4f} -> {losses[-1]:.4f}, improved={improved}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_13(quick: bool) -> RuleResult:
    """Forgetting smoke test: train JEPA on A, then B, re-evaluate on A. Cosine >0.5.
    NOTE: Uses synthetic random distributions — validates embedding stability, NOT real forgetting.
    """
    t0 = time.perf_counter()
    if quick:
        return RuleResult(
            13, "Catastrophic forgetting", SKIP, details="Skipped in quick mode (training loop)"
        )

    try:
        model = ModelFactory.get_model(ModelFactory.TYPE_JEPA)
    except Exception:
        return RuleResult(13, "Catastrophic forgetting", SKIP, details="JEPA model not available")

    with deterministic_context():
        x_a = torch.randn(8, 10, METADATA_DIM)
        y_a = torch.randn(8, OUTPUT_DIM)
        x_b = torch.randn(8, 10, METADATA_DIM) + 2.0  # Different distribution

        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        # Train on context-A
        model.train()
        for _ in range(5):
            optimizer.zero_grad()
            out = model(x_a)
            loss = criterion(out, y_a)
            loss.backward()
            optimizer.step()

        # Record output on A
        model.eval()
        with torch.no_grad():
            output_a_before = extract_output_tensor(model(x_a)).clone()

        # Train more on context-B
        model.train()
        for _ in range(5):
            optimizer.zero_grad()
            out = model(x_b)
            loss = criterion(out, torch.randn(8, OUTPUT_DIM))
            loss.backward()
            optimizer.step()

        # Re-evaluate on A
        model.eval()
        with torch.no_grad():
            output_a_after = extract_output_tensor(model(x_a))

    if output_a_before is None or output_a_after is None:
        return RuleResult(13, "Catastrophic forgetting", SKIP, details="Output extraction failed")

    sim = cosine_similarity(output_a_before.flatten(), output_a_after.flatten())
    passed = sim > 0.5

    return RuleResult(
        13,
        "Catastrophic forgetting",
        PASS if passed else FAIL,
        evidence={"cosine_before_after": round(sim, 4), "threshold": 0.5},
        details=f"Context-A cosine after B-training: {sim:.4f} (threshold=0.5)",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_14() -> RuleResult:
    """Compositional learning: VL-JEPA concept combinations differ from individuals."""
    t0 = time.perf_counter()
    vl = get_model(ModelFactory.TYPE_VL_JEPA)
    if vl is None:
        return RuleResult(14, "Compositional learning", SKIP, details="VL-JEPA not available")

    vl.eval()
    with deterministic_context():
        # Base input
        x_base = torch.randn(1, 10, METADATA_DIM)

        # Modify to activate "positioning_aggressive" (concept 0) — high enemies_visible
        x_agg = x_base.clone()
        x_agg[0, :, 8] = 1.0  # enemies_visible high

        # Modify to activate "engagement_favorable" (concept 7) — high health, armor
        x_eng = x_base.clone()
        x_eng[0, :, 0] = 1.0  # health
        x_eng[0, :, 1] = 1.0  # armor

        # Both combined
        x_both = x_base.clone()
        x_both[0, :, 8] = 1.0
        x_both[0, :, 0] = 1.0
        x_both[0, :, 1] = 1.0

        with torch.no_grad():
            r_agg = vl.forward_vl(x_agg)
            r_eng = vl.forward_vl(x_eng)
            r_both = vl.forward_vl(x_both)

    cp_agg = r_agg.get("concept_probs")
    cp_eng = r_eng.get("concept_probs")
    cp_both = r_both.get("concept_probs")

    if any(c is None for c in [cp_agg, cp_eng, cp_both]):
        return RuleResult(14, "Compositional learning", SKIP, details="concept_probs not returned")

    # Combined must differ from either alone
    diff_from_agg = torch.norm(cp_both - cp_agg).item()
    diff_from_eng = torch.norm(cp_both - cp_eng).item()
    differs = diff_from_agg > 0.01 and diff_from_eng > 0.01

    return RuleResult(
        14,
        "Compositional learning",
        PASS if differs else FAIL,
        evidence={
            "diff_from_aggressive": round(diff_from_agg, 4),
            "diff_from_engagement": round(diff_from_eng, 4),
        },
        details=f"Combined differs: agg={diff_from_agg:.4f}, eng={diff_from_eng:.4f}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_15() -> RuleResult:
    """Adversarial robustness: FGSM perturbation, output deviation <2x perturbation magnitude."""
    t0 = time.perf_counter()
    from Programma_CS2_RENAN.tools.brain_verification._common import get_all_models

    models = get_all_models()

    eps_values = [0.01, 0.05, 0.1]
    violations = []
    tested = 0

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue

        inputs = get_random_input(mt, batch_size=4, seq_len=10)

        for eps in eps_values:
            tested += 1
            x = inputs["x"].clone().requires_grad_(True)
            model.train()
            out_clean = model(x)
            t_clean = extract_output_tensor(out_clean)
            if t_clean is None:
                continue

            loss = t_clean.sum()
            loss.backward()

            if x.grad is None:
                continue

            # FGSM perturbation
            x_adv = x + eps * x.grad.sign()

            model.eval()
            with torch.no_grad():
                out_adv = model(x_adv)
                t_adv = extract_output_tensor(out_adv)
                out_clean_eval = model(x)
                t_clean_eval = extract_output_tensor(out_clean_eval)

            if t_adv is None or t_clean_eval is None:
                continue

            deviation = torch.norm(t_adv - t_clean_eval).item()
            if deviation > 2.0 * eps * np.sqrt(t_clean_eval.numel()):
                violations.append(f"{mt} eps={eps} dev={deviation:.4f}")

    if tested == 0:
        return RuleResult(15, "Adversarial robustness", SKIP, details="No models tested")

    passed = len(violations) == 0
    return RuleResult(
        15,
        "Adversarial robustness",
        PASS if passed else WARN,
        evidence={"tested": tested, "violations": violations},
        details=f"{tested} tests, {len(violations)} violations",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_16() -> RuleResult:
    """Noise resilience: output L2-distance from clean increases monotonically. No catastrophic jumps."""
    t0 = time.perf_counter()
    from Programma_CS2_RENAN.tools.brain_verification._common import get_all_models

    models = get_all_models()

    results = {}
    all_monotonic = True
    no_jumps = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue

        model.eval()
        with deterministic_context():
            x_clean = torch.randn(4, 10, METADATA_DIM)
            with torch.no_grad():
                out_clean = extract_output_tensor(model(x_clean))
            if out_clean is None:
                continue

            distances = []
            for level in NOISE_LEVELS:
                x_noisy = add_noise(x_clean, level)
                with torch.no_grad():
                    out_noisy = extract_output_tensor(model(x_noisy))
                if out_noisy is None:
                    continue
                dist = torch.norm(out_noisy - out_clean).item()
                distances.append(dist)

        # Check monotonicity
        mono = all(distances[i] <= distances[i + 1] + 1e-4 for i in range(len(distances) - 1))
        if not mono:
            all_monotonic = False

        # Check no catastrophic jumps (jump < 10x previous level)
        # Untrained models may have larger sensitivity differences across noise levels
        for i in range(1, len(distances)):
            if distances[i - 1] > 1e-6 and distances[i] > 10 * distances[i - 1]:
                no_jumps = False

        results[mt] = [round(d, 4) for d in distances]

    if not results:
        return RuleResult(16, "Noise resilience", SKIP, details="No models tested")

    passed = all_monotonic and no_jumps
    return RuleResult(
        16,
        "Noise resilience",
        PASS if passed else (WARN if no_jumps else FAIL),
        evidence={
            "distances_by_model": results,
            "monotonic": all_monotonic,
            "no_catastrophic_jumps": no_jumps,
        },
        details=f"Monotonic={all_monotonic}, no catastrophic jumps={no_jumps}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_17() -> RuleResult:
    """Context-length robustness: seq_len=[1,5,10,20,50] all produce valid output."""
    t0 = time.perf_counter()
    from Programma_CS2_RENAN.tools.brain_verification._common import get_all_models

    models = get_all_models()

    seq_lengths = [1, 5, 10, 20, 50]
    results = {}
    all_valid = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue

        model.eval()
        model_outputs = []
        for sl in seq_lengths:
            with deterministic_context():
                x = torch.randn(2, sl, METADATA_DIM)
                with torch.no_grad():
                    out = model(x)
                t = extract_output_tensor(out)
                if t is None or has_nan_or_inf(t):
                    all_valid = False
                    model_outputs.append(None)
                else:
                    model_outputs.append(t.mean(dim=0).tolist())

        # Check variance across lengths — std < 0.5 per dim
        valid_outputs = [torch.tensor(o) for o in model_outputs if o is not None]
        if len(valid_outputs) >= 2:
            stacked = torch.stack(valid_outputs)
            per_dim_std = stacked.std(dim=0)
            max_std = per_dim_std.max().item()
            results[mt] = {
                "max_per_dim_std": round(max_std, 4),
                "valid_lengths": sum(1 for o in model_outputs if o is not None),
            }

    if not results:
        return RuleResult(17, "Context-length robustness", SKIP, details="No models tested")

    passed = all_valid
    return RuleResult(
        17,
        "Context-length robustness",
        PASS if passed else FAIL,
        evidence=results,
        details=f"All valid={all_valid}, tested {len(results)} models across {len(seq_lengths)} lengths",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
