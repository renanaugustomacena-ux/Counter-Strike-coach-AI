"""F2 (TASKS#33) — streaming coaching chat.

Covers the three layers touched: LLMService.chat_stream (Ollama /api/chat
stream parsing), CoachingDialogueEngine.respond_stream (accumulated-text
callback, DR-14 whole-message semantics, cancellation, stall→fallback,
F5-06 history discipline), and the Worker progress plumbing.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest

# ── LLMService.chat_stream ──────────────────────────────────────────────────


def _fake_stream_response(chunks, done_last=True):
    """Build a context-manager mock mimicking requests.post(stream=True)."""
    import json as _json

    lines = [_json.dumps({"message": {"content": c}, "done": False}).encode() for c in chunks]
    if done_last:
        lines.append(_json.dumps({"message": {"content": ""}, "done": True}).encode())

    resp = mock.MagicMock()
    resp.raise_for_status.return_value = None
    resp.iter_lines.return_value = iter(lines)
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_chat_stream_accumulates_and_returns_full_text():
    from Programma_CS2_RENAN.backend.services.llm_service import LLMService

    svc = LLMService(model="gemma4:e2b")
    seen = []
    with mock.patch(
        "Programma_CS2_RENAN.backend.services.llm_service.requests.post",
        return_value=_fake_stream_response(["Hold ", "the ", "angle."]),
    ):
        final = svc.chat_stream([{"role": "user", "content": "tip?"}], on_chunk=seen.append)
    assert final == "Hold the angle."
    # DR-14: every callback gets the FULL accumulated text, not fragments.
    assert seen == ["Hold ", "Hold the ", "Hold the angle."]


def test_chat_stream_prepends_system_prompt():
    from Programma_CS2_RENAN.backend.services.llm_service import LLMService

    svc = LLMService(model="gemma4:e2b")
    captured = {}

    def _capture(url, json=None, timeout=None, stream=None):
        captured["messages"] = json["messages"]
        captured["stream"] = json["stream"]
        return _fake_stream_response(["ok"])

    with mock.patch("Programma_CS2_RENAN.backend.services.llm_service.requests.post", _capture):
        svc.chat_stream([{"role": "user", "content": "q"}], system_prompt="SYS")
    assert captured["stream"] is True
    assert captured["messages"][0] == {"role": "system", "content": "SYS"}


# ── CoachingDialogueEngine.respond_stream ───────────────────────────────────


@pytest.fixture
def streaming_engine():
    """A dialogue engine with a mocked LLM whose chat_stream feeds fixed chunks."""
    from Programma_CS2_RENAN.backend.services.coaching_dialogue import CoachingDialogueEngine

    eng = CoachingDialogueEngine.__new__(CoachingDialogueEngine)
    # Minimal state (bypass __init__'s DB/knowledge bootstrap).
    import threading

    eng._llm = mock.MagicMock()
    eng._player_lookup = None
    eng._player_context = {}
    eng._system_prompt = "SYS"
    eng._history = []
    eng._session_active = True
    eng._state_lock = threading.RLock()
    eng._warmed_up = True
    eng._stream_cancel = threading.Event()
    eng._llm.is_available.return_value = True
    # Neutralize retrieval + intent so the test targets streaming only.
    eng._classify_intent = lambda msg: "general"
    eng._retrieve_context = lambda msg, intent: ""
    eng._build_chat_messages = lambda aug: [{"role": "user", "content": aug}]
    return eng


def test_respond_stream_streams_and_commits_history(streaming_engine):
    eng = streaming_engine

    def _fake_chat_stream(messages, system_prompt=None, on_chunk=None, stall_timeout=None):
        for acc in ["A", "AB", "ABC"]:
            on_chunk(acc)
        return "ABC"

    eng._llm.chat_stream.side_effect = _fake_chat_stream
    seen = []
    out = eng.respond_stream("question", progress_callback=seen.append)

    assert out == "ABC"
    assert seen == ["A", "AB", "ABC"]  # accumulated, in order
    # F5-06: history holds exactly the user+assistant pair, committed once.
    assert eng._history == [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "ABC"},
    ]


def test_respond_stream_cancellation_leaves_history_clean(streaming_engine):
    eng = streaming_engine

    def _fake_chat_stream(messages, system_prompt=None, on_chunk=None, stall_timeout=None):
        on_chunk("partial ")
        eng.cancel_stream()  # user navigates away mid-stream
        on_chunk("partial more")  # this chunk must raise _StreamCancelledError
        return "should not reach"

    eng._llm.chat_stream.side_effect = _fake_chat_stream
    out = eng.respond_stream("q", progress_callback=lambda _a: None)

    assert out == ""  # cancelled → empty
    assert eng._history == []  # DR/F2.3: no bubble committed on cancel


def test_respond_stream_stall_falls_back(streaming_engine):
    import requests

    eng = streaming_engine
    eng._llm.chat_stream.side_effect = requests.exceptions.Timeout("stall")
    eng._fallback_response = lambda msg, intent: "OFFLINE-FALLBACK"

    out = eng.respond_stream("q", progress_callback=lambda _a: None)
    assert out == "OFFLINE-FALLBACK"
    # F5-06 still holds: history has the pair, with the fallback text.
    assert eng._history[-1] == {"role": "assistant", "content": "OFFLINE-FALLBACK"}


# ── Worker progress plumbing ────────────────────────────────────────────────


def test_worker_injects_progress_callback():
    from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

    captured = {}

    def _fn(progress_callback=None):
        captured["has_cb"] = progress_callback is not None
        return "done"

    w = Worker(_fn, wants_progress=True)
    w.run()
    assert captured["has_cb"] is True


def test_worker_omits_callback_without_flag():
    from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker

    captured = {}

    def _fn():
        captured["ran"] = True
        return "done"

    w = Worker(_fn)  # no wants_progress
    w.run()
    assert captured["ran"] is True
