#!/usr/bin/env python3
"""Build script for the web marquee sub-apps.

Runs ``pnpm install`` (first run only, or when lockfile changes) and
``pnpm -C <app> build`` for each registered marquee. Idempotent — skips
apps whose ``dist/index.html`` is already newer than their ``src/``.

Usage::

    ./.venv/bin/python tools/build_web.py                # all apps
    ./.venv/bin/python tools/build_web.py tactical-viewer

Exit codes:
    0  All requested apps built (or already fresh) and have dist/index.html
    1  A ``pnpm`` invocation failed (surface stdout / stderr verbatim)
    2  pnpm not installed / not on PATH
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_WEB_ROOT = _PROJECT_ROOT / "Programma_CS2_RENAN" / "apps" / "qt_app" / "web"

REGISTERED_APPS = ("tactical-viewer", "match-detail", "coach-chat")


def _needs_rebuild(app_dir: Path) -> bool:
    dist_index = app_dir / "dist" / "index.html"
    if not dist_index.exists():
        return True
    dist_mtime = dist_index.stat().st_mtime
    src = app_dir / "src"
    if not src.is_dir():
        return False
    for p in src.rglob("*"):
        if p.is_file() and p.stat().st_mtime > dist_mtime:
            return True
    return False


def _pnpm_available() -> bool:
    return shutil.which("pnpm") is not None


def _ensure_install() -> int:
    """First-time ``pnpm install`` at the workspace root."""
    node_modules = _WEB_ROOT / "node_modules"
    if node_modules.is_dir():
        return 0
    print(f"[build_web] pnpm install (workspace {_WEB_ROOT})")
    return subprocess.call(["pnpm", "install"], cwd=str(_WEB_ROOT))


def _copy_maps_to_dist(app_name: str) -> None:
    """Copy radar PNGs into ``dist/maps/`` so the web app can ``<img>`` them
    with a relative URL. Only runs for apps that use map imagery —
    currently ``tactical-viewer``. Source of truth is ``PHOTO_GUI/maps``
    at the Python package root (same path the Qt-native viewer uses).
    """
    if app_name != "tactical-viewer":
        return
    src_maps = _PROJECT_ROOT / "Programma_CS2_RENAN" / "PHOTO_GUI" / "maps"
    dst_maps = _WEB_ROOT / app_name / "dist" / "maps"
    if not src_maps.is_dir():
        print(f"[build_web] warn: PHOTO_GUI/maps missing at {src_maps}")
        return
    dst_maps.mkdir(parents=True, exist_ok=True)
    copied = 0
    for png in src_maps.glob("*.png"):
        dest = dst_maps / png.name
        if not dest.exists() or dest.stat().st_mtime < png.stat().st_mtime:
            shutil.copy2(png, dest)
            copied += 1
    if copied:
        print(f"[build_web] copied {copied} map(s) into {dst_maps}")


def _build_one(app_name: str) -> int:
    app_dir = _WEB_ROOT / app_name
    if not app_dir.is_dir():
        print(f"[build_web] skip: {app_name} (no app dir at {app_dir})")
        return 0
    if not _needs_rebuild(app_dir):
        print(f"[build_web] fresh: {app_name}")
        _copy_maps_to_dist(app_name)
        return 0
    print(f"[build_web] building {app_name}")
    rc = subprocess.call(["pnpm", "build"], cwd=str(app_dir))
    if rc == 0:
        _copy_maps_to_dist(app_name)
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "apps",
        nargs="*",
        choices=list(REGISTERED_APPS) + [[]],
        help="Marquee apps to build. Defaults to all registered.",
    )
    args = parser.parse_args()

    if not _pnpm_available():
        print(
            "error: pnpm not found on PATH. Install Node 20+ and pnpm 9+ "
            "per the P4 plan pre-work section.",
            file=sys.stderr,
        )
        return 2

    if not _WEB_ROOT.is_dir():
        print(
            f"error: web workspace missing at {_WEB_ROOT}. " "Scaffold not initialized.",
            file=sys.stderr,
        )
        return 2

    targets = args.apps or list(REGISTERED_APPS)
    install_rc = _ensure_install()
    if install_rc != 0:
        print("[build_web] pnpm install failed", file=sys.stderr)
        return 1

    for app in targets:
        rc = _build_one(app)
        if rc != 0:
            print(f"[build_web] build failed for {app}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
