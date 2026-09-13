"""D-38 (D-28 class) — every text write in the neural-core tools names its encoding.

``tools/benchmark_jepa_v2_vs_legacy.py`` wrote its markdown report with
``Path.write_text(report)``; the report carries ``Δpos R²`` and Windows'
default codec is cp1252, so the benchmark crashed with UnicodeEncodeError
on every Windows run (the two red tests on main since afdd699).  D-28
already fixed the same class in verify_lock_hashes.  This AST sweep pins
the rule for the whole neural-core v2 tool family: ``Path.write_text``,
``open(..., "w"/"a")`` and ``Path.open("w")`` must pass ``encoding=``.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCAN = (
    _REPO_ROOT / "tools" / "benchmark_jepa_v2_vs_legacy.py",
    _REPO_ROOT / "tools" / "export_episodes.py",
    _REPO_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "episode_export.py",
    _REPO_ROOT / "tools" / "measure_episode_lengths.py",
    _REPO_ROOT / "tools" / "measure_event_horizons.py",
    _REPO_ROOT / "tools" / "measure_name_join_coverage.py",
    _REPO_ROOT / "tools" / "measure_sigreg_sample_size.py",
    _REPO_ROOT / "tools" / "verify_math_claims.py",
    *sorted((_REPO_ROOT / "Programma_CS2_RENAN" / "backend" / "nn" / "jepa_v2").glob("*.py")),
)
_WRITE_MODES = {"w", "a", "w+", "a+", "wt", "at"}


def _is_text_write_without_encoding(node: ast.Call) -> bool:
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name == "write_text":
        return not any(k.arg == "encoding" for k in node.keywords)
    if name == "open":
        mode = None
        # builtin open(path, mode) / Path.open(mode)
        pos = node.args[1:] if not isinstance(func, ast.Attribute) else node.args[:1]
        if pos and isinstance(pos[0], ast.Constant) and isinstance(pos[0].value, str):
            mode = pos[0].value
        for k in node.keywords:
            if k.arg == "mode" and isinstance(k.value, ast.Constant):
                mode = k.value.value
        if mode in _WRITE_MODES and "b" not in mode:
            return not any(k.arg == "encoding" for k in node.keywords)
    return False


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        f"{path.relative_to(_REPO_ROOT)}:{node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_text_write_without_encoding(node)
    ]


def test_neural_core_text_writes_name_their_encoding():
    hits = [v for p in _SCAN if p.exists() for v in _violations(p)]
    assert hits == [], "text writes without encoding= (cp1252 trap, D-28 class):\n" + "\n".join(
        hits
    )


def test_sweep_sees_the_tools():
    assert all(p.exists() for p in _SCAN[:7]), [str(p) for p in _SCAN[:7] if not p.exists()]
