"""F-0013 regression: the parse timeout RETURNS — it no longer joins the
hung worker on with-block exit ("prevent indefinite hangs" was illusory:
shutdown(wait=True) blocked on the unkillable parse thread)."""

import threading
import time

from Programma_CS2_RENAN.backend.data_sources.demo_parser import _run_with_parse_timeout


def test_timeout_returns_promptly_despite_hung_worker():
    release = threading.Event()

    def hung_parse(_arg):
        release.wait(timeout=30)  # simulates a wedged demoparser2 call
        return "late"

    t0 = time.monotonic()
    ok, result = _run_with_parse_timeout(hung_parse, ("x",), 1, "test", "hung.dem")
    elapsed = time.monotonic() - t0

    try:
        assert ok is False and result is None
        assert elapsed < 5, f"caller blocked {elapsed:.1f}s — the join is back"
    finally:
        release.set()  # let the orphan finish so the test process exits clean


def test_fast_call_returns_result():
    ok, result = _run_with_parse_timeout(lambda x: x * 2, (21,), 5, "test", "ok.dem")
    assert ok is True and result == 42
