"""Read-only runtime context helpers for Maia agents.

Active collaboration context comes from Keryx-backed thread data stored in
Maia's SQLite state DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Any

from maia.agent_model import AgentRecord
from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxThreadMessageView,
)
from maia.runtime_adapter import RuntimeState, RuntimeStatus

__all__ = [
    "AgentRosterEntry",
    "HandoffContext",
    "RuntimeContext",
    "ThreadContext",
    "build_runtime_context",
    "format_runtime_context_for_prompt",
    "load_recent_handoffs",
    "load_team_roster",
    "load_thread_context",
]


@dataclass(slots=True)
class AgentRosterEntry:
    agent_id: str
    name: str
    role: str
    call_sign: str
    status: str
    setup_status: str
    runtime_status: str


@dataclass(slots=True)
class ThreadContext:
    thread_id: str
    topic: str
    participants: list[str]
    pending_on: str
    recent_message_ids: list[str]


@dataclass(slots=True)
class HandoffContext:
    handoff_id: str
    from_agent: str
    to_agent: str
    kind: str
    summary: str
    location: str
    created_at: str


@dataclass(slots=True)
class RuntimeContext:
    self_agent: AgentRosterEntry
    team_roster: list[AgentRosterEntry]
    thread_context: ThreadContext | None
    recent_handoffs: list[HandoffContext]


def load_team_roster(state_db_path: str | Path) -> list[AgentRosterEntry]:
    path = _validate_state_db_path(state_db_path)
    agents = _load_payload_rows(path, table="agents", order_by="position ASC")
    runtime_states = {
        state.agent_id: state for state in _load_runtime_states(path)
    }
    roster: list[AgentRosterEntry] = []
    for payload in agents:
        record = AgentRecord.from_dict(payload)
        runtime_state = runtime_states.get(record.agent_id)
        roster.append(
            AgentRosterEntry(
                agent_id=record.agent_id,
                name=record.name,
                role=record.role,
                call_sign=record.call_sign,
                status=record.status.value,
                setup_status=(runtime_state.setup_status if runtime_state and runtime_state.setup_status else "unknown"),
                runtime_status=(runtime_state.runtime_status.value if runtime_state else RuntimeStatus.STOPPED.value),
            )
        )
    return roster


def load_thread_context(state_db_path: str | Path, thread_id: str) -> ThreadContext | None:
    path = _validate_state_db_path(state_db_path)
    keryx_thread = _load_keryx_thread(path, thread_id)
    if keryx_thread is None:
        return None
    messages = _load_keryx_messages(path, thread_id)
    sorted_messages = sorted(messages, key=lambda item: (item.created_at, item.message_id))
    pending_on = sorted_messages[-1].to_agent if sorted_messages else "-"
    recent_message_ids = [item.message_id for item in sorted_messages[-5:]]
    return ThreadContext(
        thread_id=keryx_thread.thread_id,
        topic=keryx_thread.topic,
        participants=list(keryx_thread.participants),
        pending_on=pending_on,
        recent_message_ids=recent_message_ids,
    )


def load_recent_handoffs(
    state_db_path: str | Path,
    *,
    thread_id: str,
    limit: int = 3,
) -> list[HandoffContext]:
    path = _validate_state_db_path(state_db_path)
    if _load_keryx_thread(path, thread_id) is None:
        return []
    handoffs = _load_keryx_handoffs(path, thread_id)
    ordered = sorted(handoffs, key=lambda item: (item.created_at, item.handoff_id), reverse=True)
    return [
        HandoffContext(
            handoff_id=item.handoff_id,
            from_agent=item.from_agent,
            to_agent=item.to_agent,
            kind=item.kind,
            summary=item.summary,
            location=item.location,
            created_at=item.created_at,
        )
        for item in ordered[:limit]
    ]


def build_runtime_context(
    state_db_path: str | Path,
    *,
    agent_id: str,
    incoming_message: KeryxMessageRecord | KeryxThreadMessageView,
) -> RuntimeContext:
    roster = load_team_roster(state_db_path)
    try:
        self_agent = next(item for item in roster if item.agent_id == agent_id)
    except StopIteration as exc:
        raise ValueError(f"agent {agent_id!r} is missing from Maia state DB") from exc
    thread_context = load_thread_context(state_db_path, incoming_message.thread_id)
    recent_handoffs = load_recent_handoffs(
        state_db_path,
        thread_id=incoming_message.thread_id,
        limit=3,
    )
    return RuntimeContext(
        self_agent=self_agent,
        team_roster=roster,
        thread_context=thread_context,
        recent_handoffs=recent_handoffs,
    )


def format_runtime_context_for_prompt(context: RuntimeContext) -> str:
    roster_lines = [
        f"  - {entry.name} (agent_id={entry.agent_id}, role={entry.role or '-'}, runtime={entry.runtime_status})"
        for entry in context.team_roster
    ] or ["  - -"]
    lines = [
        "Current Maia context:",
        "- Known team roster:",
        *roster_lines,
    ]
    if context.thread_context is None:
        lines.extend(
            [
                "- Active thread:",
                "  - unavailable",
            ]
        )
    else:
        lines.extend(
            [
                "- Active thread:",
                f"  - thread_id={context.thread_context.thread_id}",
                f"  - topic={context.thread_context.topic or '-'}",
                f"  - participants={','.join(context.thread_context.participants) if context.thread_context.participants else '-'}",
                f"  - pending_on={context.thread_context.pending_on}",
            ]
        )
    lines.append("- Recent handoffs for this thread:")
    if context.recent_handoffs:
        for handoff in context.recent_handoffs:
            lines.append(
                "  - "
                f"handoff_id={handoff.handoff_id} "
                f"type={handoff.kind} from={handoff.from_agent} to={handoff.to_agent} "
                f"summary={handoff.summary} location={handoff.location}"
            )
    else:
        lines.append("  - -")
    return "\n".join(lines)


def _validate_state_db_path(state_db_path: str | Path) -> Path:
    path = Path(state_db_path)
    if not path.exists():
        raise ValueError(f"state DB at {path} is missing")
    return path


def _load_runtime_states(path: Path) -> list[RuntimeState]:
    return [
        RuntimeState.from_dict(payload)
        for payload in _load_payload_rows(path, table="runtime_states", order_by="agent_id ASC")
    ]


def _load_keryx_thread(path: Path, thread_id: str) -> KeryxSessionRecord | None:
    payloads = _load_json_payload_rows(
        path,
        query="SELECT payload FROM keryx_sessions WHERE session_id = ?",
        parameters=(thread_id,),
    )
    if not payloads:
        return None
    participants = _load_text_rows(
        path,
        query=(
            "SELECT participant_agent_id FROM keryx_session_participants "
            "WHERE session_id = ? ORDER BY position ASC"
        ),
        parameters=(thread_id,),
    )
    return KeryxSessionRecord.from_dict({**payloads[0], "participants": participants})


def _load_keryx_messages(path: Path, thread_id: str) -> list[KeryxMessageRecord]:
    return [
        KeryxMessageRecord.from_dict(payload)
        for payload in _load_json_payload_rows(
            path,
            query=(
                "SELECT payload FROM keryx_messages "
                "WHERE session_id = ? ORDER BY created_at ASC, message_id ASC"
            ),
            parameters=(thread_id,),
        )
    ]


def _load_keryx_handoffs(path: Path, thread_id: str) -> list[KeryxHandoffRecord]:
    return [
        KeryxHandoffRecord.from_dict(payload)
        for payload in _load_json_payload_rows(
            path,
            query=(
                "SELECT payload FROM keryx_handoffs "
                "WHERE session_id = ? ORDER BY created_at ASC, handoff_id ASC"
            ),
            parameters=(thread_id,),
        )
    ]


def _load_payload_rows(path: Path, *, table: str, order_by: str) -> list[dict[str, Any]]:
    return _load_json_payload_rows(
        path,
        query=f"SELECT payload FROM {table} ORDER BY {order_by}",
    )


def _load_json_payload_rows(
    path: Path,
    *,
    query: str,
    parameters: tuple[object, ...] = (),
) -> list[dict[str, Any]]:
    try:
        with _connect_read_only(path) as connection:
            rows = connection.execute(query, parameters).fetchall()
        payloads: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row[0])
            if not isinstance(payload, dict):
                raise ValueError("payload must decode to an object")
            payloads.append(payload)
    except (sqlite3.Error, OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"state DB at {path} is unreadable") from exc
    return payloads


def _load_text_rows(
    path: Path,
    *,
    query: str,
    parameters: tuple[object, ...] = (),
) -> list[str]:
    try:
        with _connect_read_only(path) as connection:
            rows = connection.execute(query, parameters).fetchall()
    except (sqlite3.Error, OSError) as exc:
        raise ValueError(f"state DB at {path} is unreadable") from exc
    values: list[str] = []
    for row in rows:
        if not isinstance(row[0], str):
            raise ValueError(f"state DB at {path} is unreadable")
        values.append(row[0])
    return values


def _connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
