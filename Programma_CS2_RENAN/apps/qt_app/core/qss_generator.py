"""
QSS Template Renderer — generates theme-specific Qt stylesheets from a single template.

Replaces three duplicate QSS files (cs2.qss, csgo.qss, cs16.qss) with one
base.qss.template where every color is a $token_name variable substituted
at runtime from the active DesignTokens instance.
"""

from dataclasses import asdict
from pathlib import Path
from string import Template

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import DesignTokens

_TEMPLATE_PATH = Path(__file__).parent.parent / "themes" / "base.qss.template"

# Cache: theme_name → rendered QSS string
_cache: dict[str, str] = {}


def render_qss(tokens: DesignTokens) -> str:
    """Render the QSS template with token values substituted.

    Returns the complete stylesheet string ready for QApplication.setStyleSheet().
    Results are cached per theme_name to avoid re-rendering on every call.
    """
    if tokens.theme_name in _cache:
        return _cache[tokens.theme_name]

    template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = Template(template_text).safe_substitute(asdict(tokens))
    _cache[tokens.theme_name] = rendered
    return rendered


def invalidate_cache(theme_name: str | None = None) -> None:
    """Clear cached QSS. Call when tokens or template change at runtime."""
    if theme_name:
        _cache.pop(theme_name, None)
    else:
        _cache.clear()
