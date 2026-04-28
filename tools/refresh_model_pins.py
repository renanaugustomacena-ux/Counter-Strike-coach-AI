#!/usr/bin/env python3
"""Refresh HuggingFace model revision pins in core/integrity_manifest.json.

Doctrine §53 — Software Supply Chain Is the Core Asset.
Maps to control C-MOD-01 (SECURITY/CONTROL_CATALOG.md).

For each remote-fetched model used by the app (today: SBERT for the RAG knowledge
base), records:
  - the model identifier (e.g., `sentence-transformers/all-MiniLM-L6-v2`)
  - the pinned revision (a 40-char commit SHA on HuggingFace Hub)
  - SHA-256 of every artifact file the loader uses (model.safetensors,
    config.json, tokenizer.json, tokenizer_config.json, special_tokens_map.json)

The app reads these values at first-run and refuses to load a model whose
artifact hashes do not match.

Phase 1 status:
  - Scaffold. The actual integrity manifest format and rag_knowledge.py
    integration land in Phase 2.
  - This script depends on `huggingface_hub` (already a transitive of
    `sentence-transformers==3.4.1`).

Usage:
    python tools/refresh_model_pins.py                                    # show current pins
    python tools/refresh_model_pins.py --model <id> --revision <sha>      # refresh one
    python tools/refresh_model_pins.py --check                            # exit 1 if any pin missing

Exit codes:
    0 — success / clean
    1 — pin missing or hash mismatch (--check)
    2 — usage error / network failure / model not found
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "Programma_CS2_RENAN" / "core" / "integrity_manifest.json"

# The artifact files we expect for an SBERT model. Phase 2 may extend this.
SBERT_ARTIFACTS = (
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
)

# Default model registry for this project — referenced from rag_knowledge.py.
DEFAULT_MODELS = {
    "sentence-transformers/all-MiniLM-L6-v2": {
        "purpose": "RAG knowledge base embeddings (SBERT)",
        "artifacts": SBERT_ARTIFACTS,
    },
}


def _hf_hub_available() -> bool:
    try:
        import huggingface_hub  # noqa: F401

        return True
    except ImportError:
        return False


def _download_and_hash(model_id: str, revision: str, artifacts: Iterable[str]) -> dict[str, str]:
    """Download each artifact and return {filename: sha256}."""
    from huggingface_hub import hf_hub_download  # type: ignore[import-not-found]

    out: dict[str, str] = {}
    for fname in artifacts:
        try:
            local_path = hf_hub_download(
                repo_id=model_id,
                filename=fname,
                revision=revision,
            )
        except Exception as exc:  # noqa: BLE001 — surface upstream errors clearly
            sys.stderr.write(
                f"refresh_model_pins: failed to fetch {fname} for {model_id}@{revision}: {exc}\n"
            )
            continue
        h = hashlib.sha256()
        with open(local_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(64 * 1024), b""):
                h.update(chunk)
        out[fname] = h.hexdigest()
    return out


def _load_manifest(path: pathlib.Path) -> dict[str, object]:
    if not path.is_file():
        return {"version": 1, "models": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(path: pathlib.Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--model", help="Model ID to refresh (e.g., sentence-transformers/all-MiniLM-L6-v2)."
    )
    parser.add_argument("--revision", help="40-char revision SHA on HuggingFace Hub.")
    parser.add_argument(
        "--check", action="store_true", help="Exit 1 if any default model lacks a pin."
    )
    parser.add_argument("--show", action="store_true", help="Print current pins from the manifest.")
    args = parser.parse_args(argv)

    manifest = _load_manifest(args.manifest)
    models_block = manifest.setdefault("models", {})

    if args.show or (not args.model and not args.check):
        print(f"Manifest path: {args.manifest}")
        print("Default models:")
        for model_id, meta in DEFAULT_MODELS.items():
            entry = models_block.get(model_id, {})
            rev = entry.get("revision", "(unpinned)")
            arts = entry.get("artifacts", {})
            print(f"  {model_id}")
            print(f"    purpose:  {meta['purpose']}")
            print(f"    revision: {rev}")
            print(f"    artifact hashes: {len(arts)}")
        return 0

    if args.check:
        missing: list[str] = []
        for model_id in DEFAULT_MODELS:
            entry = models_block.get(model_id)
            if not entry or not entry.get("revision"):
                missing.append(model_id)
        if missing:
            sys.stderr.write("refresh_model_pins --check: missing pins:\n")
            for m in missing:
                sys.stderr.write(f"  - {m}\n")
            sys.stderr.write("Run with --model <id> --revision <sha> to refresh.\n")
            return 1
        print("✓ all default models have pinned revisions.")
        return 0

    # Refresh path
    if not args.model or not args.revision:
        sys.stderr.write(
            "refresh_model_pins: --model and --revision are both required to refresh.\n"
        )
        return 2

    if len(args.revision) != 40 or not all(c in "0123456789abcdef" for c in args.revision):
        sys.stderr.write("refresh_model_pins: --revision must be a 40-char lowercase hex SHA.\n")
        return 2

    if not _hf_hub_available():
        sys.stderr.write(
            "refresh_model_pins: huggingface_hub not installed. "
            "Install via `pip install huggingface_hub` and retry.\n"
        )
        return 2

    artifacts = DEFAULT_MODELS.get(args.model, {}).get("artifacts", SBERT_ARTIFACTS)
    print(f"Refreshing pins for {args.model}@{args.revision}")
    hashes = _download_and_hash(args.model, args.revision, artifacts)
    if len(hashes) < len(artifacts):
        sys.stderr.write(
            f"refresh_model_pins: only {len(hashes)}/{len(artifacts)} artifacts hashed; "
            "incomplete pin not saved.\n"
        )
        return 2

    models_block[args.model] = {
        "revision": args.revision,
        "purpose": DEFAULT_MODELS.get(args.model, {}).get("purpose", "(unspecified)"),
        "artifacts": hashes,
    }
    _save_manifest(args.manifest, manifest)
    print(f"✓ wrote pin for {args.model}@{args.revision} to {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
