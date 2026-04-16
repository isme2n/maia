"""Agent domain model primitives for Maia."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from maia.runtime_spec import RuntimeSpec

__all__ = ["AgentRecord", "AgentSetupStatus", "AgentStatus"]


def _coerce_agent_status(value: object) -> "AgentStatus":
    try:
        return value if isinstance(value, AgentStatus) else AgentStatus(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid agent status: {value!r}") from exc


def _validate_agent_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Invalid agent {field_name}: expected str")
    return value


def _validate_agent_tags(value: object) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(tag, str) or not tag for tag in value
    ):
        raise ValueError("Invalid agent tags: expected list of non-empty strings")
    return list(value)


def _validate_agent_bool(value: object, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Invalid agent {field_name}: expected bool")
    return value


def _normalize_agent_runtime_spec(value: object) -> RuntimeSpec | None:
    if value is None:
        return None
    if isinstance(value, RuntimeSpec):
        return RuntimeSpec(
            image=value.image,
            workspace=value.workspace,
            command=value.command,
            env=value.env,
        )
    if not isinstance(value, Mapping):
        raise ValueError("Invalid agent runtime spec: expected object")
    return RuntimeSpec.from_dict(value)


def _normalize_agent_messaging_spec(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("Invalid agent messaging spec: expected object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError("Invalid agent messaging spec: expected string keys")
    return deepcopy(dict(value))


class AgentStatus(str, Enum):
    """Supported lifecycle states for an agent."""

    RUNNING = "running"
    STOPPED = "stopped"
    ARCHIVED = "archived"


class AgentSetupStatus(str, Enum):
    """Setup readiness states for an agent identity."""

    NOT_CONFIGURED = "not-configured"
    CONFIGURED = "configured"


def _coerce_agent_setup_status(value: object) -> "AgentSetupStatus":
    try:
        return value if isinstance(value, AgentSetupStatus) else AgentSetupStatus(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid agent setup status: {value!r}") from exc


@dataclass(slots=True)
class AgentRecord:
    """Minimal agent identity and configuration snapshot."""

    agent_id: str
    name: str
    call_sign: str = ""
    status: AgentStatus = AgentStatus.STOPPED
    setup_status: AgentSetupStatus = AgentSetupStatus.NOT_CONFIGURED
    has_started: bool = False
    persona: str = ""
    role: str = ""
    model: str = ""
    tags: list[str] = field(default_factory=list)
    runtime_spec: RuntimeSpec | None = None
    messaging_spec: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Detach mutable constructor inputs from this instance."""

        self.agent_id = _validate_agent_str(self.agent_id, field_name="agent_id")
        self.name = _validate_agent_str(self.name, field_name="name")
        self.call_sign = _validate_agent_str(
            self.call_sign or self.name,
            field_name="call_sign",
        )
        self.status = _coerce_agent_status(self.status)
        self.setup_status = _coerce_agent_setup_status(self.setup_status)
        self.has_started = _validate_agent_bool(self.has_started, field_name="has_started")
        self.persona = _validate_agent_str(self.persona, field_name="persona")
        self.role = _validate_agent_str(self.role, field_name="role")
        self.model = _validate_agent_str(self.model, field_name="model")
        self.tags = _validate_agent_tags(self.tags)
        self.runtime_spec = _normalize_agent_runtime_spec(self.runtime_spec)
        if self.runtime_spec is not None and self.setup_status is AgentSetupStatus.NOT_CONFIGURED:
            self.setup_status = AgentSetupStatus.CONFIGURED
        self.messaging_spec = _normalize_agent_messaging_spec(self.messaging_spec)

    def __copy__(self) -> Self:
        """Return an independent shallow copy of the agent record."""

        return type(self)(
            agent_id=self.agent_id,
            name=self.name,
            call_sign=self.call_sign,
            status=self.status,
            setup_status=self.setup_status,
            has_started=self.has_started,
            persona=self.persona,
            role=self.role,
            model=self.model,
            tags=self.tags,
            runtime_spec=self.runtime_spec,
            messaging_spec=self.messaging_spec,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record into plain data."""

        payload = {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "persona": self.persona,
        }
        if self.call_sign != self.name:
            payload["call_sign"] = self.call_sign
        if self.setup_status is not AgentSetupStatus.NOT_CONFIGURED:
            payload["setup_status"] = self.setup_status.value
        if self.has_started:
            payload["has_started"] = True
        if self.role:
            payload["role"] = self.role
        if self.model:
            payload["model"] = self.model
        if self.tags:
            payload["tags"] = list(self.tags)
        if self.runtime_spec is not None:
            payload["runtime_spec"] = self.runtime_spec.to_dict()
        if self.messaging_spec is not None:
            payload["messaging_spec"] = deepcopy(dict(self.messaging_spec))
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a record from serialized data."""

        role = _validate_agent_str(data.get("role", ""), field_name="role")
        model = _validate_agent_str(data.get("model", ""), field_name="model")
        tags = _validate_agent_tags(data.get("tags", []))
        runtime_spec = _normalize_agent_runtime_spec(data.get("runtime_spec"))
        messaging_spec = _normalize_agent_messaging_spec(data.get("messaging_spec"))
        setup_status = data.get("setup_status")
        if setup_status is None:
            setup_status = (
                AgentSetupStatus.CONFIGURED.value
                if runtime_spec is not None
                else AgentSetupStatus.NOT_CONFIGURED.value
            )

        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            call_sign=data.get("call_sign", data["name"]),
            status=data["status"],
            setup_status=setup_status,
            has_started=data.get("has_started", False),
            persona=data["persona"],
            role=role,
            model=model,
            tags=list(tags),
            runtime_spec=runtime_spec,
            messaging_spec=messaging_spec,
        )
