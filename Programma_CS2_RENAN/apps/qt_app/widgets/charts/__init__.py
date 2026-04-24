"""QtCharts-based chart widgets — replaces matplotlib-to-texture Kivy hack."""

import re

from PySide6.QtGui import QColor

_RGBA_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")


def token_color(value: str) -> QColor:
    """Parse a design-token color string into a QColor.

    Accepts:
        "#RRGGBB"           -> opaque hex
        "rgba(R, G, B, A)"  -> where A is either 0-255 integer or 0.0-1.0 float
        "rgb(R, G, B)"      -> opaque rgb

    Qt's ``QColor(str)`` ctor does not parse ``rgba(...)`` — we match the
    syntax the design-token JSON uses (see design/tokens/design-tokens.json)
    so chart widgets can pull grid/axis colors directly from tokens.
    """
    if not value:
        return QColor()
    if value.startswith("#"):
        return QColor(value)
    match = _RGBA_RE.match(value)
    if match:
        r, g, b = (int(match.group(i)) for i in (1, 2, 3))
        a_raw = match.group(4)
        if a_raw is None:
            alpha = 255
        else:
            a = float(a_raw)
            alpha = int(a * 255) if a <= 1.0 else int(a)
        return QColor(r, g, b, max(0, min(255, alpha)))
    # Fallback — let Qt try; it will likely yield an invalid color but
    # returning here keeps call-sites simple.
    return QColor(value)
