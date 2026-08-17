"""F-0041 regression: build_tools' three internal drifts stay dead.

(a) argv lists, no shell=True; (b) verify reads the {"binaries":[...]}
manifest the writer emits; (c) --verify-only reads "hashes";
(e) the spec target EXISTS (packaging/cs2_analyzer_win.spec)."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("rich", reason="build_tools requires rich (tools-only dep)")

REPO_ROOT = Path(__file__).resolve().parents[2]
_PTOOLS = REPO_ROOT / "Programma_CS2_RENAN" / "tools"
if str(_PTOOLS) not in sys.path:
    sys.path.insert(0, str(_PTOOLS))


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_tools_under_test", _PTOOLS / "build_tools.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_shell_true_anywhere():
    tree = ast.parse((_PTOOLS / "build_tools.py").read_text(encoding="utf-8"))
    offenders = [
        kw.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "shell" and getattr(kw.value, "value", False) is True
    ]
    assert offenders == [], f"shell=True is back at lines {offenders}"


def test_spec_target_exists():
    assert (REPO_ROOT / "packaging" / "cs2_analyzer_win.spec").exists()
    src = (_PTOOLS / "build_tools.py").read_text(encoding="utf-8")
    assert "macena.spec" not in src, "phantom spec reference is back"
    assert "cs2_analyzer_win.spec" in src


def test_verify_accepts_writer_schema(tmp_path, capsys):
    mod = _load()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "build_manifest.json").write_text(
        '{"binaries": [{"file": "a.exe", "sha256": "ab", "built_at": "t"}]}'
    )
    mod.PROJECT_ROOT = tmp_path
    with pytest.raises(SystemExit) as exc:
        mod.cmd_verify(None)
    assert exc.value.code == 0, "verify must pass on the writer's own schema"


def test_manifest_verify_only_reads_hashes(tmp_path, capsys):
    mod = _load()
    core = tmp_path / "core"
    core.mkdir()
    (core / "integrity_manifest.json").write_text('{"hashes": {"a.py": "x", "b.py": "y"}}')
    mod.SOURCE_ROOT = tmp_path

    class _A:
        verify_only = True

    with pytest.raises(SystemExit) as exc:
        mod.cmd_manifest(_A())
    assert exc.value.code == 0
    assert "2 files" in capsys.readouterr().out, "hashes key not read"
