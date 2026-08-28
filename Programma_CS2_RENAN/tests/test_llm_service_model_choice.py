"""DOCTRINE D-03 regression — the LLM model pick must reach the LIVE service.

LLMService is a process singleton whose model resolves once at construction;
before the `refresh_model` seam existed, the CoachScreen selector persisted
LLM_COACH_MODEL but the running service kept the stale model until an app
restart. These tests exercise the REAL resolution ladder (env -> setting ->
hard default) — no network: the constructor performs no I/O and
`refresh_model` is a pure state change.
"""

from __future__ import annotations

import time

from Programma_CS2_RENAN.backend.services.llm_service import LLMService
from Programma_CS2_RENAN.core import config as core_config


def _patch_setting(monkeypatch, value: str) -> None:
    """Make the ladder's LLM_COACH_MODEL lookup return `value`."""
    real_get_setting = core_config.get_setting

    def fake_get_setting(key, default=None):
        if key == "LLM_COACH_MODEL":
            return value
        return real_get_setting(key, default)

    monkeypatch.setattr(core_config, "get_setting", fake_get_setting)


class TestRefreshModel:
    def test_pick_applies_and_invalidates_availability_cache(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        svc = LLMService(model="gemma4:e2b")
        # Simulate a warm availability cache for the OLD model.
        svc._available = True
        svc._available_checked_at = time.monotonic()

        _patch_setting(monkeypatch, "llama3:8b")
        svc.refresh_model()

        assert svc.model == "llama3:8b"
        # Cache invalidated: the next is_available() must validate the NEW
        # model (family-fallback then fires loudly if it is not installed).
        assert svc._available is None
        assert svc._available_checked_at == 0.0

    def test_env_override_wins_over_ui_pick(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "pinned:model")
        svc = LLMService(model="pinned:model")
        _patch_setting(monkeypatch, "llama3:8b")

        svc.refresh_model()

        # The ladder re-ran and env kept precedence by construction.
        assert svc.model == "pinned:model"

    def test_same_model_is_a_noop(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        svc = LLMService(model="gemma4:e2b")
        svc._available = True
        svc._available_checked_at = time.monotonic()

        _patch_setting(monkeypatch, "gemma4:e2b")
        svc.refresh_model()

        # No pointless cache invalidation for a no-op re-resolution.
        assert svc._available is True

    def test_tools_probe_rekeys_on_switch(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        svc = LLMService(model="gemma4:e2b")
        svc._tools_supported = False
        svc._tools_probe_model = "gemma4:e2b"
        assert svc.tools_supported is False

        _patch_setting(monkeypatch, "llama3:8b")
        svc.refresh_model()

        # The probe cache is keyed to the model name: after a switch the
        # capability is unknown again, so the tool phase re-probes.
        assert svc.tools_supported is None

    def test_hard_default_when_setting_empty(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        svc = LLMService(model="something:else")
        _patch_setting(monkeypatch, "")

        svc.refresh_model()

        # Empty setting falls through to the ladder's hard default.
        assert svc.model == "gemma4:e2b"
