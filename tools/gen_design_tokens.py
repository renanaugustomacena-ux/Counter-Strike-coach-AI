#!/usr/bin/env python3
"""Design Token Codegen — JSON (source of truth) -> Python dataclass.

Reads ``design/tokens/design-tokens.json`` and emits
``Programma_CS2_RENAN/apps/qt_app/core/design_tokens.py``. Output is
byte-identical on unchanged input so a pre-commit hook and the
headless validator can diff the regeneration against the on-disk file.

Modes:
    default   Regenerate design_tokens.py on disk.
    --check   Regenerate in memory, compare against the on-disk file.
              Exit 1 if the two differ. Used by tools/headless_validator.
    --stdout  Print the generated source to stdout without touching
              the on-disk file.

Field mapping: each Python dataclass field maps to a dotted path inside
the theme object (for per-theme values) or to a top-level group (for
shared scale fields: spacing / radius / typography). The mapping is
explicit — no auto-derivation — so a key rename in JSON is a conscious
change that updates the generator too.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_JSON_PATH = _PROJECT_ROOT / "design" / "tokens" / "design-tokens.json"
_PY_PATH = _PROJECT_ROOT / "Programma_CS2_RENAN" / "apps" / "qt_app" / "core" / "design_tokens.py"
_TS_PATH = (
    _PROJECT_ROOT / "Programma_CS2_RENAN" / "apps" / "qt_app" / "web" / "shared" / "tokens.ts"
)

# ─────────────────────────────────────────────────────────────────────
# Field-to-path mapping
# ─────────────────────────────────────────────────────────────────────

# Per-theme fields: python_field_name -> [path inside theme.<name>]
THEME_FIELDS: list[tuple[str, list[str], str]] = [
    # (python_field, json_path, python_type_hint)
    ("theme_name", ["name"], "str"),
    ("surface_base", ["surface", "base"], "str"),
    ("surface_raised", ["surface", "raised"], "str"),
    ("surface_overlay", ["surface", "overlay"], "str"),
    ("surface_sunken", ["surface", "sunken"], "str"),
    ("surface_sidebar", ["surface", "sidebar"], "str"),
    ("surface_raised_rgba", ["surface", "raised_rgba"], "str"),
    ("surface_card_hover_border", ["surface", "card_hover_border"], "str"),
    ("border_subtle", ["border", "subtle"], "str"),
    ("border_default", ["border", "default"], "str"),
    ("border_accent_muted", ["border", "accent_muted"], "str"),
    ("text_primary", ["text", "primary"], "str"),
    ("text_secondary", ["text", "secondary"], "str"),
    ("text_tertiary", ["text", "tertiary"], "str"),
    ("text_inverse", ["text", "inverse"], "str"),
    ("text_disabled", ["text", "disabled"], "str"),
    ("accent_primary", ["accent", "primary"], "str"),
    ("accent_hover", ["accent", "hover"], "str"),
    ("accent_pressed", ["accent", "pressed"], "str"),
    ("accent_muted_15", ["accent", "muted_15"], "str"),
    ("accent_muted_25", ["accent", "muted_25"], "str"),
    ("accent_muted_30", ["accent", "muted_30"], "str"),
    ("success", ["semantic", "success"], "str"),
    ("warning", ["semantic", "warning"], "str"),
    ("error", ["semantic", "error"], "str"),
    ("info", ["semantic", "info"], "str"),
    ("toast_info_bg", ["toast", "info_bg"], "str"),
    ("toast_info_border", ["toast", "info_border"], "str"),
    ("toast_warning_bg", ["toast", "warning_bg"], "str"),
    ("toast_warning_border", ["toast", "warning_border"], "str"),
    ("toast_error_bg", ["toast", "error_bg"], "str"),
    ("toast_error_border", ["toast", "error_border"], "str"),
    ("toast_critical_bg", ["toast", "critical_bg"], "str"),
    ("toast_critical_border", ["toast", "critical_border"], "str"),
    ("toast_dismiss", ["toast", "dismiss"], "str"),
    ("chart_bg", ["chart", "bg"], "str"),
    ("chart_grid", ["chart", "grid"], "str"),
    ("chart_axis", ["chart", "axis"], "str"),
    ("chart_line_primary", ["chart", "line_primary"], "str"),
    ("chart_line_secondary", ["chart", "line_secondary"], "str"),
    ("chart_fill_positive", ["chart", "fill_positive"], "str"),
    ("chart_fill_negative", ["chart", "fill_negative"], "str"),
]

# Globals (shared across themes): python_field -> JSON top-level path
GLOBAL_FIELDS: list[tuple[str, list[str], str]] = [
    ("spacing_xs", ["spacing", "xs"], "int"),
    ("spacing_sm", ["spacing", "sm"], "int"),
    ("spacing_md", ["spacing", "md"], "int"),
    ("spacing_lg", ["spacing", "lg"], "int"),
    ("spacing_xl", ["spacing", "xl"], "int"),
    ("spacing_xxl", ["spacing", "xxl"], "int"),
    ("spacing_xxxl", ["spacing", "xxxl"], "int"),
    ("font_size_caption", ["typography", "size", "caption"], "int"),
    ("font_size_body", ["typography", "size", "body"], "int"),
    ("font_size_subtitle", ["typography", "size", "subtitle"], "int"),
    ("font_size_title", ["typography", "size", "title"], "int"),
    ("font_size_h1", ["typography", "size", "h1"], "int"),
    ("font_size_stat", ["typography", "size", "stat"], "int"),
    ("radius_sm", ["radius", "sm"], "int"),
    ("radius_md", ["radius", "md"], "int"),
    ("radius_lg", ["radius", "lg"], "int"),
    ("radius_xl", ["radius", "xl"], "int"),
]

# Theme key in JSON -> (python constant name, display name)
THEME_REGISTRY: list[tuple[str, str, str]] = [
    ("cs2", "CS2_TOKENS", "CS2"),
    ("csgo", "CSGO_TOKENS", "CSGO"),
    ("cs16", "CS16_TOKENS", "CS1.6"),
]

# Python field -> inline comment appended to the dataclass definition.
FIELD_COMMENTS: dict[str, str] = {
    "theme_name": "",
    "surface_base": "  # QMainWindow background (deepest)",
    "surface_raised": "  # Cards, panels (1 layer up)",
    "surface_overlay": "  # Tooltips, dropdowns (2 layers up)",
    "surface_sunken": "  # Inputs, wells (1 layer down)",
    "surface_sidebar": "  # Navigation sidebar",
    "surface_raised_rgba": "  # Card bg with alpha channel",
    "surface_card_hover_border": "  # Card hover border",
    "border_subtle": "  # rgba(255,255,255,0.05)",
    "border_default": "  # Scrollbar handles, input borders",
    "border_accent_muted": "  # Accent at 30% alpha",
    "text_primary": "  # Headings, important content",
    "text_secondary": "  # Descriptions, labels",
    "text_tertiary": "  # Metadata, timestamps, placeholders",
    "text_inverse": "  # On accent backgrounds",
    "text_disabled": "  # Disabled controls",
    "accent_primary": "  # Main accent color",
    "accent_hover": "  # Lighter accent for hover",
    "accent_pressed": "  # Darker accent for press",
    "accent_muted_15": "  # 15% alpha for nav hover bg",
    "accent_muted_25": "  # 25% alpha for nav active bg",
    "accent_muted_30": "  # 30% alpha for card hover border",
    "success": "  # Green",
    "warning": "  # Yellow/Orange",
    "error": "  # Red",
    "info": "  # Blue",
    "chart_grid": "  # Grid lines (low-alpha white)",
    "chart_axis": "  # Axis lines",
    "chart_line_primary": "  # Primary data series",
    "chart_line_secondary": "  # Secondary data series",
    "chart_fill_positive": "  # Positive area fill",
    "chart_fill_negative": "  # Negative area fill",
}

# Section header printed above each run of related fields in the dataclass
SECTION_HEADERS: list[tuple[int, str]] = [
    (1, "Theme identity"),  # before theme_name
    (2, "Surfaces (4-layer depth system)"),  # before surface_base
    (7, "Surfaces with alpha (for QSS rgba() usage)"),  # before surface_raised_rgba
    (9, "Borders"),  # before border_subtle
    (12, "Text hierarchy (5 levels)"),  # before text_primary
    (17, "Accent (theme-specific)"),  # before accent_primary
    (23, "Semantic"),  # before success
    (27, "Toast notification backgrounds"),  # before toast_info_bg
    (36, "Chart palette"),  # before chart_bg
]

GLOBAL_SECTIONS: list[tuple[int, str]] = [
    (0, "Spacing scale (4px grid)"),  # before spacing_xs
    (7, "Typography scale"),  # before font_size_caption
    (13, "Border radius"),  # before radius_sm
]


def _get_value(container: dict, path: list[str]) -> Any:
    cur: Any = container
    for key in path:
        if not isinstance(cur, dict):
            raise KeyError(f"expected dict at {path}, found {type(cur).__name__}")
        if key not in cur:
            raise KeyError(f"missing key {key!r} in path {path}")
        cur = cur[key]
    # DTCG leaf may be either a raw scalar or a {"$value": ..., "$type": ...} dict
    if isinstance(cur, dict) and "$value" in cur:
        return cur["$value"]
    return cur


def _render_python(tokens_json: dict) -> str:
    lines: list[str] = []
    lines.append('"""')
    lines.append("Design Token System — single source of truth for every visual constant.")
    lines.append("")
    lines.append("GENERATED BY tools/gen_design_tokens.py FROM design/tokens/design-tokens.json.")
    lines.append("Do not edit this file by hand — edit the JSON and re-run the generator.")
    lines.append("")
    lines.append("Three frozen dataclass instances (CS2, CSGO, CS1.6) provide theme-specific")
    lines.append("values while sharing the same structural contract.")
    lines.append('"""')
    lines.append("")
    lines.append("from dataclasses import dataclass")
    lines.append("")
    lines.append("")
    lines.append("@dataclass(frozen=True)")
    lines.append("class DesignTokens:")
    lines.append('    """Immutable visual token set for a single theme."""')
    lines.append("")

    def _emit_section(header: str) -> None:
        lines.append(f"    # ── {header} ──")

    # Theme-scoped fields
    section_by_idx = dict(SECTION_HEADERS)
    for idx, (field, _path, type_hint) in enumerate(THEME_FIELDS):
        if idx in section_by_idx:
            if idx > 0:
                lines.append("")
            _emit_section(section_by_idx[idx])
        comment = FIELD_COMMENTS.get(field, "")
        lines.append(f"    {field}: {type_hint}{comment}")

    # Scale fields with defaults
    global_section_by_idx = dict(GLOBAL_SECTIONS)
    scale_values = {}
    for field, path, _type in GLOBAL_FIELDS:
        scale_values[field] = _get_value(tokens_json, path)

    for idx, (field, _path, type_hint) in enumerate(GLOBAL_FIELDS):
        if idx in global_section_by_idx:
            lines.append("")
            _emit_section(global_section_by_idx[idx])
        default = scale_values[field]
        lines.append(f"    {field}: {type_hint} = {default}")

    lines.append("")
    lines.append("")
    lines.append("# " + "═" * 75)
    lines.append("# Pre-built theme instances")
    lines.append("# " + "═" * 75)
    lines.append("")

    # Emit each theme dataclass instance
    themes_obj = tokens_json.get("theme", {})
    for theme_idx, (theme_key, constant_name, _display) in enumerate(THEME_REGISTRY):
        if theme_idx > 0:
            lines.append("")
        theme_obj = themes_obj.get(theme_key)
        if theme_obj is None:
            raise KeyError(f"theme {theme_key!r} missing in JSON")
        lines.append(f"{constant_name} = DesignTokens(")
        section_by_idx_inst = dict(SECTION_HEADERS)
        for idx, (field, path, _type) in enumerate(THEME_FIELDS):
            if idx in section_by_idx_inst:
                lines.append(f"    # {section_by_idx_inst[idx]}")
            value = _get_value(theme_obj, path)
            lines.append(f'    {field}="{value}",')
        lines.append(")")

    lines.append("")
    lines.append("_THEME_TOKENS = {")
    for _, constant_name, display_name in THEME_REGISTRY:
        lines.append(f'    "{display_name}": {constant_name},')
    lines.append("}")
    lines.append("")
    lines.append("# Module-level active theme reference (updated by ThemeEngine)")
    lines.append('_active_theme: str = "CS2"')
    lines.append("")
    lines.append("")
    lines.append("def get_tokens(theme_name: str | None = None) -> DesignTokens:")
    lines.append('    """Return the DesignTokens for a theme. Defaults to the active theme."""')
    lines.append("    name = theme_name or _active_theme")
    lines.append("    return _THEME_TOKENS.get(name, CS2_TOKENS)")
    lines.append("")
    lines.append("")
    lines.append("def set_active_theme(name: str) -> None:")
    lines.append(
        '    """Update the module-level active theme. Called by ThemeEngine.apply_theme()."""'
    )
    lines.append("    global _active_theme")
    lines.append("    if name in _THEME_TOKENS:")
    lines.append("        _active_theme = name")
    lines.append("")
    return "\n".join(lines)


def _render_typescript(tokens_json: dict) -> str:
    """Render a TypeScript module mirroring the Python DesignTokens shape.

    Emits:
        export interface DesignTokens { ... }
        export const CS2_TOKENS: DesignTokens = { ... }
        export const CSGO_TOKENS: DesignTokens = { ... }
        export const CS16_TOKENS: DesignTokens = { ... }
        export const TOKENS_BY_NAME: Record<'CS2' | 'CSGO' | 'CS1.6', DesignTokens>
        export function getTokens(name?: string): DesignTokens;

    The interface order follows THEME_FIELDS + GLOBAL_FIELDS. Values for
    globals are constant across themes (spacing / radius / typography),
    but each theme instance includes them to match the Python dataclass
    so the TS surface is symmetric.
    """
    themes_obj = tokens_json.get("theme", {})
    global_values: dict[str, Any] = {}
    for field, path, _type in GLOBAL_FIELDS:
        global_values[field] = _get_value(tokens_json, path)

    lines: list[str] = []
    lines.append("/**")
    lines.append(" * Design tokens — GENERATED from design/tokens/design-tokens.json")
    lines.append(" * by tools/gen_design_tokens.py --web.")
    lines.append(" * Do NOT edit by hand; edit the JSON and re-run the generator.")
    lines.append(" */")
    lines.append("")
    # Interface
    lines.append("export interface DesignTokens {")
    for field, _path, type_hint in THEME_FIELDS:
        ts_type = "string" if type_hint == "str" else "number"
        lines.append(f"  {field}: {ts_type};")
    lines.append("")
    for field, _path, type_hint in GLOBAL_FIELDS:
        ts_type = "string" if type_hint == "str" else "number"
        lines.append(f"  {field}: {ts_type};")
    lines.append("}")
    lines.append("")

    # Each theme constant
    for theme_key, constant_name, _display in THEME_REGISTRY:
        theme_obj = themes_obj.get(theme_key)
        if theme_obj is None:
            raise KeyError(f"theme {theme_key!r} missing in JSON")
        lines.append(f"export const {constant_name}: DesignTokens = {{")
        for field, path, type_hint in THEME_FIELDS:
            value = _get_value(theme_obj, path)
            if type_hint == "str":
                lines.append(f'  {field}: "{value}",')
            else:
                lines.append(f"  {field}: {value},")
        for field, _path, type_hint in GLOBAL_FIELDS:
            value = global_values[field]
            if type_hint == "str":
                lines.append(f'  {field}: "{value}",')
            else:
                lines.append(f"  {field}: {value},")
        lines.append("};")
        lines.append("")

    # Lookup table + getter
    lines.append("export const TOKENS_BY_NAME: Record<string, DesignTokens> = {")
    for _, constant_name, display_name in THEME_REGISTRY:
        lines.append(f'  "{display_name}": {constant_name},')
    lines.append("};")
    lines.append("")
    lines.append("export function getTokens(name?: string): DesignTokens {")
    lines.append('  return TOKENS_BY_NAME[name ?? "CS2"] ?? CS2_TOKENS;')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _load_json() -> dict:
    with open(_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate in memory, compare to on-disk file. Exit 1 if stale.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print generated source to stdout without writing to disk.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help=(
            "Emit the TypeScript mirror at web/shared/tokens.ts "
            "instead of the Python dataclass. Combines with --check / --stdout."
        ),
    )
    args = parser.parse_args()

    try:
        tokens = _load_json()
    except FileNotFoundError:
        print(f"error: JSON source not found at {_JSON_PATH}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: JSON is not valid: {exc}", file=sys.stderr)
        return 2

    try:
        if args.web:
            rendered = _render_typescript(tokens)
            out_path = _TS_PATH
        else:
            rendered = _render_python(tokens)
            out_path = _PY_PATH
    except KeyError as exc:
        print(f"error: JSON is missing a token — {exc}", file=sys.stderr)
        return 2

    if args.stdout:
        sys.stdout.write(rendered)
        return 0

    if args.check:
        if not out_path.exists():
            print(
                f"error: {out_path} does not exist — run without --check first",
                file=sys.stderr,
            )
            return 1
        on_disk = out_path.read_text(encoding="utf-8")
        if on_disk == rendered:
            return 0
        print(
            f"error: {out_path.name} is stale. Run:\n"
            f"    ./.venv/bin/python {Path(__file__).relative_to(_PROJECT_ROOT)}"
            f"{' --web' if args.web else ''}",
            file=sys.stderr,
        )
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"wrote {out_path.relative_to(_PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
