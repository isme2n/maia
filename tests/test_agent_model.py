from __future__ import annotations

from copy import copy
from dataclasses import replace
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.runtime_spec import RuntimeSpec


def test_agent_status_values() -> None:
    assert AgentStatus.RUNNING.value == "running"
    assert AgentStatus.STOPPED.value == "stopped"
    assert AgentStatus.ARCHIVED.value == "archived"


def test_agent_record_creation() -> None:
    record = AgentRecord(
        agent_id="agent-001",
        name="planner",
        status=AgentStatus.RUNNING,
        persona="careful",
    )

    assert record.agent_id == "agent-001"
    assert record.name == "planner"
    assert record.status is AgentStatus.RUNNING
    assert record.persona == "careful"
    assert record.role == ""
    assert record.model == ""
    assert record.tags == []
    assert record.runtime_spec is None
    assert record.messaging_spec is None


def test_agent_record_round_trip() -> None:
    record = AgentRecord(
        agent_id="agent-002",
        name="reviewer",
        status=AgentStatus.STOPPED,
        persona="strict",
    )

    restored = AgentRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "agent_id": "agent-002",
        "name": "reviewer",
        "status": "stopped",
        "persona": "strict",
    }


def test_agent_record_round_trip_with_runtime_and_messaging_spec() -> None:
    record = AgentRecord(
        agent_id="agent-004",
        name="runner",
        status=AgentStatus.RUNNING,
        persona="careful",
        role="executor",
        model="gpt-5.4",
        tags=["runtime", "queue"],
        runtime_spec=RuntimeSpec(
            image="ghcr.io/example/runner:latest",
            workspace="/workspaces/runner",
            command=["python", "-m", "runner"],
            env={"MAIA_MODE": "runtime"},
        ),
        messaging_spec={"broker": "rabbitmq", "queue": "runner.inbox"},
    )

    restored = AgentRecord.from_dict(record.to_dict())

    assert restored == record
    assert restored.to_dict() == {
        "agent_id": "agent-004",
        "name": "runner",
        "status": "running",
        "persona": "careful",
        "role": "executor",
        "model": "gpt-5.4",
        "tags": ["runtime", "queue"],
        "runtime_spec": {
            "image": "ghcr.io/example/runner:latest",
            "workspace": "/workspaces/runner",
            "command": ["python", "-m", "runner"],
            "env": {"MAIA_MODE": "runtime"},
        },
        "messaging_spec": {"broker": "rabbitmq", "queue": "runner.inbox"},
    }


def test_agent_record_from_dict_accepts_legacy_shape_without_extension_fields() -> None:
    payload = {
        "agent_id": "agent-005",
        "name": "legacy",
        "status": "stopped",
        "persona": "",
    }

    restored = AgentRecord.from_dict(payload)

    assert restored == AgentRecord(
        agent_id="agent-005",
        name="legacy",
        status=AgentStatus.STOPPED,
        persona="",
    )
    assert restored.to_dict() == payload


def test_agent_record_from_dict_accepts_extension_profile_fields_when_present() -> None:
    restored = AgentRecord.from_dict(
        {
            "agent_id": "agent-006",
            "name": "profiled",
            "status": "stopped",
            "persona": "strict",
            "role": "reviewer",
            "model": "gpt-5.4-mini",
            "tags": ["qa"],
        }
    )

    assert restored == AgentRecord(
        agent_id="agent-006",
        name="profiled",
        status=AgentStatus.STOPPED,
        persona="strict",
        role="reviewer",
        model="gpt-5.4-mini",
        tags=["qa"],
    )


def test_agent_record_invalid_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid agent status: 'paused'"):
        AgentRecord.from_dict(
            {
                "agent_id": "agent-003",
                "name": "runner",
                "status": "paused",
                "persona": "fast",
            }
        )


def test_agent_record_direct_construction_coerces_valid_status_string() -> None:
    record = AgentRecord(
        agent_id="agent-003a",
        name="runner",
        status="running",
        persona="fast",
    )

    assert record.status is AgentStatus.RUNNING
    assert record.to_dict()["status"] == "running"


def test_agent_record_direct_construction_rejects_invalid_status_type() -> None:
    with pytest.raises(ValueError, match="Invalid agent status: 1"):
        AgentRecord(
            agent_id="agent-003b",
            name="runner",
            status=1,
            persona="fast",
        )


def test_agent_record_direct_construction_rejects_invalid_status_value() -> None:
    with pytest.raises(ValueError, match="Invalid agent status: 'paused'"):
        AgentRecord(
            agent_id="agent-003c",
            name="runner",
            status="paused",
            persona="fast",
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "error"),
    [
        ("agent_id", 1, "Invalid agent agent_id: expected str"),
        ("name", 1, "Invalid agent name: expected str"),
        ("persona", 1, "Invalid agent persona: expected str"),
    ],
)
def test_agent_record_direct_construction_validates_core_identity_fields(
    field_name: str,
    field_value: object,
    error: str,
) -> None:
    kwargs: dict[str, object] = {
        "agent_id": "agent-003ca",
        "name": "runner",
        "status": AgentStatus.RUNNING,
        "persona": "fast",
    }
    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=error):
        AgentRecord(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "field_value", "error"),
    [
        ("agent_id", 1, "Invalid agent agent_id: expected str"),
        ("name", 1, "Invalid agent name: expected str"),
        ("persona", 1, "Invalid agent persona: expected str"),
    ],
)
def test_agent_record_from_dict_validates_core_identity_fields(
    field_name: str,
    field_value: object,
    error: str,
) -> None:
    payload: dict[str, object] = {
        "agent_id": "agent-003cb",
        "name": "runner",
        "status": "running",
        "persona": "fast",
    }
    payload[field_name] = field_value

    with pytest.raises(ValueError, match=error):
        AgentRecord.from_dict(payload)


@pytest.mark.parametrize(
    ("field_name", "field_value", "error"),
    [
        ("role", 1, "Invalid agent role: expected str"),
        ("model", 1, "Invalid agent model: expected str"),
        (
            "tags",
            ("runtime",),
            "Invalid agent tags: expected list of non-empty strings",
        ),
        (
            "tags",
            ["runtime", ""],
            "Invalid agent tags: expected list of non-empty strings",
        ),
    ],
)
def test_agent_record_direct_construction_validates_profile_fields(
    field_name: str,
    field_value: object,
    error: str,
) -> None:
    kwargs: dict[str, object] = {
        "agent_id": "agent-003d",
        "name": "runner",
        "status": AgentStatus.RUNNING,
        "persona": "fast",
        "role": "executor",
        "model": "gpt-5.4",
        "tags": ["runtime"],
    }
    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=error):
        AgentRecord(**kwargs)


def test_agent_record_direct_construction_accepts_serialized_extension_fields() -> None:
    runtime_spec_payload = {
        "image": "ghcr.io/example/runner:latest",
        "workspace": "/workspaces/runner",
        "command": ["python", "-m", "runner"],
        "env": {"MAIA_MODE": "runtime"},
    }
    messaging_spec_payload = {
        "transport": {"queue": "runner.inbox"},
        "routing": ["primary"],
    }

    record = AgentRecord(
        agent_id="agent-003e",
        name="runner",
        status="running",
        persona="fast",
        role="executor",
        model="gpt-5.4",
        tags=["runtime", "queue"],
        runtime_spec=runtime_spec_payload,
        messaging_spec=messaging_spec_payload,
    )

    assert record.runtime_spec == RuntimeSpec(
        image="ghcr.io/example/runner:latest",
        workspace="/workspaces/runner",
        command=["python", "-m", "runner"],
        env={"MAIA_MODE": "runtime"},
    )
    assert record.messaging_spec == {
        "transport": {"queue": "runner.inbox"},
        "routing": ["primary"],
    }
    assert record.to_dict() == {
        "agent_id": "agent-003e",
        "name": "runner",
        "status": "running",
        "persona": "fast",
        "role": "executor",
        "model": "gpt-5.4",
        "tags": ["runtime", "queue"],
        "runtime_spec": {
            "image": "ghcr.io/example/runner:latest",
            "workspace": "/workspaces/runner",
            "command": ["python", "-m", "runner"],
            "env": {"MAIA_MODE": "runtime"},
        },
        "messaging_spec": {
            "transport": {"queue": "runner.inbox"},
            "routing": ["primary"],
        },
    }

    runtime_spec_payload["command"].append("--debug")
    messaging_spec_payload["transport"]["queue"] = "runner.copy"

    assert record.runtime_spec is not None
    assert record.runtime_spec.command == ["python", "-m", "runner"]
    assert record.messaging_spec == {
        "transport": {"queue": "runner.inbox"},
        "routing": ["primary"],
    }


def test_agent_record_direct_construction_accepts_valid_runtime_spec_instance() -> None:
    runtime_spec = RuntimeSpec(
        image="ghcr.io/example/runner:latest",
        workspace="/workspaces/runner",
        command=["python", "-m", "runner"],
        env={"MAIA_MODE": "runtime"},
    )

    record = AgentRecord(
        agent_id="agent-003ea",
        name="runner",
        status=AgentStatus.RUNNING,
        persona="fast",
        runtime_spec=runtime_spec,
    )

    assert record.runtime_spec == runtime_spec
    assert record.runtime_spec is not runtime_spec
    assert record.to_dict() == {
        "agent_id": "agent-003ea",
        "name": "runner",
        "status": "running",
        "persona": "fast",
        "runtime_spec": {
            "image": "ghcr.io/example/runner:latest",
            "workspace": "/workspaces/runner",
            "command": ["python", "-m", "runner"],
            "env": {"MAIA_MODE": "runtime"},
        },
    }


def test_agent_record_direct_construction_revalidates_runtime_spec_instance() -> None:
    runtime_spec = RuntimeSpec(
        image="ghcr.io/example/runner:latest",
        workspace="/workspaces/runner",
        command=["python", "-m", "runner"],
        env={"MAIA_MODE": "runtime"},
    )
    runtime_spec.env["MAIA_MODE"] = 1

    with pytest.raises(ValueError, match=r"Invalid runtime env: expected mapping\[str, str\]"):
        AgentRecord(
            agent_id="agent-003eb",
            name="runner",
            status=AgentStatus.RUNNING,
            persona="fast",
            runtime_spec=runtime_spec,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "error"),
    [
        ("runtime_spec", "docker://runner", "Invalid agent runtime spec: expected object"),
        (
            "runtime_spec",
            {
                "image": "ghcr.io/example/runner:latest",
                "workspace": "/workspaces/runner",
                "command": ["python", "-m", "runner"],
                "env": {"MAIA_MODE": 1},
            },
            r"Invalid runtime env: expected mapping\[str, str\]",
        ),
        (
            "messaging_spec",
            ["runner.inbox"],
            "Invalid agent messaging spec: expected object",
        ),
        (
            "messaging_spec",
            {1: "runner.inbox"},
            "Invalid agent messaging spec: expected string keys",
        ),
    ],
)
def test_agent_record_direct_construction_validates_extension_specs(
    field_name: str,
    field_value: object,
    error: str,
) -> None:
    kwargs: dict[str, object] = {
        "agent_id": "agent-003f",
        "name": "runner",
        "status": AgentStatus.RUNNING,
        "persona": "fast",
        "runtime_spec": {
            "image": "ghcr.io/example/runner:latest",
            "workspace": "/workspaces/runner",
            "command": ["python", "-m", "runner"],
            "env": {"MAIA_MODE": "runtime"},
        },
        "messaging_spec": {"queue": "runner.inbox"},
    }
    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=error):
        AgentRecord(**kwargs)


def test_agent_record_invalid_runtime_spec_error() -> None:
    with pytest.raises(ValueError, match="Invalid agent runtime spec: expected object"):
        AgentRecord.from_dict(
            {
                "agent_id": "agent-007",
                "name": "runner",
                "status": "running",
                "persona": "fast",
                "runtime_spec": "docker://runner",
            }
        )


def test_agent_record_copies_do_not_alias_nested_mutables() -> None:
    record = AgentRecord(
        agent_id="agent-008",
        name="runner",
        status=AgentStatus.RUNNING,
        persona="careful",
        tags=["runtime", "queue"],
        runtime_spec=RuntimeSpec(
            image="ghcr.io/example/runner:latest",
            workspace="/workspaces/runner",
            command=["python", "-m", "runner"],
            env={"MAIA_MODE": "runtime"},
        ),
        messaging_spec={
            "transport": {"queue": "runner.inbox"},
            "routing": ["primary"],
        },
    )

    copied = copy(record)
    replaced = replace(record, name="runner-copy")

    assert copied is not record
    assert copied.tags is not record.tags
    assert copied.runtime_spec is not record.runtime_spec
    assert copied.runtime_spec is not None
    assert record.runtime_spec is not None
    assert copied.runtime_spec.command is not record.runtime_spec.command
    assert copied.runtime_spec.env is not record.runtime_spec.env
    assert copied.messaging_spec is not record.messaging_spec
    assert copied.messaging_spec["transport"] is not record.messaging_spec["transport"]
    assert copied.messaging_spec["routing"] is not record.messaging_spec["routing"]
    assert replaced.tags is not record.tags
    assert replaced.runtime_spec is not record.runtime_spec
    assert replaced.runtime_spec is not None
    assert replaced.runtime_spec.command is not record.runtime_spec.command
    assert replaced.runtime_spec.env is not record.runtime_spec.env
    assert replaced.messaging_spec is not record.messaging_spec
    assert replaced.messaging_spec["transport"] is not record.messaging_spec["transport"]
    assert replaced.messaging_spec["routing"] is not record.messaging_spec["routing"]

    copied.tags.append("copied")
    copied.runtime_spec.command.append("--debug")
    copied.runtime_spec.env["MAIA_TRACE"] = "1"
    copied.messaging_spec["transport"]["queue"] = "runner.copy"
    copied.messaging_spec["routing"].append("copy")
    replaced.tags.append("replaced")
    replaced.runtime_spec.command.append("--audit")
    replaced.runtime_spec.env["MAIA_MODE"] = "review"
    replaced.messaging_spec["transport"]["queue"] = "runner.replace"
    replaced.messaging_spec["routing"].append("replace")

    assert record.tags == ["runtime", "queue"]
    assert record.runtime_spec.command == ["python", "-m", "runner"]
    assert record.runtime_spec.env == {"MAIA_MODE": "runtime"}
    assert record.messaging_spec == {
        "transport": {"queue": "runner.inbox"},
        "routing": ["primary"],
    }
