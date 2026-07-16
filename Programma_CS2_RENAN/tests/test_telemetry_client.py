"""Telemetry client ↔ server contract (R4 HIGH x2 fix, 2026-07-16).

The client sent a ``player_id`` key while the server's MatchTelemetry
schema requires ``player_name`` (every request 422'd), and treated only
HTTP 200 as success while the endpoint is declared ``status_code=202`` —
success was unreachable end-to-end. These tests pin the payload contract
against the REAL server schema and the 202-success handling.
"""

from unittest.mock import MagicMock, patch

from Programma_CS2_RENAN.backend.server import MatchTelemetry
from Programma_CS2_RENAN.backend.services import telemetry_client


def _send(status_code: int, captured: dict):
    response = MagicMock()
    response.status_code = status_code
    response.is_success = 200 <= status_code < 300
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.side_effect = lambda url, json, timeout: captured.update(json) or response
    with patch.object(telemetry_client, "httpx") as fake_httpx:
        fake_httpx.Client.return_value = client
        return telemetry_client.send_match_telemetry(
            "ZywOo", "vitality-vs-spirit-m2-inferno", {"rating": 1.32}
        )


def test_payload_validates_against_real_server_schema():
    captured: dict = {}
    _send(202, captured)
    # Pydantic validation against the actual server model — a renamed or
    # missing field fails here exactly as it would 422 in production.
    parsed = MatchTelemetry(**captured)
    assert parsed.player_name == "ZywOo"
    assert parsed.match_id == "vitality-vs-spirit-m2-inferno"
    assert parsed.stats == {"rating": 1.32}


def test_202_accepted_is_success():
    assert _send(202, {}) is True


def test_422_is_failure():
    assert _send(422, {}) is False
