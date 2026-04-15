from __future__ import annotations

from copy import copy
from dataclasses import replace
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.runtime_spec import RuntimeSpec


def test_runtime_spec_round_trip() -> None:
    spec = RuntimeSpec(
        image="ghcr.io/example/reviewer:latest",
        workspace="/workspace/reviewer",
        command=["python", "-m", "reviewer"],
        env={"MAIA_ENV": "test", "MAIA_ROLE": "review"},
    )

    restored = RuntimeSpec.from_dict(spec.to_dict())

    assert restored == spec
    assert restored.to_dict() == {
        "image": "ghcr.io/example/reviewer:latest",
        "workspace": "/workspace/reviewer",
        "command": ["python", "-m", "reviewer"],
        "env": {"MAIA_ENV": "test", "MAIA_ROLE": "review"},
    }


def test_runtime_spec_missing_required_fields_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid runtime spec: missing required fields: 'command', 'env'",
    ):
        RuntimeSpec.from_dict(
            {
                "image": "ghcr.io/example/reviewer:latest",
                "workspace": "/workspace/reviewer",
            }
        )


def test_runtime_spec_invalid_env_error() -> None:
    with pytest.raises(ValueError, match=r"Invalid runtime env: expected mapping\[str, str\]"):
        RuntimeSpec.from_dict(
            {
                "image": "ghcr.io/example/reviewer:latest",
                "workspace": "/workspace/reviewer",
                "command": ["python", "-m", "reviewer"],
                "env": {"MAIA_ENV": 1},
            }
        )


def test_runtime_spec_invalid_command_error() -> None:
    with pytest.raises(ValueError, match=r"Invalid runtime command: expected list\[str\]"):
        RuntimeSpec.from_dict(
            {
                "image": "ghcr.io/example/reviewer:latest",
                "workspace": "/workspace/reviewer",
                "command": ["python", 3],
                "env": {"MAIA_ENV": "test"},
            }
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "error"),
    [
        ("image", 123, "Invalid runtime image: expected str"),
        ("workspace", 123, "Invalid runtime workspace: expected str"),
        ("command", ["python", 3], r"Invalid runtime command: expected list\[str\]"),
        ("env", {"MAIA_ENV": 1}, r"Invalid runtime env: expected mapping\[str, str\]"),
    ],
)
def test_runtime_spec_direct_construction_validates_fields(
    field_name: str,
    field_value: object,
    error: str,
) -> None:
    kwargs: dict[str, object] = {
        "image": "ghcr.io/example/reviewer:latest",
        "workspace": "/workspace/reviewer",
        "command": ["python", "-m", "reviewer"],
        "env": {"MAIA_ENV": "test"},
    }
    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=error):
        RuntimeSpec(**kwargs)


def test_runtime_spec_copies_do_not_alias_nested_mutables() -> None:
    spec = RuntimeSpec(
        image="ghcr.io/example/reviewer:latest",
        workspace="/workspace/reviewer",
        command=["python", "-m", "reviewer"],
        env={"MAIA_ENV": "test", "MAIA_ROLE": "review"},
    )

    copied = copy(spec)
    replaced = replace(spec, image="ghcr.io/example/reviewer:v2")

    assert copied is not spec
    assert copied.command is not spec.command
    assert copied.env is not spec.env
    assert replaced.command is not spec.command
    assert replaced.env is not spec.env

    copied.command.append("--debug")
    copied.env["MAIA_TRACE"] = "1"
    replaced.command.append("--audit")
    replaced.env["MAIA_ENV"] = "prod"

    assert spec.command == ["python", "-m", "reviewer"]
    assert spec.env == {"MAIA_ENV": "test", "MAIA_ROLE": "review"}
