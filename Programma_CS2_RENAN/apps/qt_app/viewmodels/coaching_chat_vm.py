"""CoachingChatViewModel — Qt port of legacy_kivy/coaching_chat_vm.py.

Drives the interactive coaching chat panel via CoachingDialogueEngine + Ollama.
All engine calls run in Worker background threads; signals auto-marshal to main thread.
"""

import threading

from PySide6.QtCore import QObject, QThreadPool, Signal

from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_coaching_chat_vm")


class CoachingChatViewModel(QObject):
    """Interactive coaching chat backed by CoachingDialogueEngine."""

    messages_changed = Signal(list)
    is_loading_changed = Signal(bool)
    is_available_changed = Signal(bool)
    session_active_changed = Signal(bool)
    # F2 (TASKS#33): fires as streamed tokens arrive so the view can repaint
    # the in-progress assistant bubble without a full list rebuild per chunk.
    streaming_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = None
        self._messages: list[dict] = []
        self._lock = threading.Lock()
        self._session_active = False
        # F2: coalesce chunk repaints (>=30ms) to avoid flooding the event loop.
        self._stream_buf = ""
        self._stream_dirty = False

    def _ensure_engine(self):
        if self._engine is None:
            from Programma_CS2_RENAN.backend.services.coaching_dialogue import get_dialogue_engine

            self._engine = get_dialogue_engine()

    # ── Public API ──

    def check_and_start(self, player_name: str, demo_name: str | None = None):
        """Check availability, then start session if available (no race condition)."""
        self._pending_player = player_name
        self._pending_demo = demo_name
        self._ensure_engine()
        worker = Worker(self._bg_check)
        worker.signals.result.connect(self._on_availability_then_start)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def check_availability(self):
        self._ensure_engine()
        worker = Worker(self._bg_check)
        worker.signals.result.connect(self._on_availability)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def start_session(self, player_name: str, demo_name: str | None = None):
        if self._session_active:
            return
        self._ensure_engine()
        self.is_loading_changed.emit(True)
        worker = Worker(self._bg_start, player_name, demo_name)
        worker.signals.result.connect(self._on_session_started)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def send_message(self, text: str):
        text = text.strip()
        if not text:
            return
        self._ensure_engine()

        with self._lock:
            self._messages.append({"role": "user", "content": text})
            self.messages_changed.emit(list(self._messages))

        self.is_loading_changed.emit(True)
        self._stream_buf = ""
        worker = Worker(self._bg_respond_stream, text, wants_progress=True)
        worker.signals.progress.connect(self._on_stream_chunk)
        worker.signals.result.connect(self._on_response)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def cancel_response(self):
        """F2.3: abort the in-flight streamed response (e.g. user navigates away)."""
        if self._engine is not None:
            self._engine.cancel_stream()

    def clear_session(self):
        self.cancel_response()
        self._ensure_engine()
        # QT-02: Wrap engine call in Worker to avoid main-thread freeze
        worker = Worker(self._engine.clear_session)
        worker.signals.finished.connect(self._on_session_cleared)
        QThreadPool.globalInstance().start(worker)

    def _on_session_cleared(self):
        with self._lock:
            self._messages.clear()
        self._session_active = False
        self.messages_changed.emit([])
        self.session_active_changed.emit(False)
        self.is_loading_changed.emit(False)

    # ── Background tasks ──

    def _bg_check(self):
        return self._engine.is_available

    def _bg_start(self, player_name: str, demo_name: str | None):
        return self._engine.start_session(player_name, demo_name)

    def _bg_respond_stream(self, text: str, progress_callback=None):
        # Worker injects progress_callback when wants_progress=True (F2).
        return self._engine.respond_stream(text, progress_callback=progress_callback)

    # ── Result callbacks (main thread) ──

    def _on_availability(self, available):
        self.is_available_changed.emit(bool(available))

    def _on_availability_then_start(self, available):
        self.is_available_changed.emit(bool(available))
        if available and not self._session_active:
            player = getattr(self, "_pending_player", "")
            demo = getattr(self, "_pending_demo", None)
            if player:
                self.start_session(player, demo)
        elif not available:
            # Show a system message so the user knows why chat won't work
            with self._lock:
                self._messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Coach is offline. Make sure Ollama is running:\n"
                            "  1. ollama serve\n"
                            "  2. ollama pull gemma4:e2b"
                        ),
                    }
                )
            self.messages_changed.emit(list(self._messages))

    def _on_session_started(self, opening):
        if opening:
            with self._lock:
                self._messages.append({"role": "assistant", "content": str(opening)})
            self.messages_changed.emit(list(self._messages))
        self._session_active = True
        self.session_active_changed.emit(True)
        self.is_loading_changed.emit(False)

    def _on_stream_chunk(self, accumulated):
        # F2: accumulated is the FULL assistant text so far (DR-14). Emit the
        # live buffer; the view repaints the in-progress bubble. The final
        # committed message still arrives via _on_response.
        self._stream_buf = str(accumulated)
        self.streaming_changed.emit(self._stream_buf)

    def _on_response(self, response):
        # F2.3: a cancelled stream returns "" and must not append a bubble.
        if response:
            with self._lock:
                self._messages.append({"role": "assistant", "content": str(response)})
            self.messages_changed.emit(list(self._messages))
        self._stream_buf = ""
        self.is_loading_changed.emit(False)

    def _on_error(self, msg):
        logger.error("coaching_chat_vm error: %s", msg)
        with self._lock:
            self._messages.append(
                {
                    "role": "system",
                    "content": f"Error: {msg}",
                }
            )
        self.messages_changed.emit(list(self._messages))
        self.is_loading_changed.emit(False)
