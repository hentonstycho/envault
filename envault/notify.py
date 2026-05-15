"""Notification hooks for sync events (stdout, webhook, or no-op)."""
from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class NotifyError(Exception):
    """Raised when a notification delivery fails."""


class NotifyEvent(str, Enum):
    SYNC_OK = "sync.ok"
    SYNC_FAILED = "sync.failed"
    ROTATE_STALE = "rotate.stale"


@dataclass
class NotifyPayload:
    event: NotifyEvent
    profile: str
    message: str
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event": self.event.value,
            "profile": self.profile,
            "message": self.message,
            "meta": self.meta,
        }


def _send_webhook(url: str, payload: NotifyPayload, timeout: int = 5) -> None:
    body = json.dumps(payload.to_dict()).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except Exception as exc:  # noqa: BLE001
        raise NotifyError(f"Webhook delivery failed: {exc}") from exc


def notify(
    payload: NotifyPayload,
    webhook_url: Optional[str] = None,
    *,
    silent: bool = False,
) -> None:
    """Dispatch a notification.  Falls back to logging when no webhook is set."""
    log.debug("notify event=%s profile=%s", payload.event.value, payload.profile)
    if webhook_url:
        try:
            _send_webhook(webhook_url, payload)
        except NotifyError:
            if not silent:
                raise
            log.warning("Webhook notification suppressed (silent=True)")
    else:
        log.info("[notify] %s – %s", payload.event.value, payload.message)
