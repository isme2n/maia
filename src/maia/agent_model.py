"""Agent domain model primitives for Maia."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Self

__all__ = ["AgentRecord", "AgentStatus"]


class AgentStatus(str, Enum):
    """Supported lifecycle states for an agent."""

    RUNNING = "running"
    STOPPED = "stopped"
    ARCHIVED = "archived"


@dataclass(slots=True)
class AgentRecord:
    """Minimal agent identity and configuration snapshot."""

    agent_id: str
    name: str
    status: AgentStatus
    persona: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the record into plain data."""

        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "persona": self.persona,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a record from serialized data."""

        raw_status = data["status"]
        try:
            status = AgentStatus(raw_status)
        except ValueError as exc:
            raise ValueError(f"Invalid agent status: {raw_status!r}") from exc

        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            status=status,
            persona=data["persona"],
        )
