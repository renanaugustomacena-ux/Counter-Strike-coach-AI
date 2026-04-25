#!/usr/bin/env python3
"""Verify every requirements-lock*.txt line is exact-pinned + hashed.

Doctrine §53 — Software Supply Chain Is the Core Asset.
Maps to control C-SC-03 (SECURITY/CONTROL_CATALOG.md) and policy POL-DEPS-01.

The check:
  1. For every `requirements-lock*.txt` (and `requirements-ci*.txt` when used as a lock)
     under the repo root:
       - Each non-comment, non-blank, non-directive line must be of shape
         `<name>==<version>` (exact pin), optionally followed by a marker.
       - Each such line must be paired with at least one `--hash=sha256:<64hex>` continuation
         line (lines starting with whitespace + `--hash=`).
       - Permitted directives: `-r`, `-c`, `--index-url`, `--extra-index-url`, `--find-links`.
  2. Reports each violation with file:line.
  3. Exit 0 if all clean; exit 1 if any violation; exit 2 on usage error.

Phase 1 status:
  - The actual hashed lockfiles do not yet exist (will be generated post-ingestion via
    `uv pip compile --generate-hashes`).
  - Today this script scans whatever requirements-lock*.txt files are present and reports
    which ones lack hashes. In Phase 2 it becomes a CI gate.

Usage:
  python tools/verify_lock_hashes.py                # default: scan repo root for lock files
  python tools/verify_lock_hashes.py path/to/lock.txt [...]    # explicit files
  python tools/verify_lock_hashes.py --json         # machine-readable output
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys
from typing import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

DEFAULT_GLOBS = (
    "requirements-lock.txt",
    "requirements-lock-cpu.txt",
    "requirements-lock-cuda*.txt",
    "requirements-dev-lock.txt",
    "requirements-rap-lock.txt",
)

# Permitted directive prefixes (pip will accept these in a requirements file).
DIRECTIVES = ("-r ", "-c ", "--index-url", "--extra-index-url", "--find-links")

# Anchor: a line that begins a requirement entry. Greedy match for name==version
# possibly followed by extras and environment markers.
PIN_LINE = re.compile(
    r"^[A-Za-z0-9._\-\[\],]+\s*"  # name + optional [extras]
    r"==\s*\S+"  # exact version
    r"(\s*;.*)?$"  # optional environment marker
)

HASH_CONT = re.compile(r"^\s+--hash=sha256:[0-9a-f]{64}\s*\\?\s*$")


@dataclasses.dataclass
class Finding:
    file: str
    line: int
    rule: str
    message: str
    snippet: str = ""

    def render(self) -> str:
        loc = f"{self.file}:{self.line}"
        out = f"  [{self.rule}] {loc}  — {self.message}"
        if self.snippet:
            out += f"\n         {self.snippet.rstrip()[:160]}"
        return out


def _is_blank_or_comment(line: str) -> bool:
    s = line.strip()
    return not s or s.startswith("#")


def _is_directive(line: str) -> bool:
    s = line.lstrip()
    return any(s.startswith(d) for d in DIRECTIVES)


def _is_continuation(line: str) -> bool:
    """Non-blank line that begins with whitespace (a hash or marker continuation)."""
    return bool(line) and line[0] in (" ", "\t") and bool(line.strip())


def verify_one_file(path: pathlib.Path) -> list[Finding]:
    findings: list[Finding] = []
    if not path.is_file():
        return [Finding(str(path), 0, "MISSING", "Lockfile does not exist")]

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    rel = path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else str(path)

    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_blank_or_comment(line):
            i += 1
            continue
        if _is_directive(line):
            i += 1
            continue
        # Strip a trailing backslash continuation marker for the regex check.
        check = line.rstrip()
        if check.endswith("\\"):
            check = check[:-1].rstrip()
        if not PIN_LINE.match(check):
            findings.append(
                Finding(
                    file=rel,
                    line=i + 1,
                    rule="UNPINNED",
                    message="Line is not a `<name>==<version>` exact pin (or directive).",
                    snippet=line,
                )
            )
            i += 1
            continue

        # Found a pin line — look ahead for at least one --hash= continuation.
        j = i + 1
        hash_count = 0
        while j < len(lines) and _is_continuation(lines[j]):
            if HASH_CONT.match(lines[j]):
                hash_count += 1
            j += 1
        if hash_count == 0:
            findings.append(
                Finding(
                    file=rel,
                    line=i + 1,
                    rule="MISSING_HASH",
                    message="Pin lacks any `--hash=sha256:` continuation line.",
                    snippet=line,
                )
            )
        i = j

    return findings


def discover_lockfiles(roots: Iterable[pathlib.Path]) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for r in roots:
        if r.is_file():
            out.append(r)
            continue
        if r.is_dir():
            for glob in DEFAULT_GLOBS:
                out.extend(sorted(r.glob(glob)))
    seen: set[pathlib.Path] = set()
    deduped: list[pathlib.Path] = []
    for p in out:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        deduped.append(p)
    return deduped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=pathlib.Path,
        help="Lockfile paths or directories. If omitted, scan the repo root.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human report.")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Do not error if no lockfiles are found (Phase 1: locks not yet generated).",
    )
    args = parser.parse_args(argv)

    roots = args.paths or [REPO_ROOT]
    files = discover_lockfiles(roots)

    if not files:
        if args.allow_empty:
            if args.json:
                json.dump(
                    {"files_scanned": [], "findings": [], "ok": True, "note": "no lockfiles found"},
                    sys.stdout,
                )
                sys.stdout.write("\n")
            else:
                sys.stdout.write("verify_lock_hashes: no lockfiles found (--allow-empty).\n")
            return 0
        sys.stderr.write(
            "verify_lock_hashes: no lockfiles matched.\n"
            f"  searched roots: {[str(r) for r in roots]}\n"
            f"  default globs:  {DEFAULT_GLOBS}\n"
            "Use --allow-empty during Phase 1 (before locks are generated).\n"
        )
        return 2

    all_findings: list[Finding] = []
    for f in files:
        all_findings.extend(verify_one_file(f))

    ok = not all_findings
    if args.json:
        json.dump(
            {
                "files_scanned": [str(f) for f in files],
                "findings": [dataclasses.asdict(x) for x in all_findings],
                "ok": ok,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        sys.stdout.write("verify_lock_hashes — POL-DEPS-01 / C-SC-03\n")
        for f in files:
            sys.stdout.write(f"  scanned: {f}\n")
        sys.stdout.write(f"\nfindings: {len(all_findings)}\n")
        for v in all_findings:
            sys.stdout.write(v.render() + "\n")
        if ok:
            sys.stdout.write("\n✓ All scanned lockfiles are exact-pinned and hashed.\n")
        else:
            sys.stdout.write(
                "\n✗ At least one lockfile is missing exact-pin or hash. "
                "Regenerate with `uv pip compile --generate-hashes`.\n"
            )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
