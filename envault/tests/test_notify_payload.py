"""Fine-grained unit tests for NotifyPayload serialisation and NotifyEvent enum."""
from __future__ import annotations

import pytest

from envault.notify import NotifyEvent, NotifyPayload


def test_all_events_have_string_values():
    for event in NotifyEvent:
        assert isinstance(event.value, str)
        assert "." in event.value  # e.g. "sync.ok"


def test_payload_defaults_empty_meta():
    p = NotifyPayload(event=NotifyEvent.SYNC_OK, profile="dev", message="ok")
    assert p.meta == {}


def test_payload_to_dict_contains_all_keys():
    p = NotifyPayload(
        event=NotifyEvent.SYNC_FAILED,
        profile="staging",
        message="err",
        meta={"reason": "timeout"},
    )
    d = p.to_dict()
    assert set(d.keys()) == {"event", "profile", "message", "meta"}


def test_payload_event_serialised_as_string():
    p = NotifyPayload(event=NotifyEvent.ROTATE_STALE, profile="prod", message="stale")
    assert p.to_dict()["event"] == "rotate.stale"


def test_payload_meta_is_independent_per_instance():
    p1 = NotifyPayload(event=NotifyEvent.SYNC_OK, profile="a", message="x")
    p2 = NotifyPayload(event=NotifyEvent.SYNC_OK, profile="b", message="y")
    p1.meta["k"] = "v"
    assert "k" not in p2.meta


def test_payload_roundtrip_via_dict():
    original = NotifyPayload(
        event=NotifyEvent.SYNC_OK,
        profile="ci",
        message="3 keys synced",
        meta={"keys": 3},
    )
    d = original.to_dict()
    restored = NotifyPayload(
        event=NotifyEvent(d["event"]),
        profile=d["profile"],
        message=d["message"],
        meta=d["meta"],
    )
    assert restored.event == original.event
    assert restored.profile == original.profile
    assert restored.meta == original.meta


def test_notify_event_from_string():
    assert NotifyEvent("sync.ok") is NotifyEvent.SYNC_OK
    assert NotifyEvent("sync.failed") is NotifyEvent.SYNC_FAILED
    assert NotifyEvent("rotate.stale") is NotifyEvent.ROTATE_STALE


def test_notify_event_invalid_string_raises():
    with pytest.raises(ValueError):
        NotifyEvent("unknown.event")
