from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.message_model import MessageKind, MessageRecord, ThreadRecord


def test_message_kind_values() -> None:
    assert MessageKind.REQUEST.value == "request"
    assert MessageKind.QUESTION.value == "question"
    assert MessageKind.ANSWER.value == "answer"
    assert MessageKind.REPORT.value == "report"
    assert MessageKind.HANDOFF.value == "handoff"
    assert MessageKind.NOTE.value == "note"


def test_thread_record_round_trip() -> None:
    record = ThreadRecord(
        thread_id="thread-001",
        topic="Runtime rollout",
        participants=["planner", "reviewer"],
        created_by="planner",
        status="open",
        created_at="2026-04-15T09:00:00Z",
        updated_at="2026-04-15T09:30:00Z",
    )

    restored = ThreadRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "thread_id": "thread-001",
        "topic": "Runtime rollout",
        "participants": ["planner", "reviewer"],
        "created_by": "planner",
        "status": "open",
        "created_at": "2026-04-15T09:00:00Z",
        "updated_at": "2026-04-15T09:30:00Z",
    }


def test_thread_record_direct_construction_copies_participants() -> None:
    participants = ["planner", "reviewer"]

    record = ThreadRecord(
        thread_id="thread-001a",
        topic="Runtime rollout",
        participants=participants,
        created_by="planner",
        status="open",
        created_at="2026-04-15T09:00:00Z",
        updated_at="2026-04-15T09:30:00Z",
    )

    assert record.participants is not participants

    participants.append("runner")

    assert record.participants == ["planner", "reviewer"]
    assert record.to_dict()["participants"] == ["planner", "reviewer"]


def test_message_record_round_trip_without_reply_to_message_id() -> None:
    record = MessageRecord(
        message_id="msg-001",
        thread_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind=MessageKind.QUESTION,
        body="Can you review the runtime contract?",
        created_at="2026-04-15T09:05:00Z",
    )

    restored = MessageRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.reply_to_message_id is None
    assert restored.to_dict() == {
        "message_id": "msg-001",
        "thread_id": "thread-001",
        "from_agent": "planner",
        "to_agent": "reviewer",
        "kind": "question",
        "body": "Can you review the runtime contract?",
        "created_at": "2026-04-15T09:05:00Z",
    }


def test_message_record_round_trip_with_reply_to_message_id() -> None:
    record = MessageRecord(
        message_id="msg-002",
        thread_id="thread-001",
        from_agent="reviewer",
        to_agent="planner",
        kind=MessageKind.ANSWER,
        body="Yes. I will send notes in 10 minutes.",
        created_at="2026-04-15T09:10:00Z",
        reply_to_message_id="msg-001",
    )

    restored = MessageRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "message_id": "msg-002",
        "thread_id": "thread-001",
        "from_agent": "reviewer",
        "to_agent": "planner",
        "kind": "answer",
        "body": "Yes. I will send notes in 10 minutes.",
        "created_at": "2026-04-15T09:10:00Z",
        "reply_to_message_id": "msg-001",
    }


def test_thread_record_invalid_participants_error() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid thread participants: expected list of non-empty strings",
    ):
        ThreadRecord.from_dict(
            {
                "thread_id": "thread-002",
                "topic": "Invalid participants",
                "participants": ["planner", ""],
                "created_by": "planner",
                "status": "open",
                "created_at": "2026-04-15T09:00:00Z",
                "updated_at": "2026-04-15T09:10:00Z",
            }
        )


def test_thread_record_rejects_non_list_participants() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid thread participants: expected list of non-empty strings",
    ):
        ThreadRecord.from_dict(
            {
                "thread_id": "thread-003",
                "topic": "Invalid participants type",
                "participants": "planner",
                "created_by": "planner",
                "status": "open",
                "created_at": "2026-04-15T09:00:00Z",
                "updated_at": "2026-04-15T09:10:00Z",
            }
        )


def test_message_record_invalid_kind_error() -> None:
    with pytest.raises(ValueError, match="Invalid message kind: 'broadcast'"):
        MessageRecord.from_dict(
            {
                "message_id": "msg-003",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "reviewer",
                "kind": "broadcast",
                "body": "This should fail.",
                "created_at": "2026-04-15T09:20:00Z",
            }
        )


def test_message_record_invalid_to_agent_error() -> None:
    with pytest.raises(ValueError, match="Invalid message to_agent: expected str"):
        MessageRecord.from_dict(
            {
                "message_id": "msg-004",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": ["reviewer", "runner"],
                "kind": "request",
                "body": "This should only target one agent.",
                "created_at": "2026-04-15T09:25:00Z",
            }
        )
