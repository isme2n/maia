from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.registry import AgentRegistry
from maia.storage import JsonRegistryStorage


def test_json_registry_storage_round_trip(tmp_path: Path) -> None:
    storage = JsonRegistryStorage()
    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="agent-001",
            name="planner",
            status=AgentStatus.RUNNING,
            persona="careful",
        )
    )
    registry.add(
        AgentRecord(
            agent_id="agent-002",
            name="reviewer",
            status=AgentStatus.STOPPED,
            persona="strict",
        )
    )
    path = tmp_path / "data" / "registry.json"

    storage.save(path, registry)

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "agents": [
            {
                "agent_id": "agent-001",
                "name": "planner",
                "status": "running",
                "persona": "careful",
            },
            {
                "agent_id": "agent-002",
                "name": "reviewer",
                "status": "stopped",
                "persona": "strict",
            },
        ]
    }

    restored = storage.load(path)
    assert restored.list() == registry.list()


def test_json_registry_storage_missing_file_returns_empty_registry(
    tmp_path: Path,
) -> None:
    storage = JsonRegistryStorage()

    restored = storage.load(tmp_path / "missing.json")

    assert restored.list() == []


def test_json_registry_storage_invalid_json_raises_clear_error(
    tmp_path: Path,
) -> None:
    storage = JsonRegistryStorage()
    path = tmp_path / "registry.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid registry JSON"):
        storage.load(path)


def test_json_registry_storage_invalid_agent_record_raises_clear_error(
    tmp_path: Path,
) -> None:
    storage = JsonRegistryStorage()
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"agents": [{}]}), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"Invalid registry JSON.*agent record at index 0 is missing required fields",
    ):
        storage.load(path)


def test_json_registry_storage_invalid_agent_status_raises_clear_error(
    tmp_path: Path,
) -> None:
    storage = JsonRegistryStorage()
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps(
            {
                "agents": [
                    {
                        "agent_id": "agent-001",
                        "name": "planner",
                        "status": "broken",
                        "persona": "careful",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"Invalid registry JSON.*agent record at index 0 is invalid: Invalid agent status",
    ):
        storage.load(path)


def test_json_registry_storage_preserves_insertion_order(tmp_path: Path) -> None:
    storage = JsonRegistryStorage()
    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="agent-002",
            name="reviewer",
            status=AgentStatus.STOPPED,
            persona="strict",
        )
    )
    registry.add(
        AgentRecord(
            agent_id="agent-001",
            name="planner",
            status=AgentStatus.RUNNING,
            persona="careful",
        )
    )
    path = tmp_path / "registry.json"

    storage.save(path, registry)

    restored = storage.load(path)
    assert [record.agent_id for record in restored.list()] == [
        "agent-002",
        "agent-001",
    ]


def test_json_registry_storage_preserves_status_values(tmp_path: Path) -> None:
    storage = JsonRegistryStorage()
    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="agent-001",
            name="runner",
            status=AgentStatus.RUNNING,
            persona="fast",
        )
    )
    registry.add(
        AgentRecord(
            agent_id="agent-002",
            name="sleeper",
            status=AgentStatus.STOPPED,
            persona="calm",
        )
    )
    registry.add(
        AgentRecord(
            agent_id="agent-003",
            name="archivist",
            status=AgentStatus.ARCHIVED,
            persona="tidy",
        )
    )
    path = tmp_path / "registry.json"

    storage.save(path, registry)

    restored = storage.load(path)
    assert [record.status for record in restored.list()] == [
        AgentStatus.RUNNING,
        AgentStatus.STOPPED,
        AgentStatus.ARCHIVED,
    ]
