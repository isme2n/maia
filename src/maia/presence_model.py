"""Presence domain model primitives for Maia."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self

__all__ = ["PresenceRecord", "PresenceStatus"]


def _validate_str(value: object, *, error: str) -> None:
    if not isinstance(value, str):
        raise ValueError(error)


def _validate_optional_str(value: object, *, error: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ValueError(error)


class PresenceStatus(str, Enum):
    """Supported runtime presence states for an agent."""

    RUNNING = "running"
    STOPPED = "stopped"


@dataclass(slots=True)
class PresenceRecord:
    """Serializable runtime presence metadata for an agent."""

    agent_id: str
    runtime_status: PresenceStatus
    last_heartbeat_at: str
    container_id: str | None = None

    def __post_init__(self) -> None:
        _validate_str(self.agent_id, error="Invalid presence agent_id: expected str")
        if not isinstance(self.runtime_status, PresenceStatus):
            raise ValueError("Invalid presence runtime_status: expected PresenceStatus")
        _validate_str(
            self.last_heartbeat_at,
            error="Invalid presence last_heartbeat_at: expected str",
        )
        _validate_optional_str(
            self.container_id,
            error="Invalid presence container_id: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the presence record into plain data."""

        payload = {
            "agent_id": self.agent_id,
            "runtime_status": self.runtime_status.value,
            "last_heartbeat_at": self.last_heartbeat_at,
        }
        if self.container_id is not None:
            payload["container_id"] = self.container_id
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a presence record from serialized data."""

        missing_fields = [
            field_name
            for field_name in ("agent_id", "runtime_status", "last_heartbeat_at")
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid presence record: missing required fields: "
                f"{missing_fields_text}"
            )

        raw_status = data["runtime_status"]
        try:
            runtime_status = PresenceStatus(raw_status)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid presence runtime_status: {raw_status!r}") from exc

        return cls(
            agent_id=data["agent_id"],
            runtime_status=runtime_status,
            last_heartbeat_at=data["last_heartbeat_at"],
            container_id=data.get("container_id"),
        )
