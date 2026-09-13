"""Write packaging/version.iss from pyproject.toml (WP4c, P10-02).

The Inno Setup script ``#include``s ``version.iss`` for its ``AppVersion``, so
the installer version can never drift from ``[project].version``.  The build
script runs this before ISCC; the committed copy is refreshed with it.

Usage::

    python tools/gen_version_iss.py [--pyproject PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def read_version(pyproject: Path) -> str:
    with open(pyproject, "rb") as fh:
        data = tomllib.load(fh)
    try:
        return str(data["project"]["version"])
    except KeyError as exc:
        raise SystemExit(f"{pyproject}: no [project].version") from exc


def write_version_iss(version: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'#define AppVersion "{version}"\n', encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate packaging/version.iss from pyproject")
    parser.add_argument("--pyproject", default=str(REPO / "pyproject.toml"))
    parser.add_argument("--out", default=str(REPO / "packaging" / "version.iss"))
    args = parser.parse_args(argv)

    version = read_version(Path(args.pyproject))
    out = Path(args.out)
    write_version_iss(version, out)
    print(f"{out}: AppVersion {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
