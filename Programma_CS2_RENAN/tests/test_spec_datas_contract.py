"""Install round (WP4a) — the PyInstaller spec and get_resource_path agree.

Every ``datas`` entry lands under ``Programma_CS2_RENAN/<rel>`` inside the
bundle, so a frozen ``get_resource_path(rel)`` must resolve to exactly that
place.  Otherwise help docs, i18n, themes, fonts and map zones ship but are
never found (the D-32 class of failure).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = PROJECT_ROOT / "packaging" / "cs2_analyzer_win.spec"
APP_DIR = PROJECT_ROOT / "Programma_CS2_RENAN"

_ENTRY = re.compile(r'\(\s*str\((APP_DIR|PROJECT_ROOT)((?:\s*/\s*"[^"]+")+)\)\s*,\s*"([^"]+)"\s*\)')


def _entries() -> list[tuple[str, tuple[str, ...], str]]:
    text = SPEC.read_text(encoding="utf-8")
    body = text.split("datas = [", 1)[1].split("\n]", 1)[0]
    out = []
    for base, parts, dest in _ENTRY.findall(body):
        out.append((base, tuple(re.findall(r'"([^"]+)"', parts)), dest))
    return out


def _ident(value) -> str:
    return "/".join(value) if isinstance(value, tuple) else str(value)


def test_the_spec_parser_sees_the_real_entries():
    rels = {"/".join(rel) for _, rel, _ in _entries()}
    expected = {
        "PHOTO_GUI",
        "data/docs",
        "assets/i18n",
        "apps/qt_app/themes",
        "assets/fonts",
        "assets/map_zones",
        "core/integrity_manifest.json",
    }
    assert expected <= rels, sorted(expected - rels)


@pytest.mark.parametrize("base,rel,dest", _entries(), ids=_ident)
def test_every_bundled_entry_lands_where_get_resource_path_looks(
    base, rel, dest, monkeypatch, tmp_path
):
    if base == "PROJECT_ROOT":
        # Root-level entries (alembic, the design sprite) are resolved from
        # _MEIPASS itself, so they land at their own repo-relative path.
        src = PROJECT_ROOT.joinpath(*rel)
        src_is_dir = src.is_dir() if src.exists() else not Path(rel[-1]).suffix
        expected = "/".join(rel if src_is_dir else rel[:-1]) or "."
        assert dest == expected, (rel, dest)
        return

    src = APP_DIR.joinpath(*rel)
    src_is_dir = src.is_dir() if src.exists() else not Path(rel[-1]).suffix
    expected_dest = "/".join(("Programma_CS2_RENAN", *(rel if src_is_dir else rel[:-1])))
    assert dest == expected_dest

    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "IS_FROZEN", True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    resolved = Path(config.get_resource_path(os.path.join(*rel)))
    bundled = tmp_path.joinpath(*dest.split("/"))
    if not src_is_dir:
        bundled = bundled / rel[-1]
    assert resolved == bundled
