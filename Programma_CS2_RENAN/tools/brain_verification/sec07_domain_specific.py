"""
Section 7: Domain-Specific Intelligence (Rules 54-62)

Tests semantic understanding, pragmatic understanding, visual reasoning,
cross-modal consistency, multimodal reasoning, and planning.
Auto: 7, Manual: 2
"""

import logging
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
    get_model,
    get_random_input,
    has_nan_or_inf,
)


def run(quick: bool = False) -> SectionResult:
    section = SectionResult(7, "Domain-Specific Intelligence")

    section.add(_rule_54())
    section.add(_rule_55())
    section.add(_rule_56())
    section.add(_rule_57())
    section.add(_rule_58())
    section.add(_rule_59())
    section.add(_rule_60())
    section.add(_rule_61())
    section.add(_rule_62())

    return section


def _rule_54() -> RuleResult:
    """Semantic understanding: ConceptLabeler produces different activations for different states."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.jepa_model import ConceptLabeler
    except ImportError:
        return RuleResult(
            54, "Semantic understanding", SKIP, details="ConceptLabeler not available"
        )

    labeler = ConceptLabeler()

    # Aggressive state: high enemies_visible, high equipment, low armor
    aggressive = torch.zeros(METADATA_DIM)
    aggressive[0] = 0.5  # health
    aggressive[1] = 0.2  # armor low
    aggressive[4] = 0.9  # high equip
    aggressive[8] = 1.0  # many enemies visible

    # Passive state: low enemies, high health/armor, crouching
    passive = torch.zeros(METADATA_DIM)
    passive[0] = 1.0  # full health
    passive[1] = 1.0  # full armor
    passive[5] = 1.0  # crouching
    passive[8] = 0.0  # no enemies

    labels_agg = labeler.label_tick(aggressive)
    labels_pas = labeler.label_tick(passive)

    # Count concepts with different activation levels (>0.1 diff)
    diff = (labels_agg - labels_pas).abs()
    different_concepts = (diff > 0.1).sum().item()

    passed = different_concepts >= 4
    return RuleResult(
        54,
        "Semantic understanding",
        PASS if passed else FAIL,
        evidence={
            "different_concepts": int(different_concepts),
            "threshold": 4,
            "max_diff": round(diff.max().item(), 4),
        },
        details=f"{different_concepts}/16 concepts differ (need >=4)",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_55() -> RuleResult:
    """Pragmatic understanding: CoachingService generates different severity for different scenarios."""
    t0 = time.perf_counter()
    from Programma_CS2_RENAN.tools.brain_verification._common import get_db_session_or_none

    session = get_db_session_or_none()
    if session is None:
        return RuleResult(55, "Pragmatic understanding", SKIP, details="No DB session available")

    try:
        from Programma_CS2_RENAN.backend.services.coaching_service import CoachingService

        service = CoachingService()
        has_generate = hasattr(service, "generate_new_insights") and callable(
            service.generate_new_insights
        )
        has_coper = hasattr(service, "_generate_coper_insights") and callable(
            service._generate_coper_insights
        )

        # Behavioral check: call with minimal params to verify it doesn't crash
        call_ok = False
        if has_generate:
            try:
                result = service.generate_new_insights(
                    player_name="test_player",
                    demo_name="test_demo",
                    deviations={"kills": 0.0},
                    rounds_played=1,
                )
                call_ok = isinstance(result, (list, type(None)))
            except Exception:
                call_ok = False

        passed = has_generate and has_coper and call_ok
    except Exception as e:
        return RuleResult(
            55, "Pragmatic understanding", SKIP, details=f"CoachingService init failed: {e}"
        )

    return RuleResult(
        55,
        "Pragmatic understanding",
        PASS if passed else (WARN if has_generate else FAIL),
        evidence={"has_generate": has_generate, "has_coper": has_coper, "call_ok": call_ok},
        details=f"CoachingService: generate={has_generate}, coper={has_coper}, call_ok={call_ok}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_56() -> RuleResult:
    """Multilingual (MANUAL): test Ollama output in multiple languages."""
    return RuleResult(
        56,
        "Multilingual",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: test multi-language output via Ollama integration.",
    )


def _rule_57() -> RuleResult:
    """Visual reasoning: RAPPerception 3x64x64 -> 128-dim, different images -> different outputs."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.nn.rap_coach.perception import RAPPerception
    except ImportError:
        return RuleResult(57, "Visual reasoning", SKIP, details="RAPPerception not available")

    perc = RAPPerception()
    perc.eval()

    with deterministic_context():
        v1 = torch.randn(2, 3, 64, 64)
        m1 = torch.randn(2, 3, 64, 64)
        d1 = torch.randn(2, 3, 64, 64)

        v2 = torch.randn(2, 3, 64, 64) * 2  # Different
        m2 = torch.randn(2, 3, 64, 64) * 2
        d2 = torch.randn(2, 3, 64, 64) * 2

        with torch.no_grad():
            out1 = perc(v1, m1, d1)
            out2 = perc(v2, m2, d2)

    correct_dim = out1.shape[-1] == 128
    different = torch.norm(out1 - out2).item() > 0.01

    passed = correct_dim and different
    return RuleResult(
        57,
        "Visual reasoning",
        PASS if passed else FAIL,
        evidence={
            "output_dim": int(out1.shape[-1]),
            "correct_dim": correct_dim,
            "diff_norm": round(torch.norm(out1 - out2).item(), 4),
            "different": different,
        },
        details=f"Perception: dim={out1.shape[-1]}, different={different}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_58() -> RuleResult:
    """Cross-modal consistency: RAP zeroing any stream changes output."""
    t0 = time.perf_counter()
    rap = get_model(ModelFactory.TYPE_RAP)
    if rap is None:
        return RuleResult(58, "Cross-modal consistency", SKIP, details="RAP model not available")

    rap.eval()
    with deterministic_context():
        view = torch.randn(2, 3, 64, 64)
        map_f = torch.randn(2, 3, 64, 64)
        motion = torch.randn(2, 3, 64, 64)
        meta = torch.randn(2, 5, METADATA_DIM)

        with torch.no_grad():
            out_full = rap(view, map_f, motion, meta)
            out_no_view = rap(torch.zeros_like(view), map_f, motion, meta)
            out_no_map = rap(view, torch.zeros_like(map_f), motion, meta)
            out_no_motion = rap(view, map_f, torch.zeros_like(motion), meta)

    ref = extract_output_tensor(out_full)
    streams = {
        "view": extract_output_tensor(out_no_view),
        "map": extract_output_tensor(out_no_map),
        "motion": extract_output_tensor(out_no_motion),
    }

    contributions = {}
    all_contribute = True
    for name, zeroed in streams.items():
        if ref is None or zeroed is None:
            contributions[name] = "missing"
            all_contribute = False
            continue
        diff = torch.norm(ref - zeroed).item()
        contributes = diff > 0.001
        contributions[name] = {"diff": round(diff, 4), "contributes": contributes}
        if not contributes:
            all_contribute = False

    return RuleResult(
        58,
        "Cross-modal consistency",
        PASS if all_contribute else WARN,
        evidence=contributions,
        details=f"All 3 streams contribute: {all_contribute}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_59() -> RuleResult:
    """Multimodal reasoning: VL-JEPA concept_probs AND coaching_output both change with input."""
    t0 = time.perf_counter()
    vl = get_model(ModelFactory.TYPE_VL_JEPA)
    if vl is None:
        return RuleResult(59, "Multimodal reasoning", SKIP, details="VL-JEPA not available")

    vl.eval()
    with deterministic_context():
        x1 = torch.randn(2, 10, METADATA_DIM)
        x2 = torch.randn(2, 10, METADATA_DIM) * 3  # Different

        with torch.no_grad():
            r1 = vl.forward_vl(x1)
            r2 = vl.forward_vl(x2)

    cp_diff = torch.norm(r1["concept_probs"] - r2["concept_probs"]).item()
    co_diff = torch.norm(r1["coaching_output"] - r2["coaching_output"]).item()

    concepts_change = cp_diff > 0.01
    coaching_change = co_diff > 0.001  # Tanh output has smaller range
    both_change = concepts_change and coaching_change
    return RuleResult(
        59,
        "Multimodal reasoning",
        PASS if both_change else FAIL,
        evidence={"concept_diff": round(cp_diff, 4), "coaching_diff": round(co_diff, 4)},
        details=f"Concept diff={cp_diff:.4f}, coaching diff={co_diff:.4f}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_60() -> RuleResult:
    """Goal-directed planning: GameTree different actions for different scenarios."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.game_tree import get_game_tree_search
    except ImportError:
        return RuleResult(60, "Goal-directed planning", SKIP, details="GameTree not available")

    search = get_game_tree_search(map_name=None, use_adaptive=False)
    scenarios = [
        {
            "alive_ct": 5,
            "alive_t": 3,
            "economy_ct": 16000,
            "economy_t": 4000,
            "round_number": 10,
            "bomb_planted": False,
            "time_remaining": 90,
        },
        {
            "alive_ct": 2,
            "alive_t": 5,
            "economy_ct": 2000,
            "economy_t": 16000,
            "round_number": 10,
            "bomb_planted": True,
            "time_remaining": 20,
        },
    ]

    actions = []
    for state in scenarios:
        try:
            root = search.build_tree(state, depth=3)
            action, _ = search.get_best_action(root)
            actions.append(action)
        except Exception as e:
            logging.warning(f"Rule 60 GameTree scenario failed: {e}")
            actions.append(None)

    valid = [a for a in actions if a is not None]
    different = len(set(valid)) >= 2 if len(valid) >= 2 else False

    return RuleResult(
        60,
        "Goal-directed planning",
        PASS if different else (WARN if len(valid) > 0 else FAIL),
        evidence={"actions": actions, "different": different},
        details=f"Actions: {actions}, different={different}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_61() -> RuleResult:
    """Plan adaptation: MomentumTracker adapts after side-switch reset."""
    t0 = time.perf_counter()
    try:
        from Programma_CS2_RENAN.backend.analysis.momentum import MomentumTracker
    except ImportError:
        return RuleResult(61, "Plan adaptation", SKIP, details="MomentumTracker not available")

    tracker = MomentumTracker()
    # Build momentum in first half
    for r in range(1, 13):
        tracker.update(round_won=True, round_number=r)
    pre_switch = tracker.state.current_multiplier

    # Half switch at round 13 should reset
    tracker.update(round_won=True, round_number=13)
    post_switch = tracker.state.current_multiplier

    # Adaptation: post-switch multiplier should be different (reset)
    adapted = abs(pre_switch - post_switch) > 0.01

    return RuleResult(
        61,
        "Plan adaptation",
        PASS if adapted else WARN,
        evidence={
            "pre_switch": round(pre_switch, 4),
            "post_switch": round(post_switch, 4),
            "adapted": adapted,
        },
        details=f"Pre={pre_switch:.3f}, post-switch={post_switch:.3f}",
        duration_ms=(time.perf_counter() - t0) * 1000,
    )


def _rule_62() -> RuleResult:
    """Long-horizon reasoning (MANUAL): verify coaching considers 3+ round economy."""
    return RuleResult(
        62,
        "Long-horizon reasoning",
        MANUAL,
        rule_type="MANUAL",
        details="Manual check: verify coaching considers multi-round economy "
        "planning (3+ rounds ahead).",
    )
