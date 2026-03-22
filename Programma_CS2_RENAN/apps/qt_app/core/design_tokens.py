"""
Design Token System — single source of truth for every visual constant.

All colors, spacing, typography, and border-radius values are defined here.
Screens and widgets read from get_tokens() instead of hardcoding hex values.

Three frozen dataclass instances (CS2, CSGO, CS1.6) provide theme-specific
values while sharing the same structural contract.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignTokens:
    """Immutable visual token set for a single theme."""

    # ── Theme identity ──
    theme_name: str

    # ── Surfaces (4-layer depth system) ──
    surface_base: str  # QMainWindow background (deepest)
    surface_raised: str  # Cards, panels (1 layer up)
    surface_overlay: str  # Tooltips, dropdowns (2 layers up)
    surface_sunken: str  # Inputs, wells (1 layer down)
    surface_sidebar: str  # Navigation sidebar

    # ── Surfaces with alpha (for QSS rgba() usage) ──
    surface_raised_rgba: str  # Card bg with alpha channel
    surface_card_hover_border: str  # Card hover border

    # ── Borders ──
    border_subtle: str  # rgba(255,255,255,0.05)
    border_default: str  # Scrollbar handles, input borders
    border_accent_muted: str  # Accent at 30% alpha

    # ── Text hierarchy (5 levels) ──
    text_primary: str  # Headings, important content
    text_secondary: str  # Descriptions, labels
    text_tertiary: str  # Metadata, timestamps, placeholders
    text_inverse: str  # On accent backgrounds
    text_disabled: str  # Disabled controls

    # ── Accent (theme-specific) ──
    accent_primary: str  # Main accent color
    accent_hover: str  # Lighter accent for hover
    accent_pressed: str  # Darker accent for press
    accent_muted_15: str  # 15% alpha for nav hover bg
    accent_muted_25: str  # 25% alpha for nav active bg
    accent_muted_30: str  # 30% alpha for card hover border

    # ── Semantic ──
    success: str  # Green
    warning: str  # Yellow/Orange
    error: str  # Red
    info: str  # Blue

    # ── Toast notification backgrounds ──
    toast_info_bg: str
    toast_info_border: str
    toast_warning_bg: str
    toast_warning_border: str
    toast_error_bg: str
    toast_error_border: str
    toast_critical_bg: str
    toast_critical_border: str
    toast_dismiss: str

    # ── Chart palette ──
    chart_bg: str
    chart_grid: str  # Grid lines (low-alpha white)
    chart_axis: str  # Axis lines
    chart_line_primary: str  # Primary data series
    chart_line_secondary: str  # Secondary data series
    chart_fill_positive: str  # Positive area fill
    chart_fill_negative: str  # Negative area fill

    # ── Spacing scale (4px grid) ──
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 16
    spacing_xl: int = 24
    spacing_xxl: int = 32
    spacing_xxxl: int = 48

    # ── Typography scale ──
    font_size_caption: int = 11
    font_size_body: int = 13
    font_size_subtitle: int = 14
    font_size_title: int = 18
    font_size_h1: int = 24
    font_size_stat: int = 28

    # ── Border radius ──
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 16
    radius_xl: int = 24


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-built theme instances
# ═══════════════════════════════════════════════════════════════════════════════

CS2_TOKENS = DesignTokens(
    theme_name="CS2",
    # Surfaces
    surface_base="#14141e",
    surface_raised="#1a1a2e",
    surface_overlay="#1a1a2e",
    surface_sunken="#0f0f2e",
    surface_sidebar="#0f0f2e",
    surface_raised_rgba="rgba(20, 20, 30, 217)",
    surface_card_hover_border="rgba(217, 102, 0, 0.3)",
    # Borders
    border_subtle="rgba(255, 255, 255, 0.05)",
    border_default="#3a3a5a",
    border_accent_muted="rgba(217, 102, 0, 0.3)",
    # Text
    text_primary="#dcdcdc",
    text_secondary="#a0a0b0",
    text_tertiary="#3a3a5a",
    text_inverse="#ffffff",
    text_disabled="#666666",
    # Accent
    accent_primary="#d96600",
    accent_hover="#e67a1a",
    accent_pressed="#b85500",
    accent_muted_15="rgba(217, 102, 0, 0.15)",
    accent_muted_25="rgba(217, 102, 0, 0.25)",
    accent_muted_30="rgba(217, 102, 0, 0.3)",
    # Semantic
    success="#4caf50",
    warning="#ffaa00",
    error="#ff4444",
    info="#4a9eff",
    # Toasts
    toast_info_bg="rgba(30, 60, 90, 230)",
    toast_info_border="#4a9eff",
    toast_warning_bg="rgba(80, 60, 10, 230)",
    toast_warning_border="#ffaa00",
    toast_error_bg="rgba(80, 20, 20, 230)",
    toast_error_border="#ff4444",
    toast_critical_bg="rgba(100, 10, 10, 240)",
    toast_critical_border="#ff0000",
    toast_dismiss="#888888",
    # Charts
    chart_bg="#1a1a1a",
    chart_grid="rgba(255, 255, 255, 40)",
    chart_axis="rgba(255, 255, 255, 25)",
    chart_line_primary="#00ccff",
    chart_line_secondary="#ffaa00",
    chart_fill_positive="#4caf50",
    chart_fill_negative="#ff4444",
)

CSGO_TOKENS = DesignTokens(
    theme_name="CSGO",
    # Surfaces
    surface_base="#1a1c21",
    surface_raised="#1c1e24",
    surface_overlay="#1c1e24",
    surface_sunken="#141a24",
    surface_sidebar="#141a24",
    surface_raised_rgba="rgba(26, 28, 33, 217)",
    surface_card_hover_border="rgba(97, 125, 140, 0.3)",
    # Borders
    border_subtle="rgba(255, 255, 255, 0.05)",
    border_default="#3a3e48",
    border_accent_muted="rgba(97, 125, 140, 0.3)",
    # Text
    text_primary="#dcdcdc",
    text_secondary="#a0a8b0",
    text_tertiary="#3a3e48",
    text_inverse="#ffffff",
    text_disabled="#666666",
    # Accent
    accent_primary="#617d8c",
    accent_hover="#7a96a5",
    accent_pressed="#4e6a78",
    accent_muted_15="rgba(97, 125, 140, 0.15)",
    accent_muted_25="rgba(97, 125, 140, 0.25)",
    accent_muted_30="rgba(97, 125, 140, 0.3)",
    # Semantic
    success="#4caf50",
    warning="#c8a030",
    error="#cc4444",
    info="#617d8c",
    # Toasts
    toast_info_bg="rgba(26, 40, 60, 230)",
    toast_info_border="#617d8c",
    toast_warning_bg="rgba(60, 50, 20, 230)",
    toast_warning_border="#c8a030",
    toast_error_bg="rgba(70, 20, 20, 230)",
    toast_error_border="#cc4444",
    toast_critical_bg="rgba(90, 10, 10, 240)",
    toast_critical_border="#ee0000",
    toast_dismiss="#666666",
    # Charts
    chart_bg="#1c1e20",
    chart_grid="rgba(255, 255, 255, 40)",
    chart_axis="rgba(255, 255, 255, 25)",
    chart_line_primary="#00ccff",
    chart_line_secondary="#c8a030",
    chart_fill_positive="#4caf50",
    chart_fill_negative="#cc4444",
)

CS16_TOKENS = DesignTokens(
    theme_name="CS1.6",
    # Surfaces
    surface_base="#121a12",
    surface_raised="#182418",
    surface_overlay="#182418",
    surface_sunken="#0d2414",
    surface_sidebar="#0d2414",
    surface_raised_rgba="rgba(18, 26, 18, 217)",
    surface_card_hover_border="rgba(77, 176, 79, 0.3)",
    # Borders
    border_subtle="rgba(255, 255, 255, 0.05)",
    border_default="#2a3e2a",
    border_accent_muted="rgba(77, 176, 79, 0.3)",
    # Text
    text_primary="#dcdcdc",
    text_secondary="#80a080",
    text_tertiary="#2a3e2a",
    text_inverse="#ffffff",
    text_disabled="#555555",
    # Accent
    accent_primary="#4db04f",
    accent_hover="#66c268",
    accent_pressed="#3d9040",
    accent_muted_15="rgba(77, 176, 79, 0.15)",
    accent_muted_25="rgba(77, 176, 79, 0.25)",
    accent_muted_30="rgba(77, 176, 79, 0.3)",
    # Semantic
    success="#4db04f",
    warning="#b8a030",
    error="#cc3333",
    info="#4db04f",
    # Toasts
    toast_info_bg="rgba(18, 36, 28, 230)",
    toast_info_border="#4db04f",
    toast_warning_bg="rgba(50, 45, 15, 230)",
    toast_warning_border="#b8a030",
    toast_error_bg="rgba(60, 18, 18, 230)",
    toast_error_border="#cc3333",
    toast_critical_bg="rgba(80, 10, 10, 240)",
    toast_critical_border="#dd0000",
    toast_dismiss="#5a7a5a",
    # Charts
    chart_bg="#181e18",
    chart_grid="rgba(255, 255, 255, 40)",
    chart_axis="rgba(255, 255, 255, 25)",
    chart_line_primary="#00ccff",
    chart_line_secondary="#b8a030",
    chart_fill_positive="#4db04f",
    chart_fill_negative="#cc3333",
)

_THEME_TOKENS = {
    "CS2": CS2_TOKENS,
    "CSGO": CSGO_TOKENS,
    "CS1.6": CS16_TOKENS,
}

# Module-level active theme reference (updated by ThemeEngine)
_active_theme: str = "CS2"


def get_tokens(theme_name: str | None = None) -> DesignTokens:
    """Return the DesignTokens for a theme. Defaults to the active theme."""
    name = theme_name or _active_theme
    return _THEME_TOKENS.get(name, CS2_TOKENS)


def set_active_theme(name: str) -> None:
    """Update the module-level active theme. Called by ThemeEngine.apply_theme()."""
    global _active_theme
    if name in _THEME_TOKENS:
        _active_theme = name
