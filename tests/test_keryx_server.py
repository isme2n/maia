from __future__ import annotations

import json
import sys
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.keryx_models import (
    KeryxDeliveryMode,
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)
from maia.keryx_server import KeryxHttpServer, create_keryx_http_server
from maia.registry import AgentRegistry
from maia.runtime_adapter import RuntimeState, RuntimeStatus
from maia.runtime_spec import RuntimeSpec
from maia.runtime_state_storage import RuntimeStateStorage
from maia.storage import JsonRegistryStorage


def _build_runtime_spec() -> RuntimeSpec:
    return RuntimeSpec(
        image="maia-local/hermes-worker:latest",
        workspace="/opt/maia",
        command=[],
        env={},
    )


def _seed_roster_state(db_path: Path) -> None:
    registry = AgentRegistry()
    registry.add(
        AgentRecord(
            agent_id="planner",
            name="planner",
            call_sign="captain",
            status=AgentStatus.STOPPED,
            persona="",
            role="planner",
            runtime_spec=_build_runtime_spec(),
        )
    )
    registry.add(
        AgentRecord(
            agent_id="reviewer",
            name="reviewer",
            status=AgentStatus.RUNNING,
            persona="",
            role="reviewer",
            runtime_spec=_build_runtime_spec(),
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
                gateway_setup_status="complete",
            ),
            "reviewer": RuntimeState(
                agent_id="reviewer",
                runtime_status=RuntimeStatus.RUNNING,
                runtime_handle="runtime-001",
                setup_status="incomplete",
                gateway_setup_status="incomplete",
            ),
        },
    )


def _build_session(
    *,
    session_id: str = "session-001",
    topic: str = "Phase 1 review",
    participants: list[str] | None = None,
    status: KeryxSessionStatus = KeryxSessionStatus.ACTIVE,
    updated_at: str = "2026-04-20T09:10:00Z",
) -> KeryxSessionRecord:
    return KeryxSessionRecord(
        session_id=session_id,
        topic=topic,
        participants=list(participants or ["planner", "reviewer"]),
        created_by="planner",
        status=status,
        created_at="2026-04-20T09:00:00Z",
        updated_at=updated_at,
    )


def _build_message(
    *,
    message_id: str = "msg-001",
    session_id: str = "session-001",
    from_agent: str = "planner",
    to_agent: str = "reviewer",
    delivery_mode: KeryxDeliveryMode = KeryxDeliveryMode.AGENT_ONLY,
) -> KeryxMessageRecord:
    return KeryxMessageRecord(
        message_id=message_id,
        session_id=session_id,
        from_agent=from_agent,
        to_agent=to_agent,
        kind="request",
        body="Please review the Phase 1 patch.",
        created_at="2026-04-20T09:15:00Z",
        delivery_mode=delivery_mode,
    )


def _build_handoff(
    *,
    handoff_id: str = "handoff-001",
    session_id: str = "session-001",
    from_agent: str = "reviewer",
    to_agent: str = "planner",
    status: KeryxHandoffStatus = KeryxHandoffStatus.OPEN,
    summary: str = "Review requested.",
    updated_at: str = "2026-04-20T09:25:00Z",
) -> KeryxHandoffRecord:
    return KeryxHandoffRecord(
        handoff_id=handoff_id,
        session_id=session_id,
        from_agent=from_agent,
        to_agent=to_agent,
        kind="report",
        status=status,
        summary=summary,
        location="reports/review.md",
        created_at="2026-04-20T09:20:00Z",
        updated_at=updated_at,
    )


@pytest.fixture
def running_server(tmp_path: Path) -> Iterator[KeryxHttpServer]:
    db_path = tmp_path / "state.db"
    _seed_roster_state(db_path)
    server = create_keryx_http_server(state_db_path=db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _request(
    server: KeryxHttpServer,
    method: str,
    path: str,
    payload: object | None = None,
) -> tuple[int, object]:
    connection = HTTPConnection(server.server_address[0], server.server_address[1])
    body: bytes | None = None
    headers: dict[str, str] = {}
    if payload is not None:
        if isinstance(payload, bytes):
            body = payload
        else:
            body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body))
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    raw_body = response.read()
    connection.close()
    decoded_body = json.loads(raw_body.decode("utf-8"))
    return response.status, decoded_body


def test_keryx_http_server_exposes_phase1_json_routes(
    running_server: KeryxHttpServer,
) -> None:
    status, payload = _request(running_server, "GET", "/agents")
    assert status == 200
    assert payload == [
        {
            "agent_id": "planner",
            "name": "planner",
            "call_sign": "captain",
            "role": "planner",
            "speaking_style": "respectful",
            "speaking_style_details": "",
            "persona": "",
            "status": "stopped",
            "setup_status": "complete",
            "runtime_status": "stopped",
        },
        {
            "agent_id": "reviewer",
            "name": "reviewer",
            "call_sign": "reviewer",
            "role": "reviewer",
            "speaking_style": "respectful",
            "speaking_style_details": "",
            "persona": "",
            "status": "running",
            "setup_status": "incomplete",
            "runtime_status": "running",
        },
    ]

    status, payload = _request(running_server, "GET", "/agents/reviewer/pending-work")
    assert status == 200
    assert payload == []

    session = _build_session().to_dict()
    status, payload = _request(running_server, "POST", "/sessions", session)
    assert status == 201
    assert payload == session

    status, payload = _request(running_server, "GET", "/sessions")
    assert status == 200
    assert payload == [session]

    status, payload = _request(running_server, "GET", "/sessions/session-001")
    assert status == 200
    assert payload == session

    updated_session = _build_session(
        topic="Phase 1 review updated",
        participants=["planner", "reviewer", "archivist"],
        status=KeryxSessionStatus.IDLE,
        updated_at="2026-04-20T09:12:00Z",
    ).to_dict()
    status, payload = _request(
        running_server,
        "PATCH",
        "/sessions/session-001",
        updated_session,
    )
    assert status == 200
    assert payload == updated_session

    status, payload = _request(
        running_server,
        "GET",
        "/sessions/session-001/messages",
    )
    assert status == 200
    assert payload == []

    message = _build_message(delivery_mode=KeryxDeliveryMode.USER_DIRECT).to_dict()
    status, payload = _request(
        running_server,
        "POST",
        "/sessions/session-001/messages",
        message,
    )
    assert status == 201
    assert payload == message

    status, payload = _request(
        running_server,
        "GET",
        "/sessions/session-001/messages",
    )
    assert status == 200
    assert payload == [message]

    status, payload = _request(
        running_server,
        "GET",
        "/sessions/session-001/handoffs",
    )
    assert status == 200
    assert payload == []

    handoff = _build_handoff(from_agent="planner", to_agent="reviewer").to_dict()
    status, payload = _request(
        running_server,
        "POST",
        "/sessions/session-001/handoffs",
        handoff,
    )
    assert status == 201
    assert payload == handoff

    status, payload = _request(
        running_server,
        "GET",
        "/sessions/session-001/handoffs",
    )
    assert status == 200
    assert payload == [handoff]

    status, payload = _request(running_server, "GET", "/handoffs/handoff-001")
    assert status == 200
    assert payload == handoff

    status, payload = _request(running_server, "GET", "/agents/reviewer/pending-work")
    assert status == 200
    assert payload == [
        {
            "session": updated_session,
            "message": message,
            "handoff": handoff,
        }
    ]

    updated_handoff = _build_handoff(
        from_agent="planner",
        to_agent="reviewer",
        status=KeryxHandoffStatus.ACCEPTED,
        summary="Accepted for merge.",
        updated_at="2026-04-20T09:35:00Z",
    ).to_dict()
    status, payload = _request(
        running_server,
        "PATCH",
        "/handoffs/handoff-001",
        updated_handoff,
    )
    assert status == 200
    assert payload == updated_handoff


def test_keryx_http_server_returns_404_for_unknown_routes_and_resources(
    running_server: KeryxHttpServer,
) -> None:
    status, payload = _request(running_server, "GET", "/missing")
    assert status == 404
    assert payload == {"error": "Route not found"}

    status, payload = _request(running_server, "GET", "/sessions/session-404")
    assert status == 404
    assert payload == {
        "error": "Keryx session with id 'session-404' not found",
    }


def test_keryx_http_server_returns_400_for_invalid_json_and_id_mismatch(
    running_server: KeryxHttpServer,
) -> None:
    status, payload = _request(running_server, "POST", "/sessions", b"{bad json")
    assert status == 400
    assert payload == {"error": "Request body is not valid JSON"}

    session = _build_session().to_dict()
    status, payload = _request(running_server, "POST", "/sessions", session)
    assert status == 201

    updated_session = dict(session)
    updated_session["session_id"] = "session-002"
    status, payload = _request(
        running_server,
        "PATCH",
        "/sessions/session-001",
        updated_session,
    )
    assert status == 400
    assert payload == {
        "error": "Keryx session session_id must match route id 'session-001'",
    }

    invalid_message = _build_message().to_dict()
    invalid_message["delivery_mode"] = "broadcast"
    status, payload = _request(
        running_server,
        "POST",
        "/sessions/session-001/messages",
        invalid_message,
    )
    assert status == 400
    assert payload == {
        "error": (
            "Invalid Keryx message delivery_mode: expected one of "
            "'agent_only', 'user_direct'; got 'broadcast'"
        )
    }
