#!/usr/bin/env python3
"""Atheris coverage-guided fuzzer for demoparser2.

Doctrine §64 — Testability and Continuous Verification.
Maps to control C-SBX-02 (SECURITY/CONTROL_CATALOG.md).

The fuzzer feeds bytes (with a high probability of `PBDEMS2\\x00` magic prefix)
to `demoparser2.DemoParser(...)` and tracks coverage. Crashes, hangs, and
out-of-memory events are written to the crash directory.

Usage:
    python tools/fuzz/fuzz_demo_parser.py                    # default 30 min
    python tools/fuzz/fuzz_demo_parser.py --time-budget 600  # 10 min
    python tools/fuzz/fuzz_demo_parser.py --reproduce <path> # replay one crash input

Phase 1 status:
- Scaffold only. The actual `atheris.Setup` invocation is gated on `atheris`
  being importable; the harness gracefully degrades to a deterministic
  random-input loop if Atheris is missing (e.g., when developers run this
  locally without installing the dev requirements).
- Phase 2 enables Atheris in CI and adds the corpus seeding step.

Reproducibility:
- Deterministic seed (default 42) so the same bytes → same coverage path.
- Crash inputs are written to `<crash_dir>/<sha256>-<size>.dem` for stable IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import pathlib
import random
import signal
import sys
import time
from typing import Any

DEMO_MAGIC_V2 = b"PBDEMS2\x00"
DEFAULT_TIME_BUDGET = 1800  # seconds (30 min)


def _atheris_available() -> bool:
    try:
        import atheris  # noqa: F401

        return True
    except ImportError:
        return False


def _demoparser2_available() -> bool:
    try:
        import demoparser2  # noqa: F401

        return True
    except ImportError:
        return False


def _hash_input(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _save_crash(data: bytes, crash_dir: pathlib.Path, exception: BaseException) -> pathlib.Path:
    crash_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{_hash_input(data)}-{len(data)}.dem"
    target = crash_dir / fname
    target.write_bytes(data)
    meta = crash_dir / f"{fname}.meta"
    meta.write_text(
        f"exception_type: {type(exception).__name__}\n"
        f"exception_msg:  {str(exception)[:1000]}\n"
        f"size_bytes:     {len(data)}\n"
        f"sha256_full:    {hashlib.sha256(data).hexdigest()}\n",
        encoding="utf-8",
    )
    return target


def _try_parse(data: bytes) -> None:
    """Attempt to invoke demoparser2 on the given bytes."""
    # demoparser2's API requires a file path. Write to a tempfile.
    import tempfile

    import demoparser2

    with tempfile.NamedTemporaryFile(suffix=".dem", delete=True) as tf:
        tf.write(data)
        tf.flush()
        # The constructor itself can raise; that's the surface we fuzz.
        parser = demoparser2.DemoParser(tf.name)
        # Try a minimal exercise of the parser.
        try:
            _ = parser.parse_event("round_start")
        except Exception:
            # round_start absence is normal for malformed/short demos.
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Random-input fallback (used when Atheris is not installed)
# ──────────────────────────────────────────────────────────────────────────────


def _generate_input(rng: random.Random, magic_prob: float = 0.7) -> bytes:
    """Produce a randomly-shaped input with high probability of the magic header."""
    size = rng.randint(8, 64 * 1024)  # up to 64 KiB
    body = bytes(rng.getrandbits(8) for _ in range(size))
    if rng.random() < magic_prob:
        body = DEMO_MAGIC_V2 + body[len(DEMO_MAGIC_V2) :]
    return body


def _run_random_fallback(args: argparse.Namespace, log: logging.Logger) -> int:
    rng = random.Random(args.seed)
    crash_dir = pathlib.Path(args.crash_dir)
    deadline = time.monotonic() + float(args.time_budget)

    n_runs = 0
    n_crashes = 0
    last_status = time.monotonic()
    while time.monotonic() < deadline:
        data = _generate_input(rng)
        try:
            _try_parse(data)
        except (Exception, BaseException) as exc:  # noqa: BLE001 — fuzz target
            # demoparser2 is expected to raise on malformed input; we treat any
            # exception as "interesting" only when it's outside the known-error
            # surface. Without a clear surface, count and save all of them; the
            # operator triages.
            crash_path = _save_crash(data, crash_dir, exc)
            log.info("crash[%d]: %s -> %s", n_crashes, type(exc).__name__, crash_path)
            n_crashes += 1
        n_runs += 1
        if time.monotonic() - last_status > 30:
            log.info(
                "status: runs=%d crashes=%d remaining=%.1fs",
                n_runs,
                n_crashes,
                deadline - time.monotonic(),
            )
            last_status = time.monotonic()

    log.info("done: runs=%d crashes=%d", n_runs, n_crashes)
    return 1 if n_crashes > 0 else 0


# ──────────────────────────────────────────────────────────────────────────────
# Atheris-driven path
# ──────────────────────────────────────────────────────────────────────────────


def _run_atheris(args: argparse.Namespace, log: logging.Logger) -> int:
    import atheris  # type: ignore[import-not-found]

    crash_dir = pathlib.Path(args.crash_dir)

    def fuzz_one_input(data: bytes) -> None:
        try:
            _try_parse(data)
        except Exception as exc:  # noqa: BLE001 — fuzz target
            _save_crash(data, crash_dir, exc)
            raise  # let Atheris see the exception

    # Wrap the parsing target so coverage instrumentation triggers.
    atheris.instrument_imports()
    atheris.Setup(
        [
            sys.argv[0],
            f"-max_total_time={int(args.time_budget)}",
            f"-runs=-1",
            f"-seed={int(args.seed)}",
            f"-artifact_prefix={crash_dir.as_posix()}/",
        ],
        fuzz_one_input,
    )
    atheris.Fuzz()
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# Reproduce mode
# ──────────────────────────────────────────────────────────────────────────────


def _reproduce(args: argparse.Namespace, log: logging.Logger) -> int:
    if not _demoparser2_available():
        log.error("demoparser2 not installed; cannot reproduce.")
        return 2
    path = pathlib.Path(args.reproduce)
    if not path.is_file():
        log.error("reproduce target not found: %s", path)
        return 2
    log.info("reproducing %s (%d bytes)", path, path.stat().st_size)
    data = path.read_bytes()
    try:
        _try_parse(data)
    except Exception as exc:  # noqa: BLE001
        log.error("reproduced: %s: %s", type(exc).__name__, exc)
        return 1
    log.info("did not reproduce; parser accepted the input.")
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def _sigterm_handler(_signum: int, _frame: Any) -> None:
    sys.stderr.write("\nfuzz_demo_parser: SIGTERM/SIGINT received; exiting.\n")
    sys.exit(0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--time-budget",
        type=int,
        default=DEFAULT_TIME_BUDGET,
        help="Total fuzzing time budget in seconds (default 1800).",
    )
    parser.add_argument("--corpus-dir", type=pathlib.Path, default=pathlib.Path(".fuzz/corpus"))
    parser.add_argument("--crash-dir", type=pathlib.Path, default=pathlib.Path(".fuzz/crashes"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--reproduce",
        type=pathlib.Path,
        help="Replay a single crash input file; exit 1 if it reproduces.",
    )
    parser.add_argument(
        "--force-fallback",
        action="store_true",
        help="Skip Atheris even if available; use random fallback.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | fuzz | %(message)s")
    log = logging.getLogger("fuzz_demo_parser")

    signal.signal(signal.SIGTERM, _sigterm_handler)
    signal.signal(signal.SIGINT, _sigterm_handler)

    if args.reproduce:
        return _reproduce(args, log)

    if not _demoparser2_available():
        log.error("demoparser2 is not installed; cannot fuzz. " "pip install demoparser2==0.41.1")
        return 2

    args.crash_dir.mkdir(parents=True, exist_ok=True)
    args.corpus_dir.mkdir(parents=True, exist_ok=True)

    if not args.force_fallback and _atheris_available():
        log.info("running with Atheris (coverage-guided)")
        return _run_atheris(args, log)

    log.info("Atheris not available or --force-fallback; using deterministic random fallback")
    return _run_random_fallback(args, log)


if __name__ == "__main__":
    sys.exit(main())
