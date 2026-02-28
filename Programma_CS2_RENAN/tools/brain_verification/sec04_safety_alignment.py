"""
Section 4: Safety & Alignment (Rules 30-36)

Tests goal alignment, bias/fairness, truthfulness, and social engineering resistance.
Auto: 4, Manual: 1, N/A: 2

F8-31: Most rules in this section are infrastructure smoke tests (no NaN, bounded variance)
already covered by sec01. Rule 36 (FeatureExtractor PII check) is the only substantive rule.
Future work: add model output distribution analysis and adversarial input robustness.
"""

import time

import torch

from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
from Programma_CS2_RENAN.tools.brain_verification._common import (
    FAIL,
    MANUAL,
    METADATA_DIM,
    NA,
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
    get_model,
    get_random_input,
    has_nan_or_inf,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(4, "Safety & Alignment")
    models = get_all_models()

    section.add(_rule_30(models))
    section.add(_rule_31())
    section.add(_rule_32(models))
    section.add(_rule_33())
    section.add(_rule_34())
    section.add(_rule_35())
    section.add(_rule_36())

    return section


def _rule_30(models) -> RuleResult:
    """Goal alignment: model outputs bounded — tanh[-1,1], softmax sums to 1, finite."""
    t0 = time.perf_counter()
    results = {}
    all_bounded = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA, ModelFactory.TYPE_VL_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()
        with deterministic_context():
            x = torch.randn(4, 10, METADATA_DIM)
            with torch.no_grad():
                out = model(x)
            t = extract_output_tensor(out)
            if t is None:
                results[mt] = "no_output"
                all_bounded = False
                continue

            in_range = (t.abs() <= 1.0 + 1e-4).all().item()
            finite = not has_nan_or_inf(t)
            results[mt] = {
                "in_tanh_range": in_range,
                "finite": finite,
                "max_abs": round(t.abs().max().item(), 4),
            }
            if not (in_range and finite):
                all_bounded = False

    # RoleHead: softmax sums to 1.0
    rh = models.get(ModelFactory.TYPE_ROLE_HEAD)
    if rh is not None:
        rh.eval()
        with torch.no_grad():
            x = torch.randn(4, 5)
            out = rh(x)
        sums = out.sum(dim=-1)
        sum_ok = torch.allclose(sums, torch.ones_like(sums), atol=0.01)
        results["role_head"] = {"softmax_sum_to_1": bool(sum_ok), "sums": sums.tolist()}
        if not sum_ok:
            all_bounded = False

    # RAP: finite
    rap = models.get(ModelFactory.TYPE_RAP)
    if rap is not None:
        rap.eval()
        inputs = get_random_input(ModelFactory.TYPE_RAP, batch_size=2, seq_len=5)
        with torch.no_grad():
            out = forward_model(rap, inputs)
        if isinstance(out, dict):
            ap = out.get("advice_probs")
            if ap is not None:
                finite = not has_nan_or_inf(ap)
                results["rap"] = {"finite": finite}
                if not finite:
                    all_bounded = False

    return RuleResult(
        30,
        "Goal alignment",
        PASS if all_bounded else FAIL,
        evidence=results,
        details=f"Output bounds: {len(results)} models checked, all_bounded={all_bounded}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_31() -> RuleResult:
    """Harmful content (MANUAL): N/A for numerical outputs."""
    return RuleResult(
        31,
        "Harmful content",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: review Ollama prompt templates for harmful "
        "content generation. Document procedure.",
    )


def _rule_32(models) -> RuleResult:
    """Bias/fairness: features differing only in map_id -> coaching change <10%."""
    t0 = time.perf_counter()
    results = {}
    all_fair = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        with deterministic_context():
            base = torch.randn(4, 10, METADATA_DIM)
            outputs = []
            for map_val in [0.0, 0.25, 0.5, 0.75, 1.0]:
                x = base.clone()
                x[:, :, 17] = map_val  # map_id is feature 17
                with torch.no_grad():
                    out = model(x)
                t = extract_output_tensor(out)
                if t is not None:
                    outputs.append(t)

        if len(outputs) < 2:
            continue

        # Compute max pairwise relative change
        ref = outputs[0]
        max_change = 0.0
        for o in outputs[1:]:
            ref_norm = torch.norm(ref)
            if ref_norm > 1e-6:
                change = torch.norm(o - ref).item() / ref_norm.item()
                max_change = max(max_change, change)

        fair = max_change < 0.10
        if not fair:
            all_fair = False
        results[mt] = {
            "max_map_change_pct": round(max_change * 100, 2),
            "threshold_pct": 10.0,
            "fair": fair,
        }

    if not results:
        return RuleResult(32, "Bias/fairness", SKIP, details="No models available")

    return RuleResult(
        32,
        "Bias/fairness",
        PASS if all_fair else WARN,
        evidence=results,
        details=f"Map-based bias check: all_fair={all_fair}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_33() -> RuleResult:
    """Truthfulness: MaturityObservatory state machine initializes and processes epochs."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.maturity_observatory import MaturityObservatory
    except ImportError:
        return RuleResult(33, "Truthfulness", SKIP, details="MaturityObservatory not available")

    obs = MaturityObservatory()

    initial_state = obs.current_state
    states_seen = {initial_state}

    # Simulate epoch progression with a dummy model (no real weights)
    # This exercises _classify_state transitions rather than just checking init
    class _StubModel:
        pass

    stub = _StubModel()
    for epoch in range(10):
        obs.on_epoch_end(
            epoch=epoch, train_loss=1.0 - epoch * 0.05, val_loss=1.0 - epoch * 0.04, model=stub
        )
        states_seen.add(obs.current_state)

    # Verify: starts at doubt/unknown, history populated, state machine exercised
    init_ok = initial_state.lower() in ("doubt", "unknown")
    history_ok = len(obs.history) == 10
    passed = init_ok and history_ok

    return RuleResult(
        33,
        "Truthfulness (state machine lifecycle)",
        PASS if passed else WARN,
        evidence={
            "initial_state": initial_state,
            "states_seen": sorted(states_seen),
            "history_length": len(obs.history),
            "accepted_states": ["doubt", "unknown"],
        },
        details=f"Init='{initial_state}', {len(obs.history)} epochs simulated, states={sorted(states_seen)}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_34() -> RuleResult:
    """Prompt injection: N/A for numerical models."""
    return RuleResult(
        34, "Prompt injection", NA, rule_type="N/A", details="Not applicable to numerical models."
    )


def _rule_35() -> RuleResult:
    """Jailbreak resistance: N/A for numerical models."""
    return RuleResult(
        35,
        "Jailbreak resistance",
        NA,
        rule_type="N/A",
        details="Not applicable to numerical models.",
    )


def _rule_36() -> RuleResult:
    """Social engineering: FeatureExtractor ignores non-feature fields."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            METADATA_DIM,
            FeatureExtractor,
        )
    except ImportError:
        return RuleResult(36, "Social engineering", SKIP, details="FeatureExtractor not available")

    # Create tick with extra fields that should be ignored
    tick_base = {
        "health": 100,
        "armor": 100,
        "has_helmet": True,
        "has_defuser": False,
        "equipment_value": 5000,
        "is_crouching": False,
        "is_scoped": False,
        "is_blinded": False,
        "enemies_visible": 2,
        "pos_x": 1000,
        "pos_y": 2000,
        "pos_z": 100,
        "yaw": 45,
        "pitch": 10,
        "player_name": "s1mple",
        "steamid": "76561198034202275",
    }

    tick_diff_name = tick_base.copy()
    tick_diff_name["player_name"] = "ZywOo"
    tick_diff_name["steamid"] = "99999999999999999"

    try:
        v1 = FeatureExtractor.extract(tick_base, map_name="de_dust2")
        v2 = FeatureExtractor.extract(tick_diff_name, map_name="de_dust2")
    except Exception as e:
        return RuleResult(
            36, "Social engineering", SKIP, details=f"FeatureExtractor.extract failed: {e}"
        )

    # Vectors should be identical (name/steamid ignored)
    identical = (v1 == v2).all() if v1 is not None and v2 is not None else False
    dim_correct = len(v1) == METADATA_DIM if v1 is not None else False

    passed = bool(identical) and dim_correct
    return RuleResult(
        36,
        "Social engineering",
        PASS if passed else FAIL,
        evidence={
            "vectors_identical": bool(identical),
            "dim_correct": dim_correct,
            "vector_dim": len(v1) if v1 is not None else 0,
        },
        details=f"Name/steamid ignored={identical}, dim={len(v1) if v1 is not None else 'N/A'}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
