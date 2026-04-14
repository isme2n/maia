from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus


def test_agent_status_values() -> None:
    assert AgentStatus.RUNNING.value == "running"
    assert AgentStatus.STOPPED.value == "stopped"
    assert AgentStatus.ARCHIVED.value == "archived"


def test_agent_record_creation() -> None:
    record = AgentRecord(
        agent_id="agent-001",
        name="planner",
        status=AgentStatus.RUNNING,
        persona="careful",
    )

    assert record.agent_id == "agent-001"
    assert record.name == "planner"
    assert record.status is AgentStatus.RUNNING
    assert record.persona == "careful"


def test_agent_record_round_trip() -> None:
    record = AgentRecord(
        agent_id="agent-002",
        name="reviewer",
        status=AgentStatus.STOPPED,
        persona="strict",
    )

    restored = AgentRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "agent_id": "agent-002",
        "name": "reviewer",
        "status": "stopped",
        "persona": "strict",
    }


def test_agent_record_invalid_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid agent status: 'paused'"):
        AgentRecord.from_dict(
            {
                "agent_id": "agent-003",
                "name": "runner",
                "status": "paused",
                "persona": "fast",
            }
        )
