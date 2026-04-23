"""Agent domain model primitives for Maia."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from maia.runtime_spec import RuntimeSpec

__all__ = ["AgentRecord", "AgentSetupStatus", "AgentStatus", "SpeakingStyle"]


class SpeakingStyle(str, Enum):
    """Supported agent speaking-style presets."""

    RESPECTFUL = "respectful"
    CASUAL = "casual"
    CUSTOM = "custom"


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


def _coerce_speaking_style(value: object) -> "SpeakingStyle":
    try:
        return value if isinstance(value, SpeakingStyle) else SpeakingStyle(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(repr(style.value) for style in SpeakingStyle)
        raise ValueError(
            f"Invalid agent speaking_style: expected one of {allowed}; got {value!r}"
        ) from exc


def _normalize_speaking_style_details(value: object, *, style: SpeakingStyle) -> str:
    details = _validate_agent_str(value, field_name="speaking_style_details")
    return details if style is SpeakingStyle.CUSTOM else ""


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
    speaking_style: SpeakingStyle = SpeakingStyle.RESPECTFUL
    speaking_style_details: str = ""
    persona: str = ""
    role: str = ""
    model: str = ""
    tags: list[str] = field(default_factory=list)
    runtime_spec: RuntimeSpec | None = None

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
        self.speaking_style = _coerce_speaking_style(self.speaking_style)
        self.speaking_style_details = _normalize_speaking_style_details(
            self.speaking_style_details,
            style=self.speaking_style,
        )
        self.persona = _validate_agent_str(self.persona, field_name="persona")
        self.role = _validate_agent_str(self.role, field_name="role")
        self.model = _validate_agent_str(self.model, field_name="model")
        self.tags = _validate_agent_tags(self.tags)
        self.runtime_spec = _normalize_agent_runtime_spec(self.runtime_spec)
        if self.runtime_spec is not None and self.setup_status is AgentSetupStatus.NOT_CONFIGURED:
            self.setup_status = AgentSetupStatus.CONFIGURED

    def __copy__(self) -> Self:
        """Return an independent shallow copy of the agent record."""

        return type(self)(
            agent_id=self.agent_id,
            name=self.name,
            call_sign=self.call_sign,
            status=self.status,
            setup_status=self.setup_status,
            has_started=self.has_started,
            speaking_style=self.speaking_style,
            speaking_style_details=self.speaking_style_details,
            persona=self.persona,
            role=self.role,
            model=self.model,
            tags=self.tags,
            runtime_spec=self.runtime_spec,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record into plain data."""

        payload = {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "speaking_style": self.speaking_style.value,
            "persona": self.persona,
        }
        if self.call_sign != self.name:
            payload["call_sign"] = self.call_sign
        if self.setup_status is not AgentSetupStatus.NOT_CONFIGURED:
            payload["setup_status"] = self.setup_status.value
        if self.has_started:
            payload["has_started"] = True
        if self.speaking_style is SpeakingStyle.CUSTOM and self.speaking_style_details:
            payload["speaking_style_details"] = self.speaking_style_details
        if self.role:
            payload["role"] = self.role
        if self.model:
            payload["model"] = self.model
        if self.tags:
            payload["tags"] = list(self.tags)
        if self.runtime_spec is not None:
            payload["runtime_spec"] = self.runtime_spec.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a record from serialized data."""

        role = _validate_agent_str(data.get("role", ""), field_name="role")
        model = _validate_agent_str(data.get("model", ""), field_name="model")
        tags = _validate_agent_tags(data.get("tags", []))
        runtime_spec = _normalize_agent_runtime_spec(data.get("runtime_spec"))
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
            speaking_style=data.get("speaking_style", SpeakingStyle.RESPECTFUL.value),
            speaking_style_details=data.get("speaking_style_details", ""),
            persona=data["persona"],
            role=role,
            model=model,
            tags=list(tags),
            runtime_spec=runtime_spec,
        )
