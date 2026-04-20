from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from maia.agent_context import (
    build_runtime_context,
    format_runtime_context_for_prompt,
    load_recent_handoffs,
    load_team_roster,
    load_thread_context,
)
from maia.agent_model import AgentRecord, AgentStatus
from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)
from maia.runtime_adapter import RuntimeState, RuntimeStatus
from maia.runtime_spec import RuntimeSpec
from maia.runtime_state_storage import RuntimeStateStorage
from maia.sqlite_state import SQLiteState
from maia.storage import JsonRegistryStorage
from maia.registry import AgentRegistry
from maia.keryx_service import KeryxService


def _seed_state(db_path: Path) -> None:
    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="planner",
            name="planner",
            call_sign="planner",
            status=AgentStatus.STOPPED,
            persona="",
            role="planner",
            runtime_spec=RuntimeSpec(
                image="maia-local/hermes-worker:latest",
                workspace="/opt/maia",
                command=[],
                env={},
            ),
        )
    )
    registry.add(
        AgentRecord(
            agent_id="reviewer",
            name="reviewer",
            call_sign="reviewer",
            status=AgentStatus.RUNNING,
            persona="",
            role="reviewer",
            runtime_spec=RuntimeSpec(
                image="maia-local/hermes-worker:latest",
                workspace="/opt/maia",
                command=[],
                env={},
            ),
        )
    )
    JsonRegistryStorage().save(db_path, registry)
    RuntimeStateStorage().save(
        db_path,
        {
            "planner": RuntimeState(
                agent_id="planner",
                runtime_status=RuntimeStatus.STOPPED,
                setup_status="complete",
            ),
            "reviewer": RuntimeState(
                agent_id="reviewer",
                runtime_status=RuntimeStatus.RUNNING,
                runtime_handle="runtime-001",
                setup_status="complete",
            ),
        },
    )
    service = KeryxService(db_path)
    service.create_session(
        KeryxSessionRecord(
            session_id="thread-001",
            topic="runtime review",
            participants=["planner", "reviewer"],
            created_by="planner",
            status=KeryxSessionStatus.ACTIVE,
            created_at="2026-04-17T02:00:00Z",
            updated_at="2026-04-17T02:02:00Z",
        )
    )
    service.create_session_message(
        "thread-001",
        KeryxMessageRecord(
            message_id="msg-001",
            session_id="thread-001",
            from_agent="planner",
            to_agent="reviewer",
            kind="request",
            body="Please review the patch.",
            created_at="2026-04-17T02:01:00Z",
        ),
    )
    service.create_thread_handoff(
        "thread-001",
        KeryxHandoffRecord(
            handoff_id="handoff-001",
            session_id="thread-001",
            from_agent="planner",
            to_agent="reviewer",
            kind="file",
            status=KeryxHandoffStatus.OPEN,
            location="/tmp/review.md",
            summary="Patch review note",
            created_at="2026-04-17T02:02:00Z",
            updated_at="2026-04-17T02:02:00Z",
        ),
    )


def test_load_team_roster_reads_sqlite_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    _seed_state(db_path)

    roster = load_team_roster(db_path)

    assert [entry.agent_id for entry in roster] == ["planner", "reviewer"]
    assert roster[0].role == "planner"
    assert roster[0].runtime_status == "stopped"
    assert roster[1].runtime_status == "running"
    assert roster[1].setup_status == "complete"


def test_load_thread_context_includes_pending_on_and_recent_message_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    _seed_state(db_path)

    context = load_thread_context(db_path, "thread-001")

    assert context is not None
    assert context.thread_id == "thread-001"
    assert context.topic == "runtime review"
    assert context.participants == ["planner", "reviewer"]
    assert context.pending_on == "reviewer"
    assert context.recent_message_ids == ["msg-001"]


def test_load_recent_handoffs_returns_newest_first(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    _seed_state(db_path)
    service = KeryxService(db_path)
    service.create_thread_handoff(
        "thread-001",
        KeryxHandoffRecord(
            handoff_id="handoff-002",
            session_id="thread-001",
            from_agent="reviewer",
            to_agent="planner",
            kind="report",
            status=KeryxHandoffStatus.OPEN,
            location="/tmp/report.md",
            summary="Follow-up report",
            created_at="2026-04-17T02:03:00Z",
            updated_at="2026-04-17T02:03:00Z",
        ),
    )

    handoffs = load_recent_handoffs(db_path, thread_id="thread-001", limit=2)

    assert [item.handoff_id for item in handoffs] == ["handoff-002", "handoff-001"]


def test_build_runtime_context_and_format_for_prompt_include_roster_thread_and_handoffs(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    _seed_state(db_path)
    incoming = KeryxMessageRecord(
        message_id="msg-002",
        session_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind="request",
        body="Check current team context.",
        created_at="2026-04-17T02:04:00Z",
    )

    context = build_runtime_context(db_path, agent_id="reviewer", incoming_message=incoming)
    prompt_context = format_runtime_context_for_prompt(context)

    assert context.self_agent.agent_id == "reviewer"
    assert "Known team roster:" in prompt_context
    assert "planner (agent_id=planner, role=planner, runtime=stopped)" in prompt_context
    assert "reviewer (agent_id=reviewer, role=reviewer, runtime=running)" in prompt_context
    assert "Active thread:" in prompt_context
    assert "thread_id=thread-001" in prompt_context
    assert "pending_on=reviewer" in prompt_context
    assert "Recent handoffs for this thread:" in prompt_context
    assert "handoff_id=handoff-001" in prompt_context


def test_context_helpers_fail_clearly_for_missing_or_unreadable_db(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.db"

    with pytest.raises(ValueError, match="state DB at .* is missing"):
        load_team_roster(missing_path)

    bad_path = tmp_path / "bad.db"
    SQLiteState(bad_path).initialize()
    with sqlite3.connect(bad_path) as connection:
        connection.execute("DROP TABLE agents")

    with pytest.raises(ValueError, match="state DB at .* is unreadable"):
        load_team_roster(bad_path)

    corrupt_path = tmp_path / "corrupt.db"
    _seed_state(corrupt_path)
    with sqlite3.connect(corrupt_path) as connection:
        connection.execute("UPDATE agents SET payload = ? WHERE agent_id = ?", ("{not-json", "planner"))

    with pytest.raises(ValueError, match="state DB at .* is unreadable"):
        load_team_roster(corrupt_path)


def test_build_runtime_context_sees_newly_added_agent_without_message_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    _seed_state(db_path)
    registry = AgentRegistry()
    for payload in SQLiteState(db_path).load_agents():
        registry.add(AgentRecord.from_dict(payload))
    registry.add(
        AgentRecord(
            agent_id="researcher",
            name="researcher",
            status=AgentStatus.STOPPED,
            persona="",
            role="research",
            runtime_spec=RuntimeSpec(
                image="maia-local/hermes-worker:latest",
                workspace="/opt/maia",
                command=[],
                env={},
            ),
        )
    )
    JsonRegistryStorage().save(db_path, registry)
    incoming = KeryxMessageRecord(
        message_id="msg-002",
        session_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind="request",
        body="Check current team context.",
        created_at="2026-04-17T02:04:00Z",
    )

    context = build_runtime_context(db_path, agent_id="reviewer", incoming_message=incoming)

    assert [entry.agent_id for entry in context.team_roster] == ["planner", "reviewer", "researcher"]
