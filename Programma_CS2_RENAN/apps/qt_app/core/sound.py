"""SoundManager — micro-interaction sound effects, gated by app_state.

Plays four short WAV effects: click, success, error, notification. Each
preloaded once via ``QSoundEffect`` so ``play()`` is low-latency. Gated
behind ``AppState.sounds_enabled`` (default False): if the toggle is off
``play()`` is a no-op. Missing WAV files log exactly one WARNING the
first time a caller tries to play them; subsequent attempts are silent
so a shipping build that forgot the assets doesn't spam the log.

File layout (relative to ``PHOTO_GUI/sounds/`` via ``get_resource_path``):

    click.wav
    success.wav
    error.wav
    notification.wav

Users can drop in their own WAVs under ``PHOTO_GUI/sounds/`` — ECC runs
local-only so asset hot-swap is fine.
"""

from __future__ import annotations

import os
from typing import Literal

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

from Programma_CS2_RENAN.apps.qt_app.core.app_state import AppState
from Programma_CS2_RENAN.core.config import get_resource_path
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_sound")

SoundName = Literal["click", "success", "error", "notification"]

_SOUND_DIR = "PHOTO_GUI/sounds"
_FILES: dict[SoundName, str] = {
    "click": "click.wav",
    "success": "success.wav",
    "error": "error.wav",
    "notification": "notification.wav",
}


class SoundManager(QObject):
    """Plays one of four preloaded sound effects when toggled on."""

    def __init__(self, app_state: AppState, parent: QObject | None = None):
        super().__init__(parent)
        self._app_state = app_state
        self._effects: dict[SoundName, QSoundEffect] = {}
        self._missing_warned: set[SoundName] = set()
        self._load_effects()

    def _load_effects(self) -> None:
        sounds_dir = get_resource_path(_SOUND_DIR)
        for name, filename in _FILES.items():
            path = os.path.join(sounds_dir, filename)
            effect = QSoundEffect(self)
            if os.path.exists(path):
                effect.setSource(QUrl.fromLocalFile(path))
                effect.setVolume(0.6)
            self._effects[name] = effect

    def play(self, name: SoundName) -> None:
        """Play the named effect — no-op if sounds disabled or file missing."""
        if not self._app_state.sounds_enabled:
            return
        effect = self._effects.get(name)
        if effect is None:
            return
        # QSoundEffect reports isLoaded() False until the source has been
        # parsed. If a WAV is genuinely missing we warn exactly once.
        if effect.source().isEmpty():
            if name not in self._missing_warned:
                self._missing_warned.add(name)
                _logger.warning(
                    "SoundManager: %r WAV not found (searched %s); silenced for session",
                    name,
                    _SOUND_DIR,
                )
            return
        effect.play()
