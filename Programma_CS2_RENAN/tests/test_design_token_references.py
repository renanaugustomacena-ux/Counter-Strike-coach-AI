"""Design-token reference contract (R4 HIGH fix, 2026-07-16).

``pro_player_detail_screen`` referenced ``tokens.surface_card`` — a field
that has never existed on the frozen DesignTokens dataclass — so the
Recent Matches panel raised AttributeError whenever matches were present.
This test statically scans every qt_app Python source for ``tokens.<name>``
references and pins them to real DesignTokens fields, killing the whole
class of runtime-only token typos.
"""

import dataclasses
import re
from pathlib import Path

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import DesignTokens

_QT_APP_DIR = Path(__file__).resolve().parents[1] / "apps" / "qt_app"
_TOKEN_REF_RE = re.compile(r"\btokens\.([a-z_][a-z0-9_]*)")
# "tokens.json" is the sibling data FILE referenced in path strings,
# not an attribute access on the DesignTokens dataclass.
_FALSE_POSITIVES = {"json"}


def test_every_token_reference_exists():
    fields = {f.name for f in dataclasses.fields(DesignTokens)}
    unknown: list[str] = []
    for py_file in _QT_APP_DIR.rglob("*.py"):
        if "web" in py_file.parts:
            continue
        src = py_file.read_text(encoding="utf-8", errors="replace")
        for name in set(_TOKEN_REF_RE.findall(src)) - _FALSE_POSITIVES:
            if name not in fields:
                unknown.append(f"{py_file.name}: tokens.{name}")
    assert not unknown, (
        "References to nonexistent DesignTokens fields (AttributeError at "
        f"runtime): {sorted(unknown)}"
    )


def test_scanner_sees_qt_app_sources():
    """Guard the guard: the scan must actually cover the screens."""
    scanned = list(_QT_APP_DIR.rglob("*.py"))
    assert any("pro_player_detail_screen" in p.name for p in scanned)
