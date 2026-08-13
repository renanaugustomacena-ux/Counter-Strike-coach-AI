"""DeltaChip — benchmark-relative ± delta annotation (research dossier 29.2).

The teardown finding it implements (cs_platforms §top-patterns #6,
global synthesis #2): raw stats are never shown naked — every headline
number gains a self-referential comparison chip (``▲ +0.09 vs 47-match
avg``), because "the comparison IS the information" and self-baselines
defuse rating distrust.

Vocabulary matches the house idiom (StatBadge trend, Performance
vs-pro captions): ▲ in ``tokens.success`` / ▼ in ``tokens.error``,
JetBrains Mono at caption size, transparent background. A zero or
unknown delta hides the chip entirely — an honest chip never renders
"+0.00" against its own baseline.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class DeltaChip(QLabel):
    """Compact ``▲ +0.09 vs 30-day avg`` / ``▼ -0.12 …`` annotation label.

    Starts hidden; call :meth:`set_delta` with a real delta to show it.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("delta_chip")
        self.setFont(Typography.font("mono"))
        self.hide()

    def set_delta(self, value: float | None, baseline_label: str, fmt: str = "{:+.2f}") -> None:
        """Show ``▲/▼ {value:fmt} {baseline_label}``; zero/None hides.

        Hiding is decided on the FORMATTED value: a +0.004 delta that
        would render "+0.00 vs avg" carries no information and must not
        claim a green arrow (it compares equal to the formatted zero,
        including the "-0.00" case).
        """
        if value is None:
            self.clear()
            self.hide()
            return
        formatted = fmt.format(float(value))
        if formatted in (fmt.format(0.0), fmt.format(-0.0)):
            self.clear()
            self.hide()
            return

        tokens = get_tokens()
        arrow, color = ("▲", tokens.success) if float(value) > 0 else ("▼", tokens.error)
        self.setText(f"{arrow} {formatted} {baseline_label}".rstrip())
        self.setStyleSheet(
            f"color: {color}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        self.show()
