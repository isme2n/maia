from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.keryx_models import (
    KeryxAgentSummary,
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)


def test_keryx_session_status_values() -> None:
    assert KeryxSessionStatus.ACTIVE.value == "active"
    assert KeryxSessionStatus.IDLE.value == "idle"
    assert KeryxSessionStatus.CLOSED.value == "closed"


def test_keryx_handoff_status_values() -> None:
    assert KeryxHandoffStatus.OPEN.value == "open"
    assert KeryxHandoffStatus.ACCEPTED.value == "accepted"
    assert KeryxHandoffStatus.DONE.value == "done"


def test_keryx_agent_summary_round_trip() -> None:
    summary = KeryxAgentSummary(
        agent_id="reviewer",
        name="reviewer",
        call_sign="r",
        role="reviewer",
        status="running",
        setup_status="complete",
        runtime_status="running",
    )

    restored = KeryxAgentSummary.from_dict(summary.to_dict())

    assert restored == summary
    assert restored.to_dict() == {
        "agent_id": "reviewer",
        "name": "reviewer",
        "call_sign": "r",
        "role": "reviewer",
        "status": "running",
        "setup_status": "complete",
        "runtime_status": "running",
    }


def test_keryx_agent_summary_from_dict_defaults_call_sign_and_role() -> None:
    restored = KeryxAgentSummary.from_dict(
        {
            "agent_id": "worker",
            "name": "worker",
            "status": "stopped",
            "setup_status": "incomplete",
            "runtime_status": "stopped",
        }
    )

    assert restored.call_sign == "worker"
    assert restored.role == ""
    assert restored.to_dict() == {
        "agent_id": "worker",
        "name": "worker",
        "call_sign": "worker",
        "role": "",
        "status": "stopped",
        "setup_status": "incomplete",
        "runtime_status": "stopped",
    }


def test_keryx_agent_summary_from_dict_rejects_empty_call_sign() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid Keryx agent summary call_sign: expected non-empty str",
    ):
        KeryxAgentSummary.from_dict(
            {
                "agent_id": "worker",
                "name": "worker",
                "call_sign": "",
                "status": "stopped",
                "setup_status": "incomplete",
                "runtime_status": "stopped",
            }
        )


def test_keryx_session_record_round_trip() -> None:
    record = KeryxSessionRecord(
        session_id="session-001",
        topic="Runtime rollout",
        participants=["planner", "reviewer"],
        created_by="planner",
        status=KeryxSessionStatus.ACTIVE,
        created_at="2026-04-20T10:00:00Z",
        updated_at="2026-04-20T10:05:00Z",
    )

    restored = KeryxSessionRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "session_id": "session-001",
        "topic": "Runtime rollout",
        "participants": ["planner", "reviewer"],
        "created_by": "planner",
        "status": "active",
        "created_at": "2026-04-20T10:00:00Z",
        "updated_at": "2026-04-20T10:05:00Z",
    }


def test_keryx_session_record_direct_construction_copies_participants() -> None:
    participants = ["planner", "reviewer"]

    record = KeryxSessionRecord(
        session_id="session-002",
        topic="Patch review",
        participants=participants,
        created_by="planner",
        status="idle",
        created_at="2026-04-20T11:00:00Z",
        updated_at="2026-04-20T11:10:00Z",
    )

    assert record.status is KeryxSessionStatus.IDLE
    assert record.participants is not participants

    participants.append("runner")

    assert record.participants == ["planner", "reviewer"]


def test_keryx_session_record_invalid_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid Keryx session status: 'paused'"):
        KeryxSessionRecord(
            session_id="session-003",
            topic="Bad status",
            participants=["planner"],
            created_by="planner",
            status="paused",
            created_at="2026-04-20T11:00:00Z",
            updated_at="2026-04-20T11:05:00Z",
        )


def test_keryx_session_record_invalid_participants_error() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid Keryx session participants: expected list of non-empty strings",
    ):
        KeryxSessionRecord.from_dict(
            {
                "session_id": "session-004",
                "topic": "Bad participants",
                "participants": ["planner", ""],
                "created_by": "planner",
                "status": "active",
                "created_at": "2026-04-20T11:00:00Z",
                "updated_at": "2026-04-20T11:05:00Z",
            }
        )


def test_keryx_message_record_round_trip_with_reply_to_message_id() -> None:
    record = KeryxMessageRecord(
        message_id="msg-001",
        session_id="session-001",
        from_agent="planner",
        to_agent="reviewer",
        kind="question",
        body="Can you review the rollout notes?",
        created_at="2026-04-20T10:01:00Z",
        reply_to_message_id="msg-000",
    )

    restored = KeryxMessageRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "message_id": "msg-001",
        "session_id": "session-001",
        "from_agent": "planner",
        "to_agent": "reviewer",
        "kind": "question",
        "body": "Can you review the rollout notes?",
        "created_at": "2026-04-20T10:01:00Z",
        "reply_to_message_id": "msg-000",
    }


def test_keryx_message_record_missing_required_fields_error() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"Invalid Keryx message record: missing required fields: "
            r"'body', 'created_at'"
        ),
    ):
        KeryxMessageRecord.from_dict(
            {
                "message_id": "msg-002",
                "session_id": "session-001",
                "from_agent": "planner",
                "to_agent": "reviewer",
                "kind": "request",
            }
        )


def test_keryx_message_record_invalid_kind_error() -> None:
    with pytest.raises(ValueError, match="Invalid Keryx message kind: expected str"):
        KeryxMessageRecord(
            message_id="msg-003",
            session_id="session-001",
            from_agent="planner",
            to_agent="reviewer",
            kind=["question"],
            body="This should fail.",
            created_at="2026-04-20T10:02:00Z",
        )


def test_keryx_handoff_record_round_trip() -> None:
    record = KeryxHandoffRecord(
        handoff_id="handoff-001",
        session_id="session-001",
        from_agent="planner",
        to_agent="reviewer",
        kind="repo-ref",
        status=KeryxHandoffStatus.OPEN,
        summary="Implementation is ready for review.",
        location="https://example.test/repo/commit/abc123",
        created_at="2026-04-20T10:10:00Z",
        updated_at="2026-04-20T10:10:00Z",
    )

    restored = KeryxHandoffRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "handoff_id": "handoff-001",
        "session_id": "session-001",
        "from_agent": "planner",
        "to_agent": "reviewer",
        "kind": "repo-ref",
        "status": "open",
        "summary": "Implementation is ready for review.",
        "location": "https://example.test/repo/commit/abc123",
        "created_at": "2026-04-20T10:10:00Z",
        "updated_at": "2026-04-20T10:10:00Z",
    }


def test_keryx_handoff_record_direct_construction_coerces_status_string() -> None:
    record = KeryxHandoffRecord(
        handoff_id="handoff-002",
        session_id="session-001",
        from_agent="reviewer",
        to_agent="planner",
        kind="report",
        status="accepted",
        summary="I have started the review.",
        location="/workspace/review.md",
        created_at="2026-04-20T10:15:00Z",
        updated_at="2026-04-20T10:20:00Z",
    )

    assert record.status is KeryxHandoffStatus.ACCEPTED


def test_keryx_handoff_record_invalid_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid Keryx handoff status: 'queued'"):
        KeryxHandoffRecord(
            handoff_id="handoff-003",
            session_id="session-001",
            from_agent="planner",
            to_agent="reviewer",
            kind="link",
            status="queued",
            summary="Bad status.",
            location="https://example.test/handoff",
            created_at="2026-04-20T10:15:00Z",
            updated_at="2026-04-20T10:15:00Z",
        )


def test_keryx_handoff_record_invalid_location_error() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid Keryx handoff location: expected str",
    ):
        KeryxHandoffRecord.from_dict(
            {
                "handoff_id": "handoff-004",
                "session_id": "session-001",
                "from_agent": "planner",
                "to_agent": "reviewer",
                "kind": "file",
                "status": "done",
                "summary": "Location must be a string pointer.",
                "location": {"path": "/workspace/output.txt"},
                "created_at": "2026-04-20T10:20:00Z",
                "updated_at": "2026-04-20T10:21:00Z",
            }
        )
