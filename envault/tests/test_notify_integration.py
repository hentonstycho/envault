"""Integration tests: notify wired into sync flow."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from envault.notify import NotifyEvent, NotifyPayload, notify
from envault.sync import SyncError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, webhook: str | None = None):
    cfg = MagicMock()
    cfg.output_path = str(tmp_path / ".env")
    cfg.ssm_path = "/myapp/dev"
    cfg.profile = "default"
    cfg.webhook_url = webhook
    return cfg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_notify_sync_ok_fires_correct_event(tmp_path):
    cfg = _make_config(tmp_path)
    payload = NotifyPayload(
        event=NotifyEvent.SYNC_OK,
        profile=cfg.profile,
        message="Synced 3 keys",
        meta={"keys": 3},
    )
    with patch("envault.notify._send_webhook") as mock_send:
        notify(payload, webhook_url="http://hook.local/")
    mock_send.assert_called_once()
    _, sent_payload = mock_send.call_args.args
    assert sent_payload.event == NotifyEvent.SYNC_OK
    assert sent_payload.meta["keys"] == 3


def test_notify_sync_failed_event(tmp_path):
    cfg = _make_config(tmp_path)
    payload = NotifyPayload(
        event=NotifyEvent.SYNC_FAILED,
        profile=cfg.profile,
        message="SSM unreachable",
    )
    with patch("envault.notify._send_webhook") as mock_send:
        notify(payload, webhook_url="http://hook.local/")
    _, sent = mock_send.call_args.args
    assert sent.event == NotifyEvent.SYNC_FAILED


def test_notify_no_webhook_does_not_call_send(tmp_path, caplog):
    import logging
    payload = NotifyPayload(
        event=NotifyEvent.SYNC_OK,
        profile="staging",
        message="ok",
    )
    with patch("envault.notify._send_webhook") as mock_send:
        with caplog.at_level(logging.INFO, logger="envault.notify"):
            notify(payload, webhook_url=None)
    mock_send.assert_not_called()
    assert "sync.ok" in caplog.text


def test_notify_rotate_stale_includes_profile():
    payload = NotifyPayload(
        event=NotifyEvent.ROTATE_STALE,
        profile="prod",
        message="2 paths overdue",
        meta={"stale": ["/app/prod/SECRET"]},
    )
    d = payload.to_dict()
    assert d["profile"] == "prod"
    assert d["meta"]["stale"] == ["/app/prod/SECRET"]
