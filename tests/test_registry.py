from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.registry import AgentRegistry


def test_registry_add_and_get() -> None:
    registry = AgentRegistry()
    record = AgentRecord(
        agent_id="agent-001",
        name="planner",
        status=AgentStatus.RUNNING,
        persona="careful",
    )

    registry.add(record)
    stored = registry.get("agent-001")

    assert stored == record
    assert stored is not record


def test_registry_duplicate_add_error() -> None:
    registry = AgentRegistry()
    record = AgentRecord(
        agent_id="agent-001",
        name="planner",
        status=AgentStatus.RUNNING,
        persona="careful",
    )

    registry.add(record)

    with pytest.raises(ValueError, match="Agent with id 'agent-001' already exists"):
        registry.add(record)


def test_registry_list_preserves_add_order() -> None:
    registry = AgentRegistry()
    first = AgentRecord(
        agent_id="agent-001",
        name="planner",
        status=AgentStatus.RUNNING,
        persona="careful",
    )
    second = AgentRecord(
        agent_id="agent-002",
        name="reviewer",
        status=AgentStatus.STOPPED,
        persona="strict",
    )

    registry.add(second)
    registry.add(first)

    records = registry.list()

    assert [record.agent_id for record in records] == ["agent-002", "agent-001"]


def test_registry_set_status_updates_record() -> None:
    registry = AgentRegistry()
    record = AgentRecord(
        agent_id="agent-001",
        name="planner",
        status=AgentStatus.RUNNING,
        persona="careful",
    )

    registry.add(record)
    updated = registry.set_status("agent-001", AgentStatus.ARCHIVED)

    assert updated.status is AgentStatus.ARCHIVED
    assert registry.get("agent-001").status is AgentStatus.ARCHIVED
    assert record.status is AgentStatus.RUNNING


def test_registry_get_missing_id_error() -> None:
    registry = AgentRegistry()

    with pytest.raises(LookupError, match="Agent with id 'missing' not found"):
        registry.get("missing")


def test_registry_set_status_missing_id_error() -> None:
    registry = AgentRegistry()

    with pytest.raises(LookupError, match="Agent with id 'missing' not found"):
        registry.set_status("missing", AgentStatus.STOPPED)
