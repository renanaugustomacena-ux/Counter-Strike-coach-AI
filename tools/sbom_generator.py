#!/usr/bin/env python3
"""Generate a CycloneDX 1.6 SBOM for the project.

Doctrine §53 — Software Supply Chain Is the Core Asset.
Maps to control C-SC-06 (SECURITY/CONTROL_CATALOG.md).

Phase 1 status: standalone tool. Phase 2 wires it into `goliath.py sbom` as a
subcommand and into the CI workflow as a release-time step.

Two modes:
  1. `--from-env`     scan the active Python environment (preferred; covers
                      transitive deps as actually installed)
  2. `--from-lockfile <path>`  parse a hashed lockfile (declarative; reproducible
                      from the lockfile alone)

Both rely on `cyclonedx-bom` (the Python lib), which is added to
requirements-dev.in. If not installed, the script falls back to a minimal-but-
valid CycloneDX JSON emitter that reads from `pip list` / requirements.

Output: CycloneDX 1.6 JSON to stdout (or `--output <path>`).

Usage:
    python tools/sbom_generator.py --from-env                       # current env
    python tools/sbom_generator.py --from-lockfile requirements-lock-cpu.txt
    python tools/sbom_generator.py --from-env --output sbom.cdx.json

Verification:
    pip-audit --strict --vulnerability-service osv -r requirements-lock-cpu.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata as md
import json
import pathlib
import re
import subprocess
import sys
import uuid
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_NAME = "macena-cs2-analyzer"
PROJECT_VERSION = "1.0.0"  # synced from pyproject.toml in Phase 2

# Match `name==version` (with optional extras / markers) in a requirements lock file.
LOCK_LINE = re.compile(r"^(?P<name>[A-Za-z0-9._\-\[\],]+)==(?P<version>[^\s;]+)")


def _try_cyclonedx_lib() -> bool:
    try:
        from cyclonedx.builder.this import this_component  # noqa: F401

        return True
    except ImportError:
        return False


def _components_from_env() -> list[dict[str, Any]]:
    """Enumerate installed dists via importlib.metadata."""
    components: list[dict[str, Any]] = []
    for dist in md.distributions():
        name = dist.metadata.get("Name") or dist.metadata.get("name") or "unknown"
        version = dist.metadata.get("Version") or dist.version or "0"
        homepage = dist.metadata.get("Home-page") or ""
        license_ = dist.metadata.get("License") or ""
        purl = f"pkg:pypi/{name.lower()}@{version}"
        comp = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": purl,
            "bom-ref": purl,
            "scope": "required",
        }
        if license_:
            comp["licenses"] = [{"license": {"name": license_}}]
        if homepage:
            comp["externalReferences"] = [{"type": "website", "url": homepage}]
        components.append(comp)
    return components


def _components_from_lockfile(path: pathlib.Path) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    if not path.is_file():
        raise SystemExit(f"sbom_generator: lockfile not found: {path}")
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-") or line.startswith("--"):
            continue
        m = LOCK_LINE.match(line)
        if not m:
            continue
        name = m.group("name")
        version = m.group("version")
        purl = f"pkg:pypi/{name.lower()}@{version}"
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": purl,
                "bom-ref": purl,
                "scope": "required",
            }
        )
    return components


def _project_metadata() -> dict[str, Any]:
    pyproject = REPO_ROOT / "pyproject.toml"
    name = PROJECT_NAME
    version = PROJECT_VERSION
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        m_name = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.MULTILINE)
        m_ver = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m_name:
            name = m_name.group(1)
        if m_ver:
            version = m_ver.group(1)
    return {"name": name, "version": version}


def _git_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def build_sbom(components: list[dict[str, Any]], source_label: str) -> dict[str, Any]:
    project = _project_metadata()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    serial = f"urn:uuid:{uuid.uuid4()}"
    project_purl = f"pkg:generic/{project['name']}@{project['version']}"
    git_sha = _git_commit()

    sbom: dict[str, Any] = {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": serial,
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "tools/sbom_generator.py",
                        "version": "0.1.0-phase1",
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": project["name"],
                "version": project["version"],
                "purl": project_purl,
                "bom-ref": project_purl,
            },
            "properties": [
                {"name": "macena:source", "value": source_label},
            ],
        },
        "components": components,
    }
    if git_sha:
        sbom["metadata"]["properties"].append({"name": "macena:git-commit", "value": git_sha})
    return sbom


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument(
        "--from-env",
        action="store_true",
        help="Scan the active Python environment (default if no source given).",
    )
    src.add_argument("--from-lockfile", type=pathlib.Path, help="Parse a hashed lockfile.")
    parser.add_argument("--output", type=pathlib.Path, help="Write to file instead of stdout.")
    args = parser.parse_args(argv)

    if args.from_lockfile:
        components = _components_from_lockfile(args.from_lockfile)
        source_label = f"lockfile:{args.from_lockfile.relative_to(REPO_ROOT) if args.from_lockfile.is_relative_to(REPO_ROOT) else args.from_lockfile}"
    else:
        # Default: from current env
        components = _components_from_env()
        source_label = f"env:{sys.executable}"

    sbom = build_sbom(components, source_label)
    text = json.dumps(sbom, indent=2, sort_keys=True)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        sys.stderr.write(f"sbom_generator: wrote {len(components)} components to {args.output}\n")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
