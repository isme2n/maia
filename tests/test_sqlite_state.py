from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.app_state import get_state_db_path
from maia.registry import AgentRegistry
from maia.runtime_adapter import RuntimeState, RuntimeStatus
from maia.runtime_state_storage import RuntimeStateStorage
from maia.sqlite_state import SQLiteState
from maia.storage import JsonRegistryStorage


def test_sqlite_backed_storages_do_not_write_transitional_json_caches(tmp_path: Path) -> None:
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

    maia_home = tmp_path / ".maia"
    assert not (maia_home / "registry.json").exists()
    assert not (maia_home / "runtime" / "runtime-state.json").exists()


def test_app_state_exposes_sqlite_db_path(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path)}

    assert get_state_db_path(env) == tmp_path / ".maia" / "maia.db"


def test_sqlite_state_initializes_control_plane_schema(tmp_path: Path) -> None:
    path = tmp_path / "maia.db"

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
        "keryx_sessions",
        "keryx_session_participants",
        "keryx_messages",
        "keryx_handoffs",
    } <= tables
    assert bootstrap_row == ("pending", "shared infra not bootstrapped yet")


def test_sqlite_backed_storages_round_trip_control_plane_state(tmp_path: Path) -> None:
    db_path = tmp_path / "maia.db"
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

    restored_registry = JsonRegistryStorage().load(db_path)
    restored_runtime_states = RuntimeStateStorage().load(db_path)

    assert [record.to_dict() for record in restored_registry.list()] == [
        {
            "agent_id": "agent-001",
            "name": "planner",
            "status": "stopped",
            "speaking_style": "respectful",
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


def test_sqlite_state_tracks_infra_status(tmp_path: Path) -> None:
    path = tmp_path / "maia.db"
    state = SQLiteState(path)

    state.set_infra_status("bootstrap", status="ready", detail="sqlite initialized")

    assert state.get_infra_status("bootstrap") == {
        "name": "bootstrap",
        "status": "ready",
        "detail": "sqlite initialized",
    }
