"""Feature Engineering Module.

Uses lazy imports via __getattr__ to prevent _modulelock deadlocks when
daemon threads (ingestion workers) import submodules while the Kivy UI
thread is active. Python's import lock is not reentrant across threads,
so eager top-level imports cause deadlocks in multi-threaded Kivy apps.
"""

_KAST_NAMES = frozenset({
    "calculate_kast_for_round",
    "calculate_kast_percentage",
    "estimate_kast_from_stats",
})

_ROLE_NAMES = frozenset({
    "PlayerRole",
    "classify_role",
    "extract_role_features",
    "get_role_coaching_focus",
})

_VECTORIZER_NAMES = frozenset({
    "DataQualityError",
    "FeatureExtractor",
    "FEATURE_NAMES",
    "METADATA_DIM",
})


def __getattr__(name: str):
    if name in _KAST_NAMES:
        from Programma_CS2_RENAN.backend.processing.feature_engineering import kast

        return getattr(kast, name)

    if name in _ROLE_NAMES:
        from Programma_CS2_RENAN.backend.processing.feature_engineering import role_features

        return getattr(role_features, name)

    if name in _VECTORIZER_NAMES:
        from Programma_CS2_RENAN.backend.processing.feature_engineering import vectorizer

        return getattr(vectorizer, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DataQualityError",
    "FeatureExtractor",
    "FEATURE_NAMES",
    "METADATA_DIM",
    "calculate_kast_for_round",
    "calculate_kast_percentage",
    "estimate_kast_from_stats",
    "PlayerRole",
    "classify_role",
    "extract_role_features",
    "get_role_coaching_focus",
]
