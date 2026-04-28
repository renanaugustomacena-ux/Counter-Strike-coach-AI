#!/usr/bin/env python3
"""Drift detector — compares current `Programma_CS2_RENAN/**` SHA-256 hashes
against a baseline manifest captured at release time.

Doctrine §63 — Infrastructure as Security Primitive (drift detection).
Maps to control C-DRIFT-01 (SECURITY/CONTROL_CATALOG.md).

Phase 1 status: skeleton only. The baseline file does not yet exist; this
script produces a baseline on demand. Phase 3 wires it into the installer
flow: the installer ships a signed baseline, app startup re-verifies, and
mismatches surface as a RASP integrity event.

Usage:
    python tools/drift_detector.py --baseline                   # write baseline
    python tools/drift_detector.py --verify                     # default — verify
    python tools/drift_detector.py --baseline-path <path>       # override

Exit codes:
    0 — clean (no drift) or baseline written successfully
    1 — drift detected
    2 — usage error / missing baseline in --verify mode
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO_ROOT / "Programma_CS2_RENAN"
DEFAULT_BASELINE = REPO_ROOT / "SECURITY" / "drift_baseline.json"

# Files / directories never tracked: caches, runtime artefacts, user data.
EXCLUDE_GLOBS = (
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    # Runtime / user data that legitimately changes
    "**/backend/storage/database.db*",
    "**/backend/storage/hltv_metadata.db*",
    "**/match_data/**",
    "**/demo_cache/**",
    "**/models/**/*.pt",  # checkpoints — tracked separately via integrity_manifest
    "**/runs/**",
    "**/logs/**",
    "**/user_settings.json",
    "**/secrets.vault",
    "**/.master_key.bin",
)


@dataclasses.dataclass(frozen=True)
class FileEntry:
    path: str  # repo-relative POSIX path
    size: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


def _matches_any(p: str, patterns: Iterable[str]) -> bool:
    import fnmatch

    return any(fnmatch.fnmatch(p, pat) for pat in patterns)


def _walk_tracked_files(target: pathlib.Path) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    target_str = target.as_posix()
    for root, dirs, files in _safe_walk(target):
        # Prune excluded dirs in-place
        kept_dirs = []
        for d in dirs:
            child = (root / d).as_posix()
            rel = child[len(target_str) + 1 :] if child.startswith(target_str + "/") else child
            if _matches_any(rel, EXCLUDE_GLOBS) or _matches_any(child, EXCLUDE_GLOBS):
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs
        for fn in files:
            full = root / fn
            child = full.as_posix()
            rel = child[len(target_str) + 1 :] if child.startswith(target_str + "/") else child
            if _matches_any(rel, EXCLUDE_GLOBS) or _matches_any(child, EXCLUDE_GLOBS):
                continue
            out.append(full)
    return out


def _safe_walk(root: pathlib.Path):
    import os

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        yield pathlib.Path(dirpath), dirnames, filenames


def _hash_file(path: pathlib.Path, chunk_size: int = 64 * 1024) -> tuple[int, str]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return size, h.hexdigest()


def build_manifest(target: pathlib.Path) -> dict[str, FileEntry]:
    files = _walk_tracked_files(target)
    manifest: dict[str, FileEntry] = {}
    for f in files:
        size, sha = _hash_file(f)
        rel = f.relative_to(REPO_ROOT).as_posix()
        manifest[rel] = FileEntry(path=rel, size=size, sha256=sha)
    return manifest


def write_baseline(manifest: dict[str, FileEntry], baseline_path: pathlib.Path) -> None:
    payload = {
        "version": 1,
        "target": str(DEFAULT_TARGET.relative_to(REPO_ROOT)),
        "files": {p: e.to_dict() for p, e in sorted(manifest.items())},
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_baseline(baseline_path: pathlib.Path) -> dict[str, FileEntry]:
    if not baseline_path.is_file():
        raise FileNotFoundError(f"baseline not found: {baseline_path}")
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    out: dict[str, FileEntry] = {}
    for path, entry in payload.get("files", {}).items():
        out[path] = FileEntry(path=entry["path"], size=int(entry["size"]), sha256=entry["sha256"])
    return out


@dataclasses.dataclass
class DriftReport:
    added: list[str]
    removed: list[str]
    modified: list[str]

    @property
    def is_clean(self) -> bool:
        return not (self.added or self.removed or self.modified)

    def render(self) -> str:
        lines = ["drift_detector report:"]
        lines.append(f"  added:    {len(self.added)}")
        lines.append(f"  removed:  {len(self.removed)}")
        lines.append(f"  modified: {len(self.modified)}")
        if self.added[:5]:
            lines.append("  added (first 5):")
            for p in self.added[:5]:
                lines.append(f"    + {p}")
        if self.removed[:5]:
            lines.append("  removed (first 5):")
            for p in self.removed[:5]:
                lines.append(f"    - {p}")
        if self.modified[:5]:
            lines.append("  modified (first 5):")
            for p in self.modified[:5]:
                lines.append(f"    ~ {p}")
        return "\n".join(lines)


def diff_manifest(baseline: dict[str, FileEntry], current: dict[str, FileEntry]) -> DriftReport:
    base_set = set(baseline)
    cur_set = set(current)
    added = sorted(cur_set - base_set)
    removed = sorted(base_set - cur_set)
    modified: list[str] = []
    for p in sorted(base_set & cur_set):
        if baseline[p].sha256 != current[p].sha256 or baseline[p].size != current[p].size:
            modified.append(p)
    return DriftReport(added=added, removed=removed, modified=modified)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Write a fresh baseline manifest instead of verifying.",
    )
    parser.add_argument(
        "--baseline-path",
        type=pathlib.Path,
        default=DEFAULT_BASELINE,
        help=f"Override baseline path (default: {DEFAULT_BASELINE}).",
    )
    parser.add_argument(
        "--target",
        type=pathlib.Path,
        default=DEFAULT_TARGET,
        help=f"Override target directory (default: {DEFAULT_TARGET}).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human report.")
    args = parser.parse_args(argv)

    if not args.target.is_dir():
        sys.stderr.write(f"drift_detector: target not found: {args.target}\n")
        return 2

    current = build_manifest(args.target)

    if args.baseline:
        write_baseline(current, args.baseline_path)
        sys.stdout.write(
            f"drift_detector: baseline written to {args.baseline_path}\n"
            f"  files tracked: {len(current)}\n"
        )
        return 0

    # Verify mode
    try:
        baseline = load_baseline(args.baseline_path)
    except FileNotFoundError as exc:
        sys.stderr.write(f"drift_detector: {exc}\nRun with --baseline to create one.\n")
        return 2

    report = diff_manifest(baseline, current)

    if args.json:
        json.dump(
            {
                "baseline": str(args.baseline_path),
                "target": str(args.target),
                "is_clean": report.is_clean,
                "added": report.added,
                "removed": report.removed,
                "modified": report.modified,
                "counts": {
                    "added": len(report.added),
                    "removed": len(report.removed),
                    "modified": len(report.modified),
                    "baseline_files": len(baseline),
                    "current_files": len(current),
                },
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        sys.stdout.write(report.render() + "\n")
        if report.is_clean:
            sys.stdout.write("\n✓ no drift detected.\n")
        else:
            sys.stdout.write(
                "\n✗ drift detected. See SECURITY/INCIDENT_RESPONSE.md IR-02 / IR-05.\n"
            )

    return 0 if report.is_clean else 1


if __name__ == "__main__":
    sys.exit(main())
