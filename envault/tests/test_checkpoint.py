"""Unit tests for envault.checkpoint."""
from __future__ import annotations

import json
import time

import pytest

from envault.checkpoint import (
    Checkpoint,
    CheckpointError,
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)


@pytest.fixture()
def chk_dir(tmp_path):
    return tmp_path / "checkpoints"


def _make_checkpoint(profile: str = "dev", param_count: int = 3) -> Checkpoint:
    return Checkpoint(
        profile=profile,
        synced_at=time.time(),
        env_file=".env",
        param_count=param_count,
    )


# ---------------------------------------------------------------------------
# Checkpoint dataclass
# ---------------------------------------------------------------------------

def test_to_dict_contains_all_keys():
    c = _make_checkpoint()
    d = c.to_dict()
    assert {"profile", "synced_at", "env_file", "param_count", "extra"} == set(d)


def test_from_dict_roundtrip():
    c = _make_checkpoint(profile="staging", param_count=7)
    restored = Checkpoint.from_dict(c.to_dict())
    assert restored.profile == c.profile
    assert restored.synced_at == pytest.approx(c.synced_at)
    assert restored.param_count == 7


def test_age_seconds_uses_provided_now():
    c = Checkpoint(profile="p", synced_at=1000.0, env_file=".env", param_count=1)
    assert c.age_seconds(now=1060.0) == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# save / load
# ---------------------------------------------------------------------------

def test_save_creates_file(chk_dir):
    c = _make_checkpoint()
    save_checkpoint(chk_dir, c)
    assert any(chk_dir.iterdir())


def test_load_returns_none_when_missing(chk_dir):
    assert load_checkpoint(chk_dir, "nonexistent") is None


def test_save_and_load_roundtrip(chk_dir):
    c = _make_checkpoint(profile="prod", param_count=12)
    save_checkpoint(chk_dir, c)
    loaded = load_checkpoint(chk_dir, "prod")
    assert loaded is not None
    assert loaded.profile == "prod"
    assert loaded.param_count == 12


def test_load_raises_on_corrupt_file(chk_dir):
    chk_dir.mkdir(parents=True, exist_ok=True)
    bad_file = chk_dir / ".envault_checkpoint_dev.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(CheckpointError):
        load_checkpoint(chk_dir, "dev")


def test_save_overwrites_previous(chk_dir):
    c1 = Checkpoint(profile="dev", synced_at=100.0, env_file=".env", param_count=1)
    c2 = Checkpoint(profile="dev", synced_at=200.0, env_file=".env", param_count=5)
    save_checkpoint(chk_dir, c1)
    save_checkpoint(chk_dir, c2)
    loaded = load_checkpoint(chk_dir, "dev")
    assert loaded.synced_at == pytest.approx(200.0)
    assert loaded.param_count == 5


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

def test_clear_returns_true_when_existed(chk_dir):
    save_checkpoint(chk_dir, _make_checkpoint())
    assert clear_checkpoint(chk_dir, "dev") is True
    assert load_checkpoint(chk_dir, "dev") is None


def test_clear_returns_false_when_missing(chk_dir):
    assert clear_checkpoint(chk_dir, "dev") is False


def test_profile_with_slashes_creates_safe_filename(chk_dir):
    c = _make_checkpoint(profile="team/project/dev")
    save_checkpoint(chk_dir, c)
    files = list(chk_dir.iterdir())
    assert len(files) == 1
    assert "/" not in files[0].name
