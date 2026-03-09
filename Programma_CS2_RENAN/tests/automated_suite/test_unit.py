import pandas as pd
import pytest

from Programma_CS2_RENAN.backend.processing.feature_engineering.base_features import (
    extract_match_stats,
)
from Programma_CS2_RENAN.core.localization import LocalizationManager


def test_extract_match_stats_logic():
    """Unit Test: Verify stats extraction logic with mock data."""
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


def test_localization_switching():
    """Unit Test: Verify localization manager switches languages."""
    i18n = LocalizationManager()
    i18n.set_language("en")
    assert i18n.get_text("dashboard") == "Dashboard"

    i18n.set_language("pt")
    assert i18n.get_text("dashboard") == "Painel de Controle"

    i18n.set_language("it")
    assert i18n.get_text("dashboard") == "Dashboard"
    # Update expected string to match current dictionaries
    assert i18n.get_text("coaching") == "Suggerimenti Coach"
