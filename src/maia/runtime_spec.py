"""Runtime configuration model for Maia agents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self

__all__ = ["RuntimeSpec"]


def _validate_runtime_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Invalid runtime {field_name}: expected str")
    return value


def _validate_runtime_command(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(part, str) for part in value):
        raise ValueError("Invalid runtime command: expected list[str]")
    return list(value)


def _validate_runtime_env(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) or not isinstance(env_value, str)
        for key, env_value in value.items()
    ):
        raise ValueError("Invalid runtime env: expected mapping[str, str]")
    return dict(value)


@dataclass(slots=True)
class RuntimeSpec:
    """Serializable runtime configuration for an agent."""

    image: str
    workspace: str
    command: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Detach mutable constructor inputs from this instance."""

        self.image = _validate_runtime_str(self.image, field_name="image")
        self.workspace = _validate_runtime_str(self.workspace, field_name="workspace")
        self.command = _validate_runtime_command(self.command)
        self.env = _validate_runtime_env(self.env)

    def __copy__(self) -> Self:
        """Return an independent shallow copy of the runtime spec."""

        return type(self)(
            image=self.image,
            workspace=self.workspace,
            command=self.command,
            env=self.env,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the runtime spec into plain data."""

        return {
            "image": self.image,
            "workspace": self.workspace,
            "command": list(self.command),
            "env": dict(self.env),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a runtime spec from serialized data."""

        missing_fields = [
            field_name
            for field_name in ("image", "workspace", "command", "env")
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid runtime spec: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            image=data["image"],
            workspace=data["workspace"],
            command=data["command"],
            env=data["env"],
        )
