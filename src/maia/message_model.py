"""Thread and message domain model primitives for Maia."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self

__all__ = ["MessageKind", "MessageRecord", "ThreadRecord"]


def _validate_str(value: object, *, error: str) -> None:
    if not isinstance(value, str):
        raise ValueError(error)


def _validate_optional_str(value: object, *, error: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ValueError(error)


def _validate_string_list(value: object, *, error: str) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ValueError(error)


class MessageKind(str, Enum):
    """Supported message types exchanged within a thread."""

    REQUEST = "request"
    QUESTION = "question"
    ANSWER = "answer"
    REPORT = "report"
    HANDOFF = "handoff"
    NOTE = "note"


@dataclass(slots=True)
class ThreadRecord:
    """Serializable collaboration thread metadata."""

    thread_id: str
    topic: str
    participants: list[str]
    created_by: str
    status: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        _validate_str(self.thread_id, error="Invalid thread id: expected str")
        _validate_str(self.topic, error="Invalid thread topic: expected str")
        _validate_string_list(
            self.participants,
            error="Invalid thread participants: expected list of non-empty strings",
        )
        self.participants = list(self.participants)
        _validate_str(self.created_by, error="Invalid thread creator: expected str")
        _validate_str(self.status, error="Invalid thread status: expected str")
        _validate_str(self.created_at, error="Invalid thread created_at: expected str")
        _validate_str(self.updated_at, error="Invalid thread updated_at: expected str")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the thread record into plain data."""

        return {
            "thread_id": self.thread_id,
            "topic": self.topic,
            "participants": list(self.participants),
            "created_by": self.created_by,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a thread record from serialized data."""

        missing_fields = [
            field_name
            for field_name in (
                "thread_id",
                "topic",
                "participants",
                "created_by",
                "status",
                "created_at",
                "updated_at",
            )
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid thread record: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            thread_id=data["thread_id"],
            topic=data["topic"],
            participants=data["participants"],
            created_by=data["created_by"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass(slots=True)
class MessageRecord:
    """Serializable message envelope stored within a thread."""

    message_id: str
    thread_id: str
    from_agent: str
    to_agent: str
    kind: MessageKind
    body: str
    created_at: str
    reply_to_message_id: str | None = None

    def __post_init__(self) -> None:
        _validate_str(self.message_id, error="Invalid message id: expected str")
        _validate_str(self.thread_id, error="Invalid message thread_id: expected str")
        _validate_str(self.from_agent, error="Invalid message from_agent: expected str")
        _validate_str(self.to_agent, error="Invalid message to_agent: expected str")
        if not isinstance(self.kind, MessageKind):
            raise ValueError("Invalid message kind: expected MessageKind")
        _validate_str(self.body, error="Invalid message body: expected str")
        _validate_str(self.created_at, error="Invalid message created_at: expected str")
        _validate_optional_str(
            self.reply_to_message_id,
            error="Invalid message reply_to_message_id: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the message record into plain data."""

        payload = {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "kind": self.kind.value,
            "body": self.body,
            "created_at": self.created_at,
        }
        if self.reply_to_message_id is not None:
            payload["reply_to_message_id"] = self.reply_to_message_id
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a message record from serialized data."""

        missing_fields = [
            field_name
            for field_name in (
                "message_id",
                "thread_id",
                "from_agent",
                "to_agent",
                "kind",
                "body",
                "created_at",
            )
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid message record: missing required fields: "
                f"{missing_fields_text}"
            )

        raw_kind = data["kind"]
        try:
            kind = MessageKind(raw_kind)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid message kind: {raw_kind!r}") from exc

        return cls(
            message_id=data["message_id"],
            thread_id=data["thread_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            kind=kind,
            body=data["body"],
            created_at=data["created_at"],
            reply_to_message_id=data.get("reply_to_message_id"),
        )
