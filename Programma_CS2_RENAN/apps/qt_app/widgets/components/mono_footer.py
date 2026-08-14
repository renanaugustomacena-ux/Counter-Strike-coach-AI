"""MonoFooter — bottom-of-screen mono-tertiary annotation line.

Frame convention (17/19/…): a single tiny JetBrains Mono caption naming
the data source, e.g. ``PlayerMatchStats · demo_name=… · rating_components
from hltv_components JSON``. Callers pass the final composed string.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class MonoFooter(QLabel):
    """Mono caption in ``text_tertiary`` (QSS ``QLabel#mono_footer``)."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("mono_footer")
        self.setWordWrap(True)
