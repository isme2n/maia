from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.collaboration_storage import CollaborationState, CollaborationStorage
from maia.handoff_model import HandoffKind, HandoffRecord
from maia.message_model import MessageKind, MessageRecord, ThreadRecord


def _build_thread() -> ThreadRecord:
    return ThreadRecord(
        thread_id="thread-001",
        topic="runtime review",
        participants=["planner", "reviewer"],
        created_by="planner",
        status="open",
        created_at="2026-04-15T12:00:00Z",
        updated_at="2026-04-15T12:00:00Z",
    )


def _build_message(message_id: str = "msg-001") -> MessageRecord:
    return MessageRecord(
        message_id=message_id,
        thread_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind=MessageKind.REQUEST,
        body="please review phase 3",
        created_at="2026-04-15T12:00:00Z",
    )


def _build_handoff() -> HandoffRecord:
    return HandoffRecord(
        handoff_id="handoff-001",
        thread_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind=HandoffKind.REPORT,
        location="/tmp/reports/runtime-review.md",
        summary="Review notes are ready.",
        created_at="2026-04-15T12:05:00Z",
    )


def test_collaboration_storage_round_trip_without_handoffs(tmp_path: Path) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"

    storage.save(
        path,
        threads=[_build_thread()],
        messages=[_build_message()],
    )

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "threads": [
            {
                "thread_id": "thread-001",
                "topic": "runtime review",
                "participants": ["planner", "reviewer"],
                "created_by": "planner",
                "status": "open",
                "created_at": "2026-04-15T12:00:00Z",
                "updated_at": "2026-04-15T12:00:00Z",
            }
        ],
        "messages": [
            {
                "message_id": "msg-001",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "reviewer",
                "kind": "request",
                "body": "please review phase 3",
                "created_at": "2026-04-15T12:00:00Z",
            }
        ],
        "handoffs": [],
    }

    restored = storage.load(path)
    assert restored == CollaborationState(
        threads=[_build_thread()],
        messages=[_build_message()],
        handoffs=[],
    )


def test_collaboration_storage_round_trip_with_handoffs(tmp_path: Path) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"

    storage.save(
        path,
        threads=[_build_thread()],
        messages=[_build_message()],
        handoffs=[_build_handoff()],
    )

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "threads": [
            {
                "thread_id": "thread-001",
                "topic": "runtime review",
                "participants": ["planner", "reviewer"],
                "created_by": "planner",
                "status": "open",
                "created_at": "2026-04-15T12:00:00Z",
                "updated_at": "2026-04-15T12:00:00Z",
            }
        ],
        "messages": [
            {
                "message_id": "msg-001",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "reviewer",
                "kind": "request",
                "body": "please review phase 3",
                "created_at": "2026-04-15T12:00:00Z",
            }
        ],
        "handoffs": [
            {
                "handoff_id": "handoff-001",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "reviewer",
                "kind": "report",
                "location": "/tmp/reports/runtime-review.md",
                "summary": "Review notes are ready.",
                "created_at": "2026-04-15T12:05:00Z",
            }
        ],
    }

    restored = storage.load(path)
    assert restored == CollaborationState(
        threads=[_build_thread()],
        messages=[_build_message()],
        handoffs=[_build_handoff()],
    )


def test_collaboration_storage_missing_file_returns_empty_state(tmp_path: Path) -> None:
    storage = CollaborationStorage()

    restored = storage.load(tmp_path / "missing.json")

    assert restored == CollaborationState(threads=[], messages=[], handoffs=[])


def test_collaboration_storage_missing_handoffs_defaults_to_empty_list(
    tmp_path: Path,
) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"
    path.write_text(
        json.dumps(
            {
                "threads": [_build_thread().to_dict()],
                "messages": [_build_message().to_dict()],
            }
        ),
        encoding="utf-8",
    )

    restored = storage.load(path)

    assert restored == CollaborationState(
        threads=[_build_thread()],
        messages=[_build_message()],
        handoffs=[],
    )


def test_collaboration_storage_invalid_json_raises_clear_error(tmp_path: Path) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid collaboration JSON"):
        storage.load(path)


def test_collaboration_storage_invalid_thread_record_raises_clear_error(tmp_path: Path) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"
    path.write_text(json.dumps({"threads": [{}], "messages": []}), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"Invalid collaboration JSON.*thread record at index 0 is invalid",
    ):
        storage.load(path)


def test_collaboration_storage_invalid_message_record_raises_clear_error(tmp_path: Path) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"
    path.write_text(json.dumps({"threads": [], "messages": [{}]}), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"Invalid collaboration JSON.*message record at index 0 is invalid",
    ):
        storage.load(path)


def test_collaboration_storage_invalid_handoff_record_raises_clear_error(
    tmp_path: Path,
) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"
    path.write_text(
        json.dumps({"threads": [], "messages": [], "handoffs": [{}]}),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"Invalid collaboration JSON.*handoff record at index 0 is invalid",
    ):
        storage.load(path)


def test_collaboration_storage_save_preserves_existing_handoffs_when_omitted(
    tmp_path: Path,
) -> None:
    storage = CollaborationStorage()
    path = tmp_path / "collaboration.json"
    storage.save(
        path,
        threads=[_build_thread()],
        messages=[_build_message()],
        handoffs=[_build_handoff()],
    )

    storage.save(
        path,
        threads=[_build_thread()],
        messages=[_build_message("msg-002")],
    )

    restored = storage.load(path)

    assert restored.handoffs == [_build_handoff()]
    assert restored.messages == [_build_message("msg-002")]
