#!/usr/bin/env python3
"""Refresh image digest pins in docker-compose.yml.

Doctrine §53 — Software Supply Chain Is the Core Asset.
Maps to control C-DOCK-01 (SECURITY/CONTROL_CATALOG.md).

For each `image:` directive in docker-compose.yml, resolve the current digest
of the referenced tag via `docker manifest inspect` (or `skopeo inspect` if
available) and rewrite the line to use `image: <repo>@sha256:<digest>` form.

Phase 1 status:
  - Scaffold only. Today's docker-compose.yml uses `ghcr.io/flaresolverr/flaresolverr:v3.4.6`
    (tag pin). Phase 2 flips to digest pin via this script.
  - This script does not require the Docker daemon to be running; it only needs
    `docker manifest inspect` (or `skopeo`) to query the registry.

Usage:
    python tools/refresh_compose_digests.py --dry-run     # default: print changes
    python tools/refresh_compose_digests.py --apply       # write changes back
    python tools/refresh_compose_digests.py --check       # exit 1 if any tag pin remains

The script also reports a summary suitable for a weekly Dependabot-equivalent
PR opened against `docker-compose.yml`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Optional

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"

# Match `image: <ref>` in YAML. Permissive on whitespace; captures the ref.
IMAGE_LINE_RE = re.compile(r"^(\s*image:\s*)(\S+)\s*$")
# A digest reference looks like `<repo>@sha256:<64hex>`
DIGEST_RE = re.compile(r"^(?P<repo>[^@\s]+)@sha256:[0-9a-f]{64}$")
# A tag reference looks like `<repo>:<tag>` (no slash in tag, no @ in ref)
TAG_RE = re.compile(r"^(?P<repo>[^:@\s]+(?::\d+)?(?:/[^:@\s]+)*):(?P<tag>[^:@\s/]+)$")


def _find_tool() -> Optional[str]:
    for cand in ("docker", "skopeo"):
        if shutil.which(cand):
            return cand
    return None


def _resolve_digest(ref: str, tool: str) -> Optional[str]:
    """Query the registry for the manifest digest of <repo>:<tag>."""
    if tool == "docker":
        # `docker manifest inspect <ref>` returns a JSON; the digest is in
        # `manifests[0].digest` for multi-arch, or top-level `config.digest`
        # for single-arch. We want the top-level "digest" of the manifest the
        # registry returned for HEAD; experimental but widely supported.
        try:
            proc = subprocess.run(
                ["docker", "manifest", "inspect", "--verbose", ref],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None
        # Multi-arch index is a list with a top-level "Descriptor"
        if isinstance(data, list):
            # Take the descriptor.digest of the first entry (linux/amd64 typically).
            for entry in data:
                desc = entry.get("Descriptor", {})
                d = desc.get("digest")
                if d and d.startswith("sha256:"):
                    return d
        elif isinstance(data, dict):
            d = data.get("Descriptor", {}).get("digest")
            if d and d.startswith("sha256:"):
                return d
        return None

    if tool == "skopeo":
        try:
            proc = subprocess.run(
                ["skopeo", "inspect", f"docker://{ref}"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None
        d = data.get("Digest")
        if d and d.startswith("sha256:"):
            return d
        return None

    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--compose", type=pathlib.Path, default=DEFAULT_COMPOSE)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print proposed changes without writing (default).",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Write the resolved digest pins back to the compose file.",
    )
    group.add_argument(
        "--check", action="store_true", help="Exit 1 if any image: line is still a tag pin."
    )
    args = parser.parse_args(argv)

    if not args.compose.is_file():
        sys.stderr.write(f"refresh_compose_digests: file not found: {args.compose}\n")
        return 2

    text = args.compose.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    findings: list[tuple[int, str, str]] = []  # (lineno, before, after_or_reason)

    if args.check:
        for i, line in enumerate(lines, start=1):
            m = IMAGE_LINE_RE.match(line.rstrip("\n"))
            if not m:
                continue
            ref = m.group(2)
            if DIGEST_RE.match(ref):
                continue
            findings.append((i, ref, "tag pin (digest required)"))
        if findings:
            sys.stdout.write("refresh_compose_digests --check: tag pins remain:\n")
            for lineno, ref, reason in findings:
                sys.stdout.write(f"  {args.compose}:{lineno}  {ref}  ({reason})\n")
            return 1
        sys.stdout.write("refresh_compose_digests --check: ✓ all images digest-pinned.\n")
        return 0

    tool = _find_tool()
    if tool is None:
        sys.stderr.write(
            "refresh_compose_digests: neither `docker` nor `skopeo` is on PATH; "
            "cannot resolve digests. Install one and retry.\n"
        )
        return 2

    new_lines: list[str] = []
    changed = False
    for i, line in enumerate(lines, start=1):
        m = IMAGE_LINE_RE.match(line.rstrip("\n"))
        if not m:
            new_lines.append(line)
            continue
        prefix = m.group(1)
        ref = m.group(2)
        if DIGEST_RE.match(ref):
            new_lines.append(line)
            continue  # already digest-pinned
        tag_match = TAG_RE.match(ref)
        if not tag_match:
            findings.append((i, ref, "unrecognised reference shape (skipped)"))
            new_lines.append(line)
            continue

        repo = tag_match.group("repo")
        tag = tag_match.group("tag")
        full_tagged = f"{repo}:{tag}"
        digest = _resolve_digest(full_tagged, tool)
        if not digest:
            findings.append((i, ref, "could not resolve digest (network? registry auth?)"))
            new_lines.append(line)
            continue

        new_ref = f"{repo}@{digest}"
        comment = f"   # was: {repo}:{tag}\n"
        new_line = f"{prefix}{new_ref}\n"
        # Insert a sibling comment line above for traceability if not already present
        # (best-effort; YAML allows blank comments freely).
        new_lines.append(comment)
        new_lines.append(new_line)
        findings.append((i, ref, new_ref))
        changed = True

    sys.stdout.write(f"refresh_compose_digests using `{tool}`\n")
    for lineno, before, after in findings:
        sys.stdout.write(
            f"  {args.compose}:{lineno}\n     before: {before}\n     after:  {after}\n"
        )

    if args.apply:
        if not changed:
            sys.stdout.write("\n✓ no changes needed.\n")
            return 0
        args.compose.write_text("".join(new_lines), encoding="utf-8")
        sys.stdout.write(f"\n✓ wrote {args.compose}\n")
        return 0

    sys.stdout.write("\n(dry-run; pass --apply to write changes)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
