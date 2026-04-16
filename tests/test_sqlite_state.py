from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.app_state import get_collaboration_path, get_registry_path, get_runtime_state_path, get_state_db_path
from maia.collaboration_storage import CollaborationState, CollaborationStorage
from maia.handoff_model import HandoffKind, HandoffRecord
from maia.message_model import MessageKind, MessageRecord, ThreadRecord
from maia.registry import AgentRegistry
from maia.runtime_adapter import RuntimeState, RuntimeStatus
from maia.runtime_state_storage import RuntimeStateStorage
from maia.sqlite_state import SQLiteState
from maia.storage import JsonRegistryStorage


def test_sqlite_backed_storages_write_labeled_transitional_json_caches(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path)}
    db_path = get_state_db_path(env)

    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="agent-001",
            name="planner",
            status=AgentStatus.STOPPED,
            persona="",
        )
    )
    JsonRegistryStorage().save(db_path, registry)
    RuntimeStateStorage().save(
        db_path,
        {
            "agent-001": RuntimeState(
                agent_id="agent-001",
                runtime_status=RuntimeStatus.STOPPED,
                setup_status="configured",
            )
        },
    )
    CollaborationStorage().save(db_path, threads=[], messages=[], handoffs=[])

    registry_cache = json.loads(get_registry_path(env).read_text(encoding="utf-8"))
    runtime_cache = json.loads(get_runtime_state_path(env).read_text(encoding="utf-8"))
    collaboration_cache = json.loads(get_collaboration_path(env).read_text(encoding="utf-8"))

    for payload in (registry_cache, runtime_cache, collaboration_cache):
        assert payload["_maia_local_state"] is True
        assert payload["_maia_storage_kind"] == "transitional-json-cache"


def test_app_state_exposes_sqlite_db_path(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path)}

    assert get_state_db_path(env) == tmp_path / ".maia" / "state.db"
    assert get_registry_path(env) == tmp_path / ".maia" / "registry.json"
    assert get_runtime_state_path(env) == tmp_path / ".maia" / "runtime" / "runtime-state.json"
    assert get_collaboration_path(env) == tmp_path / ".maia" / "collaboration.json"


def test_sqlite_state_initializes_control_plane_schema(tmp_path: Path) -> None:
    path = tmp_path / "state.db"

    SQLiteState(path).initialize()

    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        bootstrap_row = connection.execute(
            "SELECT status, detail FROM infra_state WHERE name = 'bootstrap'"
        ).fetchone()

    assert {
        "agents",
        "runtime_states",
        "infra_state",
        "collaboration_threads",
        "collaboration_messages",
        "collaboration_handoffs",
    } <= tables
    assert bootstrap_row == ("pending", "shared infra not bootstrapped yet")


def test_sqlite_backed_storages_round_trip_control_plane_state(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="agent-001",
            name="planner",
            status=AgentStatus.STOPPED,
            persona="",
            role="lead",
            model="gpt-5",
            tags=["prod"],
        )
    )

    JsonRegistryStorage().save(db_path, registry)
    RuntimeStateStorage().save(
        db_path,
        {
            "agent-001": RuntimeState(
                agent_id="agent-001",
                runtime_status=RuntimeStatus.RUNNING,
                runtime_handle="runtime-001",
                setup_status="configured",
            )
        },
    )
    CollaborationStorage().save(
        db_path,
        threads=[
            ThreadRecord(
                thread_id="thread-001",
                topic="runtime review",
                participants=["agent-001", "agent-002"],
                created_by="agent-001",
                status="open",
                created_at="2026-04-16T16:01:00Z",
                updated_at="2026-04-16T16:01:00Z",
            )
        ],
        messages=[
            MessageRecord(
                message_id="msg-001",
                thread_id="thread-001",
                from_agent="agent-001",
                to_agent="agent-002",
                kind=MessageKind.REQUEST,
                body="review this",
                created_at="2026-04-16T16:02:00Z",
            )
        ],
        handoffs=[
            HandoffRecord(
                handoff_id="handoff-001",
                thread_id="thread-001",
                from_agent="agent-001",
                to_agent="agent-002",
                kind=HandoffKind.REPORT,
                location="reports/review.md",
                summary="ready",
                created_at="2026-04-16T16:03:00Z",
            )
        ],
    )

    restored_registry = JsonRegistryStorage().load(db_path)
    restored_runtime_states = RuntimeStateStorage().load(db_path)
    restored_collaboration = CollaborationStorage().load(db_path)

    assert [record.to_dict() for record in restored_registry.list()] == [
        {
            "agent_id": "agent-001",
            "name": "planner",
            "status": "stopped",
            "persona": "",
            "role": "lead",
            "model": "gpt-5",
            "tags": ["prod"],
        }
    ]
    assert restored_runtime_states == {
        "agent-001": RuntimeState(
            agent_id="agent-001",
            runtime_status=RuntimeStatus.RUNNING,
            runtime_handle="runtime-001",
            setup_status="configured",
        )
    }
    assert restored_collaboration == CollaborationState(
        threads=[
            ThreadRecord(
                thread_id="thread-001",
                topic="runtime review",
                participants=["agent-001", "agent-002"],
                created_by="agent-001",
                status="open",
                created_at="2026-04-16T16:01:00Z",
                updated_at="2026-04-16T16:01:00Z",
            )
        ],
        messages=[
            MessageRecord(
                message_id="msg-001",
                thread_id="thread-001",
                from_agent="agent-001",
                to_agent="agent-002",
                kind=MessageKind.REQUEST,
                body="review this",
                created_at="2026-04-16T16:02:00Z",
            )
        ],
        handoffs=[
            HandoffRecord(
                handoff_id="handoff-001",
                thread_id="thread-001",
                from_agent="agent-001",
                to_agent="agent-002",
                kind=HandoffKind.REPORT,
                location="reports/review.md",
                summary="ready",
                created_at="2026-04-16T16:03:00Z",
            )
        ],
    )


def test_sqlite_state_tracks_infra_status(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    state = SQLiteState(path)

    state.set_infra_status("bootstrap", status="ready", detail="sqlite initialized")

    assert state.get_infra_status("bootstrap") == {
        "name": "bootstrap",
        "status": "ready",
        "detail": "sqlite initialized",
    }