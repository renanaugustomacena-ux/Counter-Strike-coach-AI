"""
Coaching Module - AI-Powered CS2 Coaching Engine.

This module provides the coaching and feedback components for the CS2 analyzer:
- HybridCoachingEngine: Multi-layer generative coaching
- generate_corrections: Generates tactical corrections based on deviation analysis
- ExplanationGenerator: Grounded narrative generation for model predictions
- PlayerCardAssimilator: Interface to professional player baselines
- PlayerTokenResolver: Resolves player tokens for AI coach comparisons
"""

from Programma_CS2_RENAN.backend.coaching.correction_engine import generate_corrections
from Programma_CS2_RENAN.backend.coaching.explainability import ExplanationGenerator
from Programma_CS2_RENAN.backend.coaching.hybrid_engine import HybridCoachingEngine
from Programma_CS2_RENAN.backend.coaching.pro_bridge import (
    PlayerCardAssimilator,
    get_pro_baseline_for_coach,
)
from Programma_CS2_RENAN.backend.coaching.token_resolver import PlayerTokenResolver

__all__ = [
    "HybridCoachingEngine",
    "generate_corrections",
    "ExplanationGenerator",
    "PlayerCardAssimilator",
    "get_pro_baseline_for_coach",
    "PlayerTokenResolver",
]
