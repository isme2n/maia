from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.keryx_models import (
    KeryxDeliveryMode,
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)
from maia.keryx_storage import KeryxStorage


def _build_session(
    *,
    session_id: str = "session-001",
    topic: str = "Phase 1 review",
    participants: list[str] | None = None,
    status: KeryxSessionStatus = KeryxSessionStatus.ACTIVE,
    updated_at: str = "2026-04-19T09:00:00Z",
) -> KeryxSessionRecord:
    return KeryxSessionRecord(
        session_id=session_id,
        topic=topic,
        participants=list(participants or ["planner", "reviewer"]),
        created_by="planner",
        status=status,
        created_at="2026-04-19T08:55:00Z",
        updated_at=updated_at,
    )


def _build_message(
    *,
    message_id: str = "msg-001",
    session_id: str = "session-001",
    created_at: str = "2026-04-19T09:01:00Z",
    delivery_mode: KeryxDeliveryMode = KeryxDeliveryMode.AGENT_ONLY,
) -> KeryxMessageRecord:
    return KeryxMessageRecord(
        message_id=message_id,
        session_id=session_id,
        from_agent="planner",
        to_agent="reviewer",
        kind="request",
        body="Please review the Phase 1 storage patch.",
        created_at=created_at,
        delivery_mode=delivery_mode,
    )


def _build_handoff(
    *,
    handoff_id: str = "handoff-001",
    session_id: str = "session-001",
    status: KeryxHandoffStatus = KeryxHandoffStatus.OPEN,
    summary: str = "Review is ready.",
    updated_at: str = "2026-04-19T09:03:00Z",
) -> KeryxHandoffRecord:
    return KeryxHandoffRecord(
        handoff_id=handoff_id,
        session_id=session_id,
        from_agent="reviewer",
        to_agent="planner",
        kind="report",
        status=status,
        summary=summary,
        location="reports/review.md",
        created_at="2026-04-19T09:02:00Z",
        updated_at=updated_at,
    )


def test_keryx_storage_round_trips_phase1_records(tmp_path: Path) -> None:
    storage = KeryxStorage(tmp_path / "maia.db")
    session = _build_session()
    session_two = _build_session(
        session_id="session-002",
        topic="Follow-up",
        participants=["planner", "analyst"],
        updated_at="2026-04-19T09:10:00Z",
    )
    message = _build_message(delivery_mode=KeryxDeliveryMode.USER_DIRECT)
    handoff = _build_handoff()

    storage.create_session(session)
    storage.create_session(session_two)
    storage.create_message(message)
    storage.create_handoff(handoff)

    assert storage.list_sessions() == [session, session_two]
    assert storage.get_session(session.session_id) == session
    assert storage.list_messages(session_id=session.session_id) == [message]
    assert storage.list_messages(session_id=session.session_id)[0].delivery_mode is KeryxDeliveryMode.USER_DIRECT
    assert storage.list_handoffs(session_id=session.session_id) == [handoff]
    assert storage.get_handoff(handoff.handoff_id) == handoff


def test_keryx_storage_update_session_rewrites_membership(tmp_path: Path) -> None:
    path = tmp_path / "maia.db"
    storage = KeryxStorage(path)
    storage.create_session(_build_session())

    updated = _build_session(
        topic="Phase 1 review updated",
        participants=["planner", "analyst", "reviewer"],
        status=KeryxSessionStatus.IDLE,
        updated_at="2026-04-19T10:00:00Z",
    )

    result = storage.update_session(updated)

    assert result == updated
    assert storage.get_session(updated.session_id) == updated

    with sqlite3.connect(path) as connection:
        participant_rows = connection.execute(
            """
            SELECT position, participant_agent_id
            FROM keryx_session_participants
            WHERE session_id = ?
            ORDER BY position ASC
            """,
            (updated.session_id,),
        ).fetchall()

    assert participant_rows == [
        (0, "planner"),
        (1, "analyst"),
        (2, "reviewer"),
    ]


def test_keryx_storage_update_handoff_persists_new_status(tmp_path: Path) -> None:
    storage = KeryxStorage(tmp_path / "maia.db")
    storage.create_session(_build_session())
    storage.create_handoff(_build_handoff())

    updated = _build_handoff(
        status=KeryxHandoffStatus.ACCEPTED,
        summary="Accepted for merge.",
        updated_at="2026-04-19T09:15:00Z",
    )

    result = storage.update_handoff(updated)

    assert result == updated
    assert storage.get_handoff(updated.handoff_id) == updated
    assert storage.list_handoffs(session_id=updated.session_id) == [updated]


def test_keryx_storage_unfiltered_lists_are_ordered_by_created_at_then_id(
    tmp_path: Path,
) -> None:
    storage = KeryxStorage(tmp_path / "maia.db")
    session_one = _build_session(session_id="session-001")
    session_two = _build_session(session_id="session-002")
    storage.create_session(session_one)
    storage.create_session(session_two)

    later_message = _build_message(
        message_id="msg-002",
        session_id=session_one.session_id,
        created_at="2026-04-19T09:05:00Z",
    )
    earlier_message = _build_message(
        message_id="msg-001",
        session_id=session_two.session_id,
        created_at="2026-04-19T09:00:00Z",
    )
    same_time_later_id_handoff = _build_handoff(
        handoff_id="handoff-002",
        session_id=session_one.session_id,
        updated_at="2026-04-19T09:04:00Z",
    )
    same_time_earlier_id_handoff = _build_handoff(
        handoff_id="handoff-001",
        session_id=session_two.session_id,
        updated_at="2026-04-19T09:05:00Z",
    )

    storage.create_message(later_message)
    storage.create_message(earlier_message)
    storage.create_handoff(same_time_later_id_handoff)
    storage.create_handoff(same_time_earlier_id_handoff)

    assert storage.list_messages() == [earlier_message, later_message]
    assert storage.list_handoffs() == [
        same_time_earlier_id_handoff,
        same_time_later_id_handoff,
    ]


def test_keryx_storage_missing_records_and_session_updates_raise_lookup_error(
    tmp_path: Path,
) -> None:
    storage = KeryxStorage(tmp_path / "maia.db")

    assert storage.get_session("missing-session") is None
    assert storage.get_handoff("missing-handoff") is None

    with pytest.raises(LookupError, match="missing-session"):
        storage.create_message(_build_message(session_id="missing-session"))

    with pytest.raises(LookupError, match="missing-session"):
        storage.create_handoff(_build_handoff(session_id="missing-session"))

    storage.create_session(_build_session())

    with pytest.raises(LookupError, match="handoff-001"):
        storage.update_handoff(_build_handoff())

    with pytest.raises(LookupError, match="session-002"):
        storage.update_session(_build_session(session_id="session-002"))


def test_keryx_storage_keeps_minimal_message_api_surface() -> None:
    assert not hasattr(KeryxStorage, "get_message")
    assert not hasattr(KeryxStorage, "update_message")
