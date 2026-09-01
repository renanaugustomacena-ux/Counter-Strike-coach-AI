"""F-0006 — the demo-parse guard SSOT.

demoparser2 is a Rust extension: a malformed .dem can raise a pyo3
``PanicException`` (observed live on 0.41.4: ``range end index 16 out of
range for slice of length 12`` in first_pass/parser.rs). PanicException
subclasses ``BaseException`` — every ``except Exception`` parse guard in
the pipeline let it fly, so one bad demo aborted the whole ingestion run
despite docstrings promising "never aborts".

pyo3 creates the class LAZILY at first panic (module ``pyo3_runtime`` is
not importable up front), so the guard is name-based. Module-07
discipline: KeyboardInterrupt / SystemExit / GeneratorExit ALWAYS
propagate — the only BaseException absorbed is the named panic.

Usage at a call site::

    try:
        parser.parse_header()
    except BaseException as exc:  # noqa: BLE001 — filtered by is_parse_error
        if not is_parse_error(exc):
            raise
        <existing fallback>
"""

from __future__ import annotations


class ParseTimeoutError(RuntimeError):
    """Tick-parse timeout. Raised instead of returning an empty DataFrame:
    an empty frame is indistinguishable from a legitimately fully-processed
    incremental parse, so a timeout that returned one was recorded as
    'completed / No new ticks' — full aggregate stats, zero ticks, never
    retried. Lives here (not in demo_parser) so ``is_parse_error`` can
    PROPAGATE it: a timeout is an infrastructure verdict, not a malformed
    demo, and must reach the task-status machinery as a failure."""


_PROPAGATE = (KeyboardInterrupt, SystemExit, GeneratorExit, ParseTimeoutError)


def is_parse_error(exc: BaseException) -> bool:
    """True when a demoparser2 guard should ABSORB this exception."""
    if isinstance(exc, _PROPAGATE):
        return False
    if isinstance(exc, Exception):
        return True
    return type(exc).__name__ == "PanicException"
