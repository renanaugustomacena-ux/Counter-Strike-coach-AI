import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.processing.feature_engineering.base_features import (
    extract_match_stats,
)
from Programma_CS2_RENAN.core.localization import LocalizationManager


def test_extract_match_stats_logic():
    """Verify stats extraction logic with mock data."""
    data = {
        "kills": [1, 2, 0],
        "deaths": [0, 1, 1],
        "adr": [100.0, 120.0, 50.0],
        "headshot_pct": [0.5, 1.0, 0.0],
        "kast": [1.0, 1.0, 0.33],
        "opening_duel": [1, 0, -1],
        "blind_time": [5.0, 2.0, 0.0],
        "enemies_blinded": [2, 1, 0],
        "is_clutch_win": [0, 1, 0],
        "aggression_score": [500.0, 600.0, 200.0],
        "hits": [10, 15, 5],
        "shots": [30, 40, 20],
        "money_spent": [4000, 5000, 3000],
    }
    df = pd.DataFrame(data)
    stats = extract_match_stats(df)

    assert stats["avg_kills"] == 1.0
    assert stats["kd_ratio"] == 1.5
    assert stats["accuracy"] == 30 / 90
    assert stats["opening_duel_win_pct"] == 0.5  # 1 win, 1 loss, 1 none


def test_extract_match_stats_single_round():
    """Edge case: single-round DataFrame still produces valid stats."""
    data = {
        "kills": [3],
        "deaths": [1],
        "adr": [150.0],
        "headshot_pct": [0.66],
        "kast": [1.0],
        "opening_duel": [1],
        "blind_time": [0.0],
        "enemies_blinded": [0],
        "is_clutch_win": [0],
        "aggression_score": [700.0],
        "hits": [8],
        "shots": [12],
        "money_spent": [5000],
    }
    df = pd.DataFrame(data)
    stats = extract_match_stats(df)

    assert stats["avg_kills"] == 3.0
    assert stats["avg_deaths"] == 1.0
    assert stats["kd_ratio"] == 3.0
    assert stats["accuracy"] == 8 / 12


def test_localization_switching():
    """Verify localization manager switches languages correctly."""
    i18n = LocalizationManager()
    i18n.set_language("en")
    assert i18n.get_text("dashboard") == "Dashboard"

    i18n.set_language("pt")
    assert i18n.get_text("dashboard") == "Painel de Controle"

    i18n.set_language("it")
    assert i18n.get_text("dashboard") == "Dashboard"
    assert i18n.get_text("coaching") == "Suggerimenti Coach"


def test_localization_missing_key_returns_key():
    """LOC-02 fallback: unknown key returns the raw key string."""
    i18n = LocalizationManager()
    i18n.set_language("en")
    result = i18n.get_text("nonexistent_key_xyz_42")
    assert result == "nonexistent_key_xyz_42"


def test_localization_all_supported_languages():
    """All supported languages must provide the 'dashboard' key."""
    i18n = LocalizationManager()
    for lang in ("en", "pt", "it"):
        i18n.set_language(lang)
        text = i18n.get_text("dashboard")
        assert isinstance(text, str)
        assert len(text) > 0, f"Empty 'dashboard' text for language {lang}"
