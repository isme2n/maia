"""Runtime adapter contract primitives for Maia agent lifecycle."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from maia.agent_model import AgentRecord

__all__ = [
    "RuntimeAdapter",
    "RuntimeLogsRequest",
    "RuntimeLogsResult",
    "RuntimeStartRequest",
    "RuntimeStartResult",
    "RuntimeState",
    "RuntimeStatus",
    "RuntimeStatusRequest",
    "RuntimeStatusResult",
    "RuntimeStopRequest",
    "RuntimeStopResult",
]


def _validate_str(value: object, *, error: str) -> None:
    if not isinstance(value, str):
        raise ValueError(error)


def _validate_optional_str(value: object, *, error: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ValueError(error)


def _validate_tail_lines(value: object) -> int:
    if not isinstance(value, int) or value < 1:
        raise ValueError("Invalid runtime logs request tail_lines: expected int >= 1")
    return value


def _validate_log_lines(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("Invalid runtime logs result lines: expected list[str]")
    return list(value)


def _parse_runtime_status(value: object) -> "RuntimeStatus":
    try:
        return value if isinstance(value, RuntimeStatus) else RuntimeStatus(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid runtime status: {value!r}") from exc


def _load_agent_record(data: object, *, error: str) -> AgentRecord:
    if not isinstance(data, Mapping):
        raise ValueError(error)
    return AgentRecord.from_dict(data)


def _load_runtime_state(data: object, *, error: str) -> "RuntimeState":
    if not isinstance(data, Mapping):
        raise ValueError(error)
    return RuntimeState.from_dict(data)


class RuntimeStatus(str, Enum):
    """Runtime lifecycle states surfaced by adapter operations."""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(slots=True)
class RuntimeState:
    """Observed runtime state for a Maia agent."""

    agent_id: str
    runtime_status: RuntimeStatus
    runtime_handle: str | None = None
    setup_status: str | None = None
    gateway_setup_status: str | None = None

    def __post_init__(self) -> None:
        _validate_str(self.agent_id, error="Invalid runtime state agent_id: expected str")
        if not isinstance(self.runtime_status, RuntimeStatus):
            raise ValueError("Invalid runtime state runtime_status: expected RuntimeStatus")
        _validate_optional_str(
            self.runtime_handle,
            error="Invalid runtime state runtime_handle: expected str",
        )
        _validate_optional_str(
            self.setup_status,
            error="Invalid runtime state setup_status: expected str",
        )
        _validate_optional_str(
            self.gateway_setup_status,
            error="Invalid runtime state gateway_setup_status: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the runtime state into plain data."""

        payload = {
            "agent_id": self.agent_id,
            "runtime_status": self.runtime_status.value,
        }
        if self.runtime_handle is not None:
            payload["runtime_handle"] = self.runtime_handle
        if self.setup_status is not None:
            payload["setup_status"] = self.setup_status
        if self.gateway_setup_status is not None:
            payload["gateway_setup_status"] = self.gateway_setup_status
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a runtime state from serialized data."""

        missing_fields = [
            field_name
            for field_name in ("agent_id", "runtime_status")
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime state: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            agent_id=data["agent_id"],
            runtime_status=_parse_runtime_status(data["runtime_status"]),
            runtime_handle=data.get("runtime_handle"),
            setup_status=data.get("setup_status"),
            gateway_setup_status=data.get("gateway_setup_status"),
        )


@dataclass(slots=True)
class RuntimeStartRequest:
    """Request to start an agent runtime from a registry snapshot."""

    agent: AgentRecord

    def __post_init__(self) -> None:
        if not isinstance(self.agent, AgentRecord):
            raise ValueError("Invalid runtime start request agent: expected AgentRecord")
        self.agent = copy(self.agent)
        if self.agent.runtime_spec is None:
            raise ValueError(
                "Invalid runtime start request agent runtime_spec: expected RuntimeSpec"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the start request into plain data."""

        return {"agent": self.agent.to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a start request from serialized data."""

        missing_fields = [
            field_name for field_name in ("agent",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime start request: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            agent=_load_agent_record(
                data["agent"],
                error="Invalid runtime start request agent: expected object",
            )
        )


@dataclass(slots=True)
class RuntimeStopRequest:
    """Request to stop an agent runtime."""

    agent_id: str
    runtime_handle: str | None = None

    def __post_init__(self) -> None:
        _validate_str(self.agent_id, error="Invalid runtime stop request agent_id: expected str")
        _validate_optional_str(
            self.runtime_handle,
            error="Invalid runtime stop request runtime_handle: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the stop request into plain data."""

        payload = {"agent_id": self.agent_id}
        if self.runtime_handle is not None:
            payload["runtime_handle"] = self.runtime_handle
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a stop request from serialized data."""

        missing_fields = [
            field_name for field_name in ("agent_id",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime stop request: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            agent_id=data["agent_id"],
            runtime_handle=data.get("runtime_handle"),
        )


@dataclass(slots=True)
class RuntimeStatusRequest:
    """Request to inspect an agent runtime."""

    agent_id: str

    def __post_init__(self) -> None:
        _validate_str(
            self.agent_id,
            error="Invalid runtime status request agent_id: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the status request into plain data."""

        return {"agent_id": self.agent_id}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a status request from serialized data."""

        missing_fields = [
            field_name for field_name in ("agent_id",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime status request: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(agent_id=data["agent_id"])


@dataclass(slots=True)
class RuntimeLogsRequest:
    """Request to fetch recent runtime log lines for an agent."""

    agent_id: str
    tail_lines: int = 100

    def __post_init__(self) -> None:
        _validate_str(self.agent_id, error="Invalid runtime logs request agent_id: expected str")
        self.tail_lines = _validate_tail_lines(self.tail_lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the logs request into plain data."""

        return {
            "agent_id": self.agent_id,
            "tail_lines": self.tail_lines,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a logs request from serialized data."""

        missing_fields = [
            field_name for field_name in ("agent_id",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime logs request: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            agent_id=data["agent_id"],
            tail_lines=data.get("tail_lines", 100),
        )


@dataclass(slots=True)
class RuntimeStartResult:
    """Result of a runtime start request."""

    runtime: RuntimeState

    def __post_init__(self) -> None:
        if not isinstance(self.runtime, RuntimeState):
            raise ValueError("Invalid runtime start result runtime: expected RuntimeState")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the start result into plain data."""

        return {"runtime": self.runtime.to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a start result from serialized data."""

        missing_fields = [
            field_name for field_name in ("runtime",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime start result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            runtime=_load_runtime_state(
                data["runtime"],
                error="Invalid runtime start result runtime: expected object",
            )
        )


@dataclass(slots=True)
class RuntimeStopResult:
    """Result of a runtime stop request."""

    runtime: RuntimeState

    def __post_init__(self) -> None:
        if not isinstance(self.runtime, RuntimeState):
            raise ValueError("Invalid runtime stop result runtime: expected RuntimeState")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the stop result into plain data."""

        return {"runtime": self.runtime.to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a stop result from serialized data."""

        missing_fields = [
            field_name for field_name in ("runtime",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime stop result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            runtime=_load_runtime_state(
                data["runtime"],
                error="Invalid runtime stop result runtime: expected object",
            )
        )


@dataclass(slots=True)
class RuntimeStatusResult:
    """Result of a runtime status request."""

    runtime: RuntimeState

    def __post_init__(self) -> None:
        if not isinstance(self.runtime, RuntimeState):
            raise ValueError("Invalid runtime status result runtime: expected RuntimeState")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the status result into plain data."""

        return {"runtime": self.runtime.to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a status result from serialized data."""

        missing_fields = [
            field_name for field_name in ("runtime",) if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime status result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            runtime=_load_runtime_state(
                data["runtime"],
                error="Invalid runtime status result runtime: expected object",
            )
        )


@dataclass(slots=True)
class RuntimeLogsResult:
    """Result of a runtime logs request."""

    runtime: RuntimeState
    lines: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.runtime, RuntimeState):
            raise ValueError("Invalid runtime logs result runtime: expected RuntimeState")
        self.lines = _validate_log_lines(self.lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the logs result into plain data."""

        return {
            "runtime": self.runtime.to_dict(),
            "lines": list(self.lines),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a logs result from serialized data."""

        missing_fields = [
            field_name
            for field_name in ("runtime", "lines")
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime logs result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            runtime=_load_runtime_state(
                data["runtime"],
                error="Invalid runtime logs result runtime: expected object",
            ),
            lines=data["lines"],
        )


class RuntimeAdapter(ABC):
    """Abstract contract for Maia's runtime plane."""

    @abstractmethod
    def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        """Start an agent runtime."""

    @abstractmethod
    def stop(self, request: RuntimeStopRequest) -> RuntimeStopResult:
        """Stop an agent runtime."""

    @abstractmethod
    def status(self, request: RuntimeStatusRequest) -> RuntimeStatusResult:
        """Inspect the current runtime state for an agent."""

    @abstractmethod
    def logs(self, request: RuntimeLogsRequest) -> RuntimeLogsResult:
        """Fetch recent runtime log lines for an agent."""
