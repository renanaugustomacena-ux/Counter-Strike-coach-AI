"""26-NORM-01 / C11 — tick-rate SSOT contract (owner decision 2026-07-17).

Two guarantees:
1. ``core.tick_rate`` resolves per-demo rates honestly (metadata → header →
   None sentinel, never a fabricated default, out-of-range rejected).
2. NO other production module spells a bare tick-rate literal 64 — every
   fallback must import ``DEFAULT_TICK_RATE`` from the SSOT so the audit
   trail is a single grep. AST-based (immune to comments and docstrings),
   same systemic-contract spirit as test_design_token_references.
"""

from __future__ import annotations

import ast
from pathlib import Path

from Programma_CS2_RENAN.core.tick_rate import (
    DEFAULT_TICK_RATE,
    is_valid_tick_rate,
    resolve_tick_rate,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAN_ROOTS = (
    _REPO_ROOT / "Programma_CS2_RENAN",
    _REPO_ROOT / "tools",
)
_SSOT_FILE = _REPO_ROOT / "Programma_CS2_RENAN" / "core" / "tick_rate.py"


class TestResolveTickRate:
    def test_metadata_wins_over_header(self):
        assert resolve_tick_rate(128.0, 64.0) == 128.0

    def test_header_fallback_when_metadata_missing(self):
        assert resolve_tick_rate(None, 128.0) == 128.0

    def test_out_of_range_metadata_falls_through_to_header(self):
        assert resolve_tick_rate(1000.0, 64.0) == 64.0

    def test_none_sentinel_when_nothing_valid(self):
        assert resolve_tick_rate(None, None) is None
        assert resolve_tick_rate("garbage", 9999) is None

    def test_validity_window(self):
        assert is_valid_tick_rate(32.0) and is_valid_tick_rate(256.0)
        assert not is_valid_tick_rate(31.9)
        assert not is_valid_tick_rate(256.1)
        assert not is_valid_tick_rate(None)
        assert not is_valid_tick_rate("not-a-number")

    def test_default_is_sixty_four(self):
        # The one sanctioned literal — if this ever changes, every importer
        # follows automatically; that is the point of the SSOT.
        assert DEFAULT_TICK_RATE == 64


def _is_64(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value in (64, 64.0)


def _is_ticky(name: str | None) -> bool:
    return bool(name) and "tick_rate" in name.lower()


def _violations_in(tree: ast.AST) -> list[int]:
    """Line numbers of bare 64 literals bound to tick-rate-ish names."""
    hits: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            names += [t.attr for t in node.targets if isinstance(t, ast.Attribute)]
            if any(_is_ticky(n) or n.upper() == "TICK_RATE" for n in names) and _is_64(node.value):
                hits.append(node.lineno)

        elif isinstance(node, ast.AnnAssign):
            target = node.target
            name = (
                target.id
                if isinstance(target, ast.Name)
                else target.attr if isinstance(target, ast.Attribute) else ""
            )
            if _is_ticky(name) and node.value is not None:
                if _is_64(node.value):
                    hits.append(node.lineno)
                elif isinstance(node.value, ast.Call):  # Field(default=64.0)
                    for kw in node.value.keywords:
                        if kw.arg == "default" and _is_64(kw.value):
                            hits.append(node.lineno)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            positional = args.posonlyargs + args.args
            for arg, default in zip(
                positional[len(positional) - len(args.defaults) :], args.defaults
            ):
                if _is_ticky(arg.arg) and default is not None and _is_64(default):
                    hits.append(default.lineno)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults):
                if _is_ticky(arg.arg) and default is not None and _is_64(default):
                    hits.append(default.lineno)

        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if _is_ticky(kw.arg) and _is_64(kw.value):
                    hits.append(kw.value.lineno)
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) == 3
                and isinstance(node.args[1], ast.Constant)
                and _is_ticky(str(node.args[1].value))
                and _is_64(node.args[2])
            ):
                hits.append(node.lineno)

        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and _is_ticky(str(key.value))
                    and value is not None
                    and _is_64(value)
                ):
                    hits.append(key.lineno)

    return hits


class TestNoBareTickRateLiterals:
    def test_production_code_has_no_bare_64(self):
        offenders: list[str] = []
        for root in _SCAN_ROOTS:
            for path in sorted(root.rglob("*.py")):
                parts = path.parts
                if "__pycache__" in parts or "tests" in parts:
                    continue
                if path == _SSOT_FILE:
                    continue
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeDecodeError):
                    continue  # the AST compile-gate owns syntax policing
                for line in _violations_in(tree):
                    offenders.append(f"{path.relative_to(_REPO_ROOT)}:{line}")
        assert not offenders, (
            "Bare tick-rate literal 64 outside the SSOT (26-NORM-01) — import "
            "DEFAULT_TICK_RATE from Programma_CS2_RENAN.core.tick_rate instead:\n  "
            + "\n  ".join(offenders)
        )

    def test_scanner_catches_a_seeded_violation(self):
        """The ban must actually bite: a synthetic offender IS detected."""
        tree = ast.parse(
            "def f(tick_rate: int = 64):\n"
            "    x = {'tick_rate': 64.0}\n"
            "    y = getattr(obj, 'tick_rate', 64)\n"
            "    TICK_RATE = 64\n"
        )
        assert len(_violations_in(tree)) == 4
