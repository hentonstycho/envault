"""Tests for envault.notify."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

from envault.notify import (
    NotifyError,
    NotifyEvent,
    NotifyPayload,
    _send_webhook,
    notify,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(
    event: NotifyEvent = NotifyEvent.SYNC_OK,
    profile: str = "default",
    message: str = "all good",
) -> NotifyPayload:
    return NotifyPayload(event=event, profile=profile, message=message)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_payload_to_dict():
    p = _make_payload(meta={"keys": 3})
    d = p.to_dict()
    assert d["event"] == "sync.ok"
    assert d["profile"] == "default"
    assert d["meta"] == {"keys": 3}


def test_notify_no_webhook_logs(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="envault.notify"):
        notify(_make_payload(), webhook_url=None)
    assert "sync.ok" in caplog.text


def test_notify_calls_send_webhook():
    payload = _make_payload()
    with patch("envault.notify._send_webhook") as mock_send:
        notify(payload, webhook_url="http://example.com/hook")
    mock_send.assert_called_once_with("http://example.com/hook", payload)


def test_notify_raises_when_webhook_fails_not_silent():
    payload = _make_payload()
    with patch("envault.notify._send_webhook", side_effect=NotifyError("boom")):
        with pytest.raises(NotifyError, match="boom"):
            notify(payload, webhook_url="http://bad.host/", silent=False)


def test_notify_silent_swallows_webhook_error(caplog):
    import logging
    payload = _make_payload()
    with patch("envault.notify._send_webhook", side_effect=NotifyError("boom")):
        with caplog.at_level(logging.WARNING, logger="envault.notify"):
            notify(payload, webhook_url="http://bad.host/", silent=True)
    assert "suppressed" in caplog.text


def test_send_webhook_raises_on_bad_url():
    with pytest.raises(NotifyError):
        _send_webhook("http://127.0.0.1:1", _make_payload(), timeout=1)


def test_send_webhook_posts_json(tmp_path):
    """Spin up a tiny HTTP server and verify the payload arrives."""
    received: list[bytes] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            received.append(self.rfile.read(length))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_):  # silence server logs
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    t = Thread(target=server.handle_request, daemon=True)
    t.start()

    payload = _make_payload(event=NotifyEvent.ROTATE_STALE, message="stale keys")
    _send_webhook(f"http://127.0.0.1:{port}/hook", payload)
    t.join(timeout=2)

    assert received
    data = json.loads(received[0])
    assert data["event"] == "rotate.stale"
    assert data["message"] == "stale keys"
