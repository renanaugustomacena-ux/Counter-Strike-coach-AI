"""F-0006 regression: demoparser2 guards absorb Rust panics AND the
parser's own error class; interrupts always propagate.

Live evidence (baseline): pyo3 PanicException ('range end index 16 out
of range for slice of length 12') flew through every `except Exception`
guard — one bad demo aborted ingestion. Additionally the two narrowed
`(OSError, ValueError, RuntimeError, KeyError)` guards missed
demoparser2's OWN error class, which is a direct Exception subclass."""

from unittest.mock import patch

import pytest

from Programma_CS2_RENAN.backend.data_sources.parse_guard import is_parse_error


class _FakePanic(BaseException):
    """Mimics pyo3_runtime.PanicException: BaseException subclass, lazy class."""


_FakePanic.__name__ = "PanicException"


class TestIsParseError:
    def test_panic_named_baseexception_is_absorbed(self):
        assert is_parse_error(_FakePanic("range end index 16"))

    def test_ordinary_exceptions_are_absorbed(self):
        assert is_parse_error(ValueError("bad demo"))
        assert is_parse_error(RuntimeError("parse fail"))

    def test_demoparser_own_error_class_is_absorbed(self):
        class Exception_(Exception):  # direct Exception subclass, like DemoParser.Exception
            pass

        assert is_parse_error(Exception_("corrupt header"))

    @pytest.mark.parametrize("exc", [KeyboardInterrupt(), SystemExit(0), GeneratorExit()])
    def test_interrupts_always_propagate(self, exc):
        assert not is_parse_error(exc)

    def test_unknown_baseexception_propagates(self):
        class Weird(BaseException):
            pass

        assert not is_parse_error(Weird())


class TestHeaderMetaGuard:
    def test_panic_in_parse_header_yields_defaults(self):
        from Programma_CS2_RENAN.run_ingestion import _parse_demo_header_meta

        with patch("demoparser2.DemoParser") as dp:
            dp.return_value.parse_header.side_effect = _FakePanic("slice of length 12")
            map_name, tick_rate = _parse_demo_header_meta("corrupt.dem")
        assert map_name == "de_unknown"
        assert tick_rate == 64.0

    def test_keyboard_interrupt_escapes_the_guard(self):
        from Programma_CS2_RENAN.run_ingestion import _parse_demo_header_meta

        with patch("demoparser2.DemoParser") as dp:
            dp.return_value.parse_header.side_effect = KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                _parse_demo_header_meta("any.dem")
