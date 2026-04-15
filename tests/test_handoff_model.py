from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.handoff_model import HandoffKind, HandoffRecord


def test_handoff_kind_values() -> None:
    assert HandoffKind.FILE.value == "file"
    assert HandoffKind.DIR.value == "dir"
    assert HandoffKind.REPO_REF.value == "repo-ref"
    assert HandoffKind.REPORT.value == "report"
    assert HandoffKind.LINK.value == "link"


def test_handoff_record_round_trip() -> None:
    record = HandoffRecord(
        handoff_id="handoff-001",
        thread_id="thread-001",
        from_agent="planner",
        to_agent="worker",
        kind=HandoffKind.REPO_REF,
        location="https://example.test/repo/commit/abc123",
        summary="Implementation is ready for review.",
        created_at="2026-04-15T10:00:00Z",
    )

    restored = HandoffRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "handoff_id": "handoff-001",
        "thread_id": "thread-001",
        "from_agent": "planner",
        "to_agent": "worker",
        "kind": "repo-ref",
        "location": "https://example.test/repo/commit/abc123",
        "summary": "Implementation is ready for review.",
        "created_at": "2026-04-15T10:00:00Z",
    }


def test_handoff_record_missing_required_fields_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid handoff record: missing required fields: 'summary', 'created_at'",
    ):
        HandoffRecord.from_dict(
            {
                "handoff_id": "handoff-002",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "worker",
                "kind": "file",
                "location": "/workspace/output.txt",
            }
        )


def test_handoff_record_invalid_kind_error() -> None:
    with pytest.raises(ValueError, match="Invalid handoff kind: 'bundle'"):
        HandoffRecord.from_dict(
            {
                "handoff_id": "handoff-003",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "worker",
                "kind": "bundle",
                "location": "/workspace/output.txt",
                "summary": "Unsupported kind.",
                "created_at": "2026-04-15T10:05:00Z",
            }
        )


def test_handoff_record_invalid_location_error() -> None:
    with pytest.raises(ValueError, match="Invalid handoff location: expected str"):
        HandoffRecord.from_dict(
            {
                "handoff_id": "handoff-004",
                "thread_id": "thread-001",
                "from_agent": "planner",
                "to_agent": "worker",
                "kind": "link",
                "location": {"url": "https://example.test/report"},
                "summary": "Location must be a string pointer.",
                "created_at": "2026-04-15T10:10:00Z",
            }
        )
