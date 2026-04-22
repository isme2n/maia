from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxPendingWorkRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)
from maia.keryx_service import KeryxResourceNotFoundError, KeryxService, KeryxServiceError
from maia.keryx_storage import KeryxStorage
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
            speaking_style="casual",
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
    registry.add(
        AgentRecord(
            agent_id="archivist",
            name="archivist",
            status=AgentStatus.ARCHIVED,
            persona="",
            role="",
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
) -> KeryxMessageRecord:
    return KeryxMessageRecord(
        message_id=message_id,
        session_id=session_id,
        from_agent=from_agent,
        to_agent=to_agent,
        kind="request",
        body="Please review the Phase 1 patch.",
        created_at="2026-04-20T09:15:00Z",
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


def test_keryx_service_lists_roster_from_registry_and_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "maia.db"
    _seed_roster_state(db_path)

    roster = KeryxService(db_path).list_roster()

    assert [entry.agent_id for entry in roster] == ["planner", "reviewer", "archivist"]
    assert roster[0].to_dict() == {
        "agent_id": "planner",
        "name": "planner",
        "call_sign": "captain",
        "role": "planner",
        "speaking_style": "casual",
        "speaking_style_details": "",
        "persona": "",
        "status": "stopped",
        "setup_status": "complete",
        "runtime_status": "stopped",
    }
    assert roster[1].to_dict() == {
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
    }
    assert roster[2].to_dict() == {
        "agent_id": "archivist",
        "name": "archivist",
        "call_sign": "archivist",
        "role": "",
        "speaking_style": "respectful",
        "speaking_style_details": "",
        "persona": "",
        "status": "archived",
        "setup_status": "not-configured",
        "runtime_status": "stopped",
    }


def test_keryx_service_manages_sessions_messages_and_handoffs(tmp_path: Path) -> None:
    db_path = tmp_path / "maia.db"
    _seed_roster_state(db_path)
    service = KeryxService(db_path)

    session = _build_session()
    assert service.create_session(session) == session
    assert service.list_sessions() == [session]
    assert service.get_session(session.session_id) == session

    updated_session = _build_session(
        topic="Phase 1 review updated",
        participants=["planner", "reviewer", "archivist"],
        status=KeryxSessionStatus.IDLE,
        updated_at="2026-04-20T09:12:00Z",
    )
    assert service.update_session(session.session_id, updated_session) == updated_session
    assert service.get_session(updated_session.session_id) == updated_session

    assert service.list_session_messages(updated_session.session_id) == []
    message = _build_message(session_id=updated_session.session_id)
    assert service.create_session_message(updated_session.session_id, message) == message
    assert service.list_session_messages(updated_session.session_id) == [message]

    assert service.list_session_handoffs(updated_session.session_id) == []
    handoff = _build_handoff(session_id=updated_session.session_id)
    assert service.create_session_handoff(updated_session.session_id, handoff) == handoff
    assert service.list_session_handoffs(updated_session.session_id) == [handoff]
    assert (
        service.get_session_handoff(updated_session.session_id, handoff.handoff_id)
        == handoff
    )

    updated_handoff = _build_handoff(
        session_id=updated_session.session_id,
        status=KeryxHandoffStatus.ACCEPTED,
        summary="Accepted for merge.",
        updated_at="2026-04-20T09:35:00Z",
    )
    assert (
        service.update_session_handoff(
            updated_session.session_id,
            handoff.handoff_id,
            updated_handoff,
        )
        == updated_handoff
    )
    assert (
        service.get_session_handoff(
            updated_session.session_id,
            updated_handoff.handoff_id,
        )
        == updated_handoff
    )
    assert service.list_session_handoffs(updated_session.session_id) == [updated_handoff]


def test_keryx_service_lists_pending_work_from_open_handoffs(tmp_path: Path) -> None:
    db_path = tmp_path / "maia.db"
    _seed_roster_state(db_path)
    service = KeryxService(db_path)

    session = _build_session()
    service.create_session(session)
    message = _build_message(session_id=session.session_id)
    service.create_session_message(session.session_id, message)
    open_handoff = _build_handoff(
        session_id=session.session_id,
        from_agent="planner",
        to_agent="reviewer",
    )
    service.create_session_handoff(session.session_id, open_handoff)
    service.create_session_handoff(
        session.session_id,
        _build_handoff(
            handoff_id="handoff-closed",
            session_id=session.session_id,
            from_agent="planner",
            to_agent="reviewer",
            status=KeryxHandoffStatus.DONE,
        ),
    )

    assert service.list_pending_work("planner") == []
    assert service.list_pending_work("reviewer") == [
        KeryxPendingWorkRecord(session=session, message=message, handoff=open_handoff)
    ]


def test_keryx_service_raises_service_not_found_errors_for_missing_resources(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "maia.db"
    _seed_roster_state(db_path)
    KeryxStorage(db_path).create_session(_build_session())
    service = KeryxService(db_path)

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx session with id 'missing-session' not found",
    ) as missing_session:
        service.get_session("missing-session")

    assert isinstance(missing_session.value, KeryxServiceError)

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx session with id 'missing-session' not found",
    ):
        service.list_session_messages("missing-session")

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx session with id 'missing-session' not found",
    ):
        service.create_session_message(
            "missing-session",
            _build_message(session_id="missing-session"),
        )

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx session with id 'missing-session' not found",
    ):
        service.list_session_handoffs("missing-session")

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx session with id 'missing-session' not found",
    ):
        service.create_session_handoff(
            "missing-session",
            _build_handoff(session_id="missing-session"),
        )

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx session with id 'missing-session' not found",
    ):
        service.update_session(
            "missing-session",
            _build_session(session_id="missing-session"),
        )

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx handoff with id 'missing-handoff' not found",
    ):
        service.get_handoff("missing-handoff")

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx handoff with id 'missing-handoff' not found",
    ):
        service.update_handoff(
            "missing-handoff",
            _build_handoff(handoff_id="missing-handoff"),
        )

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx handoff with id 'missing-handoff' not found in session 'session-001'",
    ):
        service.get_session_handoff("session-001", "missing-handoff")

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx handoff with id 'missing-handoff' not found in session 'session-001'",
    ):
        service.update_session_handoff(
            "session-001",
            "missing-handoff",
            _build_handoff(
                handoff_id="missing-handoff",
                session_id="session-001",
            ),
        )


def test_keryx_service_scopes_handoff_get_and_update_to_the_route_session(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "maia.db"
    _seed_roster_state(db_path)
    service = KeryxService(db_path)

    primary_session = _build_session(session_id="session-001")
    secondary_session = _build_session(session_id="session-002")
    service.create_session(primary_session)
    service.create_session(secondary_session)

    handoff = _build_handoff(session_id=primary_session.session_id)
    service.create_session_handoff(primary_session.session_id, handoff)

    assert (
        service.get_session_handoff(primary_session.session_id, handoff.handoff_id)
        == handoff
    )

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx handoff with id 'handoff-001' not found in session 'session-002'",
    ):
        service.get_session_handoff(secondary_session.session_id, handoff.handoff_id)

    with pytest.raises(
        KeryxResourceNotFoundError,
        match="Keryx handoff with id 'handoff-001' not found in session 'session-002'",
    ):
        service.update_session_handoff(
            secondary_session.session_id,
            handoff.handoff_id,
            _build_handoff(
                handoff_id=handoff.handoff_id,
                session_id=secondary_session.session_id,
                status=KeryxHandoffStatus.DONE,
            ),
        )

    assert (
        service.get_session_handoff(primary_session.session_id, handoff.handoff_id)
        == handoff
    )


def test_keryx_service_rejects_route_id_mismatches_for_nested_resources(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "maia.db"
    _seed_roster_state(db_path)
    service = KeryxService(db_path)

    session = _build_session(session_id="session-001")
    service.create_session(session)
    handoff = _build_handoff(session_id=session.session_id)
    service.create_session_handoff(session.session_id, handoff)

    with pytest.raises(
        ValueError,
        match="Keryx session session_id must match route id 'session-001'",
    ):
        service.update_session(
            session.session_id,
            _build_session(session_id="session-002"),
        )

    with pytest.raises(
        ValueError,
        match="Keryx message session_id must match route id 'session-001'",
    ):
        service.create_session_message(
            session.session_id,
            _build_message(session_id="session-002"),
        )

    with pytest.raises(
        ValueError,
        match="Keryx handoff session_id must match route id 'session-001'",
    ):
        service.create_session_handoff(
            session.session_id,
            _build_handoff(session_id="session-002"),
        )

    with pytest.raises(
        ValueError,
        match="Keryx handoff session_id must match route id 'session-001'",
    ):
        service.update_session_handoff(
            session.session_id,
            handoff.handoff_id,
            _build_handoff(
                handoff_id=handoff.handoff_id,
                session_id="session-002",
            ),
        )

    with pytest.raises(
        ValueError,
        match="Keryx handoff handoff_id must match route id 'handoff-001'",
    ):
        service.update_session_handoff(
            session.session_id,
            handoff.handoff_id,
            _build_handoff(
                handoff_id="handoff-002",
                session_id=session.session_id,
            ),
        )
