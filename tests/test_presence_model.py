from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.presence_model import PresenceRecord, PresenceStatus


def test_presence_status_values() -> None:
    assert PresenceStatus.RUNNING.value == "running"
    assert PresenceStatus.STOPPED.value == "stopped"


def test_presence_record_round_trip_without_container_id() -> None:
    record = PresenceRecord(
        agent_id="worker-001",
        runtime_status=PresenceStatus.RUNNING,
        last_heartbeat_at="2026-04-15T10:15:00Z",
    )

    restored = PresenceRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.container_id is None
    assert restored.to_dict() == {
        "agent_id": "worker-001",
        "runtime_status": "running",
        "last_heartbeat_at": "2026-04-15T10:15:00Z",
    }


def test_presence_record_round_trip_with_container_id() -> None:
    record = PresenceRecord(
        agent_id="worker-001",
        runtime_status=PresenceStatus.RUNNING,
        last_heartbeat_at="2026-04-15T10:20:00Z",
        container_id="container-123",
    )

    restored = PresenceRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "agent_id": "worker-001",
        "runtime_status": "running",
        "last_heartbeat_at": "2026-04-15T10:20:00Z",
        "container_id": "container-123",
    }


def test_presence_record_missing_required_fields_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid presence record: missing required fields: 'last_heartbeat_at'",
    ):
        PresenceRecord.from_dict(
            {
                "agent_id": "worker-001",
                "runtime_status": "running",
            }
        )


def test_presence_record_invalid_runtime_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid presence runtime_status: 'paused'"):
        PresenceRecord.from_dict(
            {
                "agent_id": "worker-001",
                "runtime_status": "paused",
                "last_heartbeat_at": "2026-04-15T10:25:00Z",
            }
        )


def test_presence_record_invalid_container_id_error() -> None:
    with pytest.raises(ValueError, match="Invalid presence container_id: expected str"):
        PresenceRecord.from_dict(
            {
                "agent_id": "worker-001",
                "runtime_status": "running",
                "last_heartbeat_at": "2026-04-15T10:25:00Z",
                "container_id": 123,
            }
        )
