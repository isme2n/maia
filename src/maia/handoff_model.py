"""Legacy handoff domain primitives for Maia.

These records remain only for non-active compatibility paths alongside the
Keryx-backed collaboration contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self

__all__ = ["HandoffKind", "HandoffRecord"]


def _validate_str(value: object, *, error: str) -> None:
    if not isinstance(value, str):
        raise ValueError(error)


class HandoffKind(str, Enum):
    """Supported handoff pointer types shared between agents."""

    FILE = "file"
    DIR = "dir"
    REPO_REF = "repo-ref"
    REPORT = "report"
    LINK = "link"


@dataclass(slots=True)
class HandoffRecord:
    """Legacy handoff metadata kept outside Maia's active Keryx thread contract."""

    handoff_id: str
    thread_id: str
    from_agent: str
    to_agent: str
    kind: HandoffKind
    location: str
    summary: str
    created_at: str

    def __post_init__(self) -> None:
        _validate_str(self.handoff_id, error="Invalid handoff id: expected str")
        _validate_str(self.thread_id, error="Invalid handoff thread_id: expected str")
        _validate_str(self.from_agent, error="Invalid handoff from_agent: expected str")
        _validate_str(self.to_agent, error="Invalid handoff to_agent: expected str")
        if not isinstance(self.kind, HandoffKind):
            raise ValueError("Invalid handoff kind: expected HandoffKind")
        _validate_str(self.location, error="Invalid handoff location: expected str")
        _validate_str(self.summary, error="Invalid handoff summary: expected str")
        _validate_str(self.created_at, error="Invalid handoff created_at: expected str")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the handoff record into plain data."""

        return {
            "handoff_id": self.handoff_id,
            "thread_id": self.thread_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "kind": self.kind.value,
            "location": self.location,
            "summary": self.summary,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a handoff record from serialized data."""

        missing_fields = [
            field_name
            for field_name in (
                "handoff_id",
                "thread_id",
                "from_agent",
                "to_agent",
                "kind",
                "location",
                "summary",
                "created_at",
            )
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid handoff record: missing required fields: "
                f"{missing_fields_text}"
            )

        raw_kind = data["kind"]
        try:
            kind = HandoffKind(raw_kind)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid handoff kind: {raw_kind!r}") from exc

        return cls(
            handoff_id=data["handoff_id"],
            thread_id=data["thread_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            kind=kind,
            location=data["location"],
            summary=data["summary"],
            created_at=data["created_at"],
        )
