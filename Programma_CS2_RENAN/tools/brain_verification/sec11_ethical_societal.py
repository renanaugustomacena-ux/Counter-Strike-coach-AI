"""
Section 11: Ethical & Societal Impact (Rules 81-89)

Tests disparate impact, accessibility, decision documentation, privacy,
and security considerations.
Auto: 3, Manual: 6
"""

import time

import torch

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
    section = SectionResult(11, "Ethical & Societal Impact")

    section.add(_rule_81())
    section.add(_rule_82())
    section.add(_rule_83())
    section.add(_rule_84())
    section.add(_rule_85())
    section.add(_rule_86())
    section.add(_rule_87())
    section.add(_rule_88())
    section.add(_rule_89())

    return section


def _rule_81() -> RuleResult:
    """Disparate impact: map_id + round_phase variation -> output variance <20% of overall."""
    t0 = time.perf_counter()
    models = get_all_models()
    results = {}
    all_ok = True

    for mt in [ModelFactory.TYPE_LEGACY, ModelFactory.TYPE_JEPA]:
        model = models.get(mt)
        if model is None:
            continue
        model.eval()

        with deterministic_context():
            base = torch.randn(8, 10, METADATA_DIM)
            all_outputs = []

            for map_val in [0.0, 0.5, 1.0]:
                for phase_val in [0.0, 0.33, 0.66, 1.0]:
                    x = base.clone()
                    x[:, :, 17] = map_val  # map_id
                    x[:, :, 18] = phase_val  # round_phase
                    with torch.no_grad():
                        out = model(x)
                    t = extract_output_tensor(out)
                    if t is not None:
                        all_outputs.append(t)

        if len(all_outputs) < 2:
            continue

        # Overall variance
        stacked = torch.stack(all_outputs)
        overall_var = stacked.var().item()

        # Map-only variance (average across phases)
        map_outputs = {}
        for i, m in enumerate([0.0, 0.5, 1.0]):
            map_outputs[m] = []
        idx = 0
        for map_val in [0.0, 0.5, 1.0]:
            for _ in [0.0, 0.33, 0.66, 1.0]:
                if idx < len(all_outputs):
                    map_outputs[map_val].append(all_outputs[idx])
                idx += 1

        map_means = []
        for m, outs in map_outputs.items():
            if outs:
                map_means.append(torch.stack(outs).mean(dim=0))

        if len(map_means) >= 2:
            map_var = torch.stack(map_means).var().item()
            ratio = map_var / max(overall_var, 1e-8)
            fair = ratio < 0.20
            if not fair:
                all_ok = False
            results[mt] = {
                "map_var": round(map_var, 6),
                "overall_var": round(overall_var, 6),
                "ratio": round(ratio, 4),
                "fair": fair,
            }

    if not results:
        return RuleResult(81, "Disparate impact", SKIP, details="No models available")

    return RuleResult(
        81,
        "Disparate impact",
        PASS if all_ok else WARN,
        evidence=results,
        details=f"Map/phase variance ratio: all_fair={all_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_82() -> RuleResult:
    """Stereotype/bias (MANUAL): review coaching for playstyle stereotyping."""
    return RuleResult(
        82,
        "Stereotype/bias",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: review coaching outputs for playstyle "
        "stereotyping. Document findings.",
    )


def _rule_83() -> RuleResult:
    """Accessibility (MANUAL): WCAG 2.1 AA verification for Kivy UI."""
    return RuleResult(
        83,
        "Accessibility",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: WCAG 2.1 AA verification for Kivy UI "
        "components. Document procedure.",
    )


def _rule_84() -> RuleResult:
    """Decision documentation: all forward passes include explainability outputs."""
    t0 = time.perf_counter()
    models = get_all_models()
    checks = {}

    # Legacy: gate_weights
    legacy = models.get(ModelFactory.TYPE_LEGACY)
    if legacy is not None:
        checks["legacy_gate"] = hasattr(legacy, "gate")

    # RAP: attribution
    rap = models.get(ModelFactory.TYPE_RAP)
    if rap is not None:
        rap.eval()
        inputs = get_random_input(ModelFactory.TYPE_RAP, batch_size=1, seq_len=5)
        with torch.no_grad():
            out = forward_model(rap, inputs)
        checks["rap_attribution"] = isinstance(out, dict) and "attribution" in out

    # VL-JEPA: concept_probs
    vl = models.get(ModelFactory.TYPE_VL_JEPA)
    if vl is not None:
        vl.eval()
        x = torch.randn(1, 10, METADATA_DIM)
        with torch.no_grad():
            out = vl.forward_vl(x)
        checks["vl_concepts"] = "concept_probs" in out

    passed = all(checks.values()) if checks else False
    return RuleResult(
        84,
        "Decision documentation",
        PASS if passed else FAIL,
        evidence=checks,
        details=f"Explainability: {sum(checks.values())}/{len(checks)} models",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_85() -> RuleResult:
    """Stakeholder input (MANUAL): stakeholder review procedure."""
    return RuleResult(
        85,
        "Stakeholder input",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: stakeholder review of AI coaching system. " "Document procedure.",
    )


def _rule_86() -> RuleResult:
    """Impact assessment (MANUAL): coaching impact assessment."""
    return RuleResult(
        86,
        "Impact assessment",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: assess coaching impact on player behavior "
        "and performance. Document procedure.",
    )


def _rule_87() -> RuleResult:
    """Privacy: FeatureExtractor 19-dim vector does NOT contain PII."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.processing.feature_engineering.vectorizer import (
            METADATA_DIM,
            FeatureExtractor,
        )
    except ImportError:
        return RuleResult(87, "Privacy", SKIP, details="FeatureExtractor not available")

    feature_names = FeatureExtractor.get_feature_names()
    # Exact-match PII identifiers — not substring matching, to avoid false
    # positives like "equipment_value" matching "value".
    pii_fields = {"player_name", "steamid", "steam_id", "ip_address", "email", "real_name"}

    found_pii = [f for f in feature_names if f.lower() in pii_fields]
    dim_ok = len(feature_names) == METADATA_DIM

    passed = len(found_pii) == 0 and dim_ok
    return RuleResult(
        87,
        "Privacy",
        PASS if passed else FAIL,
        evidence={
            "feature_count": len(feature_names),
            "pii_found": found_pii,
            "dim_ok": dim_ok,
            "features": feature_names,
        },
        details=f"Features: {len(feature_names)} dims, PII found={found_pii}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_88() -> RuleResult:
    """Adversarial security (MANUAL): adversarial testing against Ollama endpoint."""
    return RuleResult(
        88,
        "Adversarial security",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: test adversarial inputs against Ollama "
        "endpoint. Document procedure.",
    )


def _rule_89() -> RuleResult:
    """Model theft resistance (MANUAL): .pt files not publicly served."""
    return RuleResult(
        89,
        "Model theft resistance",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: verify .pt files not publicly served. "
        "Check MODELS_DIR permissions.",
    )
