"""Tests for the FACEIT API boundary (rate-limit handling)."""

from unittest.mock import MagicMock

import pytest

from Programma_CS2_RENAN.backend.data_sources.faceit_integration import (
    FACEITAPIError,
    FACEITIntegration,
)


class TestRetryAfterParsing:
    """R4 MED: RFC 7231 allows an HTTP-date Retry-After; bare int() raised
    an uncaught ValueError (the handler only catches RequestException),
    crashing the request path instead of backing off."""

    @staticmethod
    def _integration_with_responses(responses):
        integ = FACEITIntegration.__new__(FACEITIntegration)
        integ.BASE_URL = FACEITIntegration.BASE_URL
        integ.last_request_time = 0.0
        session = MagicMock()
        session.get.side_effect = responses
        integ.session = session
        return integ

    @staticmethod
    def _response(status, headers=None, payload=None):
        resp = MagicMock()
        resp.status_code = status
        resp.headers = headers or {}
        resp.json.return_value = payload or {}
        resp.raise_for_status.return_value = None
        return resp

    def test_http_date_retry_after_backs_off_60s(self, monkeypatch):
        import Programma_CS2_RENAN.backend.data_sources.faceit_integration as fi

        sleeps = []
        monkeypatch.setattr(fi.time, "sleep", lambda s: sleeps.append(s))

        rate_limited = self._response(429, headers={"Retry-After": "Fri, 17 Jul 2026 12:00:00 GMT"})
        ok = self._response(200, payload={"ok": True})
        integ = self._integration_with_responses([rate_limited, ok])

        result = integ._rate_limited_request("/players")
        assert result == {"ok": True}
        # sleeps[0] is the 429 backoff; the recursive call may add a small
        # inter-request throttle sleep afterwards.
        assert sleeps[0] == 60, "HTTP-date header must fall back to 60s, not crash"

    def test_numeric_retry_after_capped_at_300(self, monkeypatch):
        import Programma_CS2_RENAN.backend.data_sources.faceit_integration as fi

        sleeps = []
        monkeypatch.setattr(fi.time, "sleep", lambda s: sleeps.append(s))

        rate_limited = self._response(429, headers={"Retry-After": "900"})
        ok = self._response(200, payload={"ok": True})
        integ = self._integration_with_responses([rate_limited, ok])

        assert integ._rate_limited_request("/players") == {"ok": True}
        assert sleeps[0] == 300

    def test_persistent_429_raises_typed_error(self, monkeypatch):
        import Programma_CS2_RENAN.backend.data_sources.faceit_integration as fi

        monkeypatch.setattr(fi.time, "sleep", lambda s: None)
        rate_limited = self._response(429, headers={"Retry-After": "1"})
        integ = self._integration_with_responses([rate_limited] * 5)

        with pytest.raises(FACEITAPIError, match="Rate limit exceeded"):
            integ._rate_limited_request("/players")
