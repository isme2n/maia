from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.runtime_adapter import RuntimeStatus, RuntimeState
from maia.team_metadata import TeamMetadata
from maia.cli_init import (
    InitDependencies,
    derive_init_next_step,
    derive_init_runtime_status,
    format_init_output_lines,
    handle_init,
    init_runtime_start_capable,
    select_init_agent,
)


class _FakeRegistry:
    def __init__(self, records: list[AgentRecord]) -> None:
        self._records = {record.agent_id: record for record in records}

    def list(self) -> list[AgentRecord]:
        return list(self._records.values())

    def get(self, agent_id: str) -> AgentRecord:
        return self._records[agent_id]


class _FakeStorage:
    def __init__(self, registry: _FakeRegistry) -> None:
        self._registry = registry

    def load(self, state_path: Path | str) -> _FakeRegistry:
        return self._registry


def test_select_init_agent_prefers_team_default_over_name_sorting() -> None:
    alpha = AgentRecord(agent_id="agent-alpha", name="alpha")
    zeta = AgentRecord(agent_id="agent-zeta", name="zeta")
    archived = AgentRecord(agent_id="agent-archived", name="archived", status=AgentStatus.ARCHIVED)
    registry = _FakeRegistry([zeta, archived, alpha])
    metadata = TeamMetadata(
        team_name="",
        team_description="",
        team_tags=[],
        default_agent_id="agent-zeta",
    )

    selected, source = select_init_agent(registry, metadata)

    assert selected == zeta
    assert source == "default-agent"


def test_select_init_agent_falls_back_to_first_active_agent_when_default_is_missing() -> None:
    alpha = AgentRecord(agent_id="agent-alpha", name="alpha")
    zeta = AgentRecord(agent_id="agent-zeta", name="zeta")
    registry = _FakeRegistry([zeta, alpha])
    metadata = TeamMetadata(
        team_name="",
        team_description="",
        team_tags=[],
        default_agent_id="missing-agent",
    )

    selected, source = select_init_agent(registry, metadata)

    assert selected == alpha
    assert source == "first-active-agent"


def test_derive_init_runtime_status_defaults_to_not_started() -> None:
    assert derive_init_runtime_status(None) == "not-started"
    assert (
        derive_init_runtime_status(
            RuntimeState(
                agent_id="planner",
                runtime_status=RuntimeStatus.STOPPED,
                runtime_handle=None,
                setup_status="complete",
                gateway_setup_status="complete",
            )
        )
        == "stopped"
    )


def test_derive_init_next_step_prioritizes_runtime_transition_before_start() -> None:
    record = AgentRecord(agent_id="planner", name="planner")

    command, reason = derive_init_next_step(
        infra_ready=True,
        selected_agent=record,
        agent_setup_ready=True,
        gateway_ready=True,
        default_destination_ready=True,
        runtime_running=False,
        runtime_status=RuntimeStatus.STARTING.value,
    )

    assert command == "maia agent status planner"
    assert reason == "wait-for-runtime-transition"


def test_format_init_output_lines_uses_preview_formatter_consistently() -> None:
    report = {
        "infra_ready": True,
        "agent_identity_ready": True,
        "selected_agent_id": "agent-123",
        "selected_agent_name": "planner",
        "selected_agent_source": "sole-active-agent",
        "agent_setup_ready": True,
        "setup_status": "complete",
        "gateway_ready": True,
        "gateway_status": "complete",
        "default_destination_ready": True,
        "runtime_running": False,
        "runtime_status": "stopped",
        "conversation_ready": False,
        "next_command": "maia agent start planner",
        "next_reason": "start-agent-runtime",
    }

    lines = format_init_output_lines(report, format_preview_value=lambda value: f"<{value}>")

    assert lines == [
        "state name=infra_ready ready=yes",
        "state name=agent_identity_ready ready=yes agent_id=<agent-123> name=<planner> source=<sole-active-agent>",
        "state name=agent_setup_ready ready=yes status=<complete>",
        "state name=gateway_ready ready=yes status=<complete>",
        "state name=default_destination_ready ready=yes status=<complete>",
        "state name=runtime_running ready=no status=<stopped>",
        "state name=conversation_ready ready=no",
        "next command=<maia agent start planner> reason=<start-agent-runtime>",
    ]


def test_init_runtime_start_capable_requires_cli_and_daemon() -> None:
    assert init_runtime_start_capable(
        "/tmp/state.db",
        collect_doctor_checks=lambda state_path: [
            {"name": "docker_cli", "status": "ok"},
            {"name": "docker_daemon", "status": "ok"},
        ],
    )
    assert not init_runtime_start_capable(
        "/tmp/state.db",
        collect_doctor_checks=lambda state_path: [
            {"name": "docker_cli", "status": "ok"},
            {"name": "docker_daemon", "status": "missing"},
        ],
    )


def test_handle_init_orchestrates_existing_agent_to_ready_start_step(
    capsys: pytest.CaptureFixture[str],
) -> None:
    record = AgentRecord(agent_id="planner-id", name="planner")
    registry = _FakeRegistry([record])
    storage = _FakeStorage(registry)
    runtime_state = RuntimeState(
        agent_id="planner-id",
        runtime_status=RuntimeStatus.STOPPED,
        runtime_handle=None,
        setup_status="complete",
        gateway_setup_status="complete",
    )

    deps = InitDependencies(
        ensure_init_infra_ready=lambda state_path: True,
        init_infra_ready=lambda state_path: True,
        load_team_metadata=lambda path: TeamMetadata("", "", [], ""),
        select_init_agent=select_init_agent,
        create_agent_interactively=lambda storage, state_path, registry: (_ for _ in ()).throw(AssertionError("should not create agent")),
        format_created_agent_line=lambda record: f"created {record.name}",
        load_runtime_setup_state=lambda agent_id: runtime_state,
        derive_setup_state=lambda runtime_state: "complete",
        run_agent_setup_passthrough=lambda record: (_ for _ in ()).throw(AssertionError("should not rerun setup")),
        orchestrate_init_gateway_setup_if_needed=lambda record: None,
        init_runtime_start_capable=lambda state_path: False,
        build_runtime_adapter=lambda: object(),
        orchestrate_init_runtime_start_if_needed=lambda record, storage, state_path, registry, runtime_adapter: (_ for _ in ()).throw(AssertionError("should not start runtime")),
        resolve_runtime_state_for_init=lambda record, runtime_adapter, infra_ready: runtime_state,
        sync_registry_status_from_runtime_state=lambda record, runtime_state, storage, state_path, registry: record,
        derive_gateway_setup_state=lambda runtime_state: "complete",
        is_gateway_start_ready=lambda status: status in {"complete", "token-only"},
        is_default_destination_ready=lambda status: status == "complete",
        derive_init_runtime_status=derive_init_runtime_status,
        derive_init_next_step=derive_init_next_step,
        format_init_output_lines=lambda report, *, format_preview_value: format_init_output_lines(report, format_preview_value=format_preview_value),
        format_preview_value=lambda value: f"<{value}>",
    )

    exit_code = handle_init(
        storage,
        "/tmp/state.db",
        "/tmp/team.json",
        deps=deps,
    )

    assert exit_code == 1
    out_lines = capsys.readouterr().out.splitlines()
    assert out_lines[-1] == "next command=<maia agent start planner> reason=<start-agent-runtime>"
    assert "state name=agent_identity_ready ready=yes agent_id=<planner-id> name=<planner> source=<sole-active-agent>" in out_lines


def test_handle_init_preserves_setup_failure_exit_code_and_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    record = AgentRecord(agent_id="planner-id", name="planner")
    registry = _FakeRegistry([record])
    storage = _FakeStorage(registry)
    failed_setup_state = RuntimeState(
        agent_id="planner-id",
        runtime_status=RuntimeStatus.STOPPED,
        runtime_handle=None,
        setup_status="incomplete",
        gateway_setup_status="incomplete",
    )

    deps = InitDependencies(
        ensure_init_infra_ready=lambda state_path: True,
        init_infra_ready=lambda state_path: True,
        load_team_metadata=lambda path: TeamMetadata("", "", [], ""),
        select_init_agent=select_init_agent,
        create_agent_interactively=lambda storage, state_path, registry: (_ for _ in ()).throw(AssertionError("should not create agent")),
        format_created_agent_line=lambda record: f"created {record.name}",
        load_runtime_setup_state=lambda agent_id: failed_setup_state,
        derive_setup_state=lambda runtime_state: "incomplete" if runtime_state is not None else "not-started",
        run_agent_setup_passthrough=lambda record: (7, None, "broken Hermes setup"),
        orchestrate_init_gateway_setup_if_needed=lambda record: None,
        init_runtime_start_capable=lambda state_path: False,
        build_runtime_adapter=lambda: object(),
        orchestrate_init_runtime_start_if_needed=lambda record, storage, state_path, registry, runtime_adapter: (_ for _ in ()).throw(AssertionError("should not start runtime")),
        resolve_runtime_state_for_init=lambda record, runtime_adapter, infra_ready: failed_setup_state,
        sync_registry_status_from_runtime_state=lambda record, runtime_state, storage, state_path, registry: record,
        derive_gateway_setup_state=lambda runtime_state: "incomplete",
        is_gateway_start_ready=lambda status: status in {"complete", "token-only"},
        is_default_destination_ready=lambda status: status == "complete",
        derive_init_runtime_status=derive_init_runtime_status,
        derive_init_next_step=derive_init_next_step,
        format_init_output_lines=lambda report, *, format_preview_value: format_init_output_lines(report, format_preview_value=format_preview_value),
        format_preview_value=lambda value: value,
    )

    exit_code = handle_init(
        storage,
        "/tmp/state.db",
        "/tmp/team.json",
        deps=deps,
    )

    captured = capsys.readouterr()
    assert exit_code == 7
    assert "Agent setup failed for 'planner'. Rerun maia agent setup planner after fixing the Hermes setup issue. broken Hermes setup" in captured.err
    assert "next command=maia agent setup planner reason=finish-agent-setup" in captured.out
