"""Helpers for Maia's canonical `maia init` flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import sys

from maia import infra_runtime
from maia.agent_model import AgentRecord, AgentStatus
from maia.cli_bootstrap import format_setup_step_line, is_doctor_failure
from maia.runtime_adapter import RuntimeStatus, RuntimeState
from maia.team_metadata import TeamMetadata

__all__ = [
    "InitDependencies",
    "derive_init_next_step",
    "derive_init_runtime_status",
    "ensure_init_infra_ready",
    "format_init_output_lines",
    "handle_init",
    "init_infra_ready",
    "init_runtime_start_capable",
    "select_init_agent",
]


@dataclass(slots=True)
class InitDependencies:
    ensure_init_infra_ready: Callable[[Path | str], bool]
    init_infra_ready: Callable[[Path | str], bool]
    load_team_metadata: Callable[[Path | str], TeamMetadata]
    select_init_agent: Callable[[object, TeamMetadata], tuple[AgentRecord | None, str]]
    create_agent_interactively: Callable[[object, Path | str, object], AgentRecord]
    format_created_agent_line: Callable[[AgentRecord], str]
    load_runtime_setup_state: Callable[[str], RuntimeState | None]
    derive_setup_state: Callable[[RuntimeState | None], str]
    run_agent_setup_passthrough: Callable[[AgentRecord], tuple[int, object | None, str | None]]
    orchestrate_init_gateway_setup_if_needed: Callable[[AgentRecord], int | None]
    init_runtime_start_capable: Callable[[Path | str], bool]
    build_runtime_adapter: Callable[[], object]
    orchestrate_init_runtime_start_if_needed: Callable[[AgentRecord, object, Path | str, object, object], tuple[bool, str | None]]
    resolve_runtime_state_for_init: Callable[[AgentRecord, object, bool], RuntimeState | None]
    sync_registry_status_from_runtime_state: Callable[[AgentRecord, RuntimeState, object, Path | str, object], AgentRecord]
    derive_gateway_setup_state: Callable[[RuntimeState | None], str]
    is_gateway_start_ready: Callable[[str | None], bool]
    is_default_destination_ready: Callable[[str | None], bool]
    derive_init_runtime_status: Callable[[RuntimeState | None], str]
    derive_init_next_step: Callable[..., tuple[str, str]]
    format_init_output_lines: Callable[..., list[str]]
    format_preview_value: Callable[[str], str]


def select_init_agent(
    registry,
    team_metadata: TeamMetadata,
) -> tuple[AgentRecord | None, str]:
    active_records = [
        record for record in registry.list() if record.status is not AgentStatus.ARCHIVED
    ]
    if not active_records:
        return None, "none"
    default_agent_id = team_metadata.default_agent_id.strip()
    if default_agent_id:
        try:
            default_record = registry.get(default_agent_id)
        except LookupError:
            default_record = None
        if default_record is not None and default_record.status is not AgentStatus.ARCHIVED:
            return default_record, "default-agent"
    ordered_records = sorted(active_records, key=lambda record: (record.name, record.agent_id))
    if len(ordered_records) == 1:
        return ordered_records[0], "sole-active-agent"
    return ordered_records[0], "first-active-agent"


def init_infra_ready(state_path: Path | str) -> bool:
    checks = infra_runtime.collect_doctor_checks(state_path)
    return not any(is_doctor_failure(check) for check in checks)


def ensure_init_infra_ready(state_path: Path | str) -> bool:
    if init_infra_ready(state_path):
        return True
    try:
        steps = infra_runtime.bootstrap_shared_infra(state_path)
    except ValueError:
        return False
    for step in steps:
        print(format_setup_step_line(step))
    return init_infra_ready(state_path)


def init_runtime_start_capable(
    state_path: Path | str,
    *,
    collect_doctor_checks: Callable[[Path | str], list[dict[str, str]]] | None = None,
) -> bool:
    doctor_checks = (
        infra_runtime.collect_doctor_checks if collect_doctor_checks is None else collect_doctor_checks
    )
    check_status_by_name = {check["name"]: check["status"] for check in doctor_checks(state_path)}
    return (
        check_status_by_name.get("docker_cli") == "ok"
        and check_status_by_name.get("docker_daemon") == "ok"
    )


def derive_init_runtime_status(runtime_state: RuntimeState | None) -> str:
    if runtime_state is None:
        return "not-started"
    return runtime_state.runtime_status.value


def derive_init_next_step(
    *,
    infra_ready: bool,
    selected_agent: AgentRecord | None,
    agent_setup_ready: bool,
    gateway_ready: bool,
    default_destination_ready: bool,
    runtime_running: bool,
    runtime_status: str,
) -> tuple[str, str]:
    if not infra_ready:
        return "maia doctor", "shared-infra-not-ready"
    if selected_agent is None:
        return "maia agent new", "create-first-agent-identity"
    if not agent_setup_ready:
        return f"maia agent setup {selected_agent.name}", "finish-agent-setup"
    if not gateway_ready:
        return f"maia agent setup-gateway {selected_agent.name}", "configure-usable-gateway"
    if not default_destination_ready:
        return f"maia agent setup-gateway {selected_agent.name}", "configure-default-destination"
    if runtime_status in {RuntimeStatus.STARTING.value, RuntimeStatus.STOPPING.value}:
        return f"maia agent status {selected_agent.name}", "wait-for-runtime-transition"
    if not runtime_running:
        return f"maia agent start {selected_agent.name}", "start-agent-runtime"
    return "-", "conversation-ready-now"


def format_init_output_lines(
    report: dict[str, object],
    *,
    format_preview_value: Callable[[str], str],
) -> list[str]:
    return [
        _format_init_state_line(
            "infra_ready",
            bool(report["infra_ready"]),
            format_preview_value=format_preview_value,
        ),
        _format_init_state_line(
            "agent_identity_ready",
            bool(report["agent_identity_ready"]),
            agent_id=str(report["selected_agent_id"]),
            name=str(report["selected_agent_name"]),
            source=str(report["selected_agent_source"]),
            format_preview_value=format_preview_value,
        ),
        _format_init_state_line(
            "agent_setup_ready",
            bool(report["agent_setup_ready"]),
            status=str(report["setup_status"]),
            format_preview_value=format_preview_value,
        ),
        _format_init_state_line(
            "gateway_ready",
            bool(report["gateway_ready"]),
            status=str(report["gateway_status"]),
            format_preview_value=format_preview_value,
        ),
        _format_init_state_line(
            "default_destination_ready",
            bool(report["default_destination_ready"]),
            status=str(report["gateway_status"]),
            format_preview_value=format_preview_value,
        ),
        _format_init_state_line(
            "runtime_running",
            bool(report["runtime_running"]),
            status=str(report["runtime_status"]),
            format_preview_value=format_preview_value,
        ),
        _format_init_state_line(
            "conversation_ready",
            bool(report["conversation_ready"]),
            format_preview_value=format_preview_value,
        ),
        " ".join(
            (
                "next",
                f"command={format_preview_value(str(report['next_command']))}",
                f"reason={format_preview_value(str(report['next_reason']))}",
            )
        ),
    ]


def handle_init(
    storage,
    state_path: Path | str,
    team_metadata_path: Path | str,
    *,
    deps: InitDependencies,
) -> int:
    orchestration_exit_code: int | None = None
    init_start_attempted = False
    init_start_error: str | None = None
    infra_ready = deps.ensure_init_infra_ready(state_path)
    if not infra_ready:
        orchestration_exit_code = 1

    registry = storage.load(state_path)
    team_metadata = deps.load_team_metadata(team_metadata_path)
    selected_agent, selected_source = deps.select_init_agent(registry, team_metadata)
    if infra_ready and selected_agent is None:
        selected_agent = deps.create_agent_interactively(storage, state_path, registry)
        print(deps.format_created_agent_line(selected_agent))
        selected_source = "sole-active-agent"

    if infra_ready and selected_agent is not None:
        setup_state = deps.load_runtime_setup_state(selected_agent.agent_id)
        if deps.derive_setup_state(setup_state) != "complete":
            setup_exit_code, _setup_result, setup_error = deps.run_agent_setup_passthrough(selected_agent)
            if setup_error is not None:
                print(
                    f"Agent setup failed for {selected_agent.name!r}. "
                    f"Rerun maia agent setup {selected_agent.name} after fixing the Hermes setup issue. {setup_error}",
                    file=sys.stderr,
                )
            elif setup_exit_code != 0:
                print(
                    f"Agent setup failed for {selected_agent.name!r}. "
                    f"Rerun maia agent setup {selected_agent.name} after fixing the Hermes setup issue",
                    file=sys.stderr,
                )
            if setup_exit_code != 0:
                orchestration_exit_code = setup_exit_code
        gateway_exit_code = deps.orchestrate_init_gateway_setup_if_needed(selected_agent)
        if gateway_exit_code is not None:
            orchestration_exit_code = gateway_exit_code
        if deps.init_runtime_start_capable(state_path):
            registry = storage.load(state_path)
            selected_agent = registry.get(selected_agent.agent_id)
            init_start_attempted, init_start_error = deps.orchestrate_init_runtime_start_if_needed(
                selected_agent,
                storage,
                state_path,
                registry,
                deps.build_runtime_adapter(),
            )

    registry = storage.load(state_path)
    team_metadata = deps.load_team_metadata(team_metadata_path)
    selected_agent, selected_source = deps.select_init_agent(registry, team_metadata)
    infra_ready = deps.init_infra_ready(state_path)
    runtime_state = None
    if selected_agent is not None:
        runtime_state = deps.resolve_runtime_state_for_init(
            selected_agent,
            deps.build_runtime_adapter(),
            infra_ready=infra_ready,
        )
        if runtime_state is not None:
            selected_agent = deps.sync_registry_status_from_runtime_state(
                selected_agent,
                runtime_state,
                storage,
                state_path,
                registry,
            )

    setup_status = deps.derive_setup_state(runtime_state)
    gateway_status = deps.derive_gateway_setup_state(runtime_state)
    runtime_status = deps.derive_init_runtime_status(runtime_state)
    agent_identity_ready = selected_agent is not None
    agent_setup_ready = agent_identity_ready and setup_status == "complete"
    gateway_ready = agent_identity_ready and deps.is_gateway_start_ready(gateway_status)
    default_destination_ready = agent_identity_ready and deps.is_default_destination_ready(gateway_status)
    runtime_running = agent_identity_ready and infra_ready and runtime_status == RuntimeStatus.RUNNING.value
    conversation_ready = all(
        (
            infra_ready,
            agent_identity_ready,
            agent_setup_ready,
            gateway_ready,
            default_destination_ready,
            runtime_running,
        )
    )
    next_command, next_reason = deps.derive_init_next_step(
        infra_ready=infra_ready,
        selected_agent=selected_agent,
        agent_setup_ready=agent_setup_ready,
        gateway_ready=gateway_ready,
        default_destination_ready=default_destination_ready,
        runtime_running=runtime_running,
        runtime_status=runtime_status,
    )
    report = {
        "infra_ready": infra_ready,
        "agent_identity_ready": agent_identity_ready,
        "selected_agent_id": "-" if selected_agent is None else selected_agent.agent_id,
        "selected_agent_name": "-" if selected_agent is None else selected_agent.name,
        "selected_agent_source": selected_source,
        "agent_setup_ready": agent_setup_ready,
        "setup_status": setup_status,
        "gateway_ready": gateway_ready,
        "gateway_status": gateway_status,
        "default_destination_ready": default_destination_ready,
        "runtime_running": runtime_running,
        "runtime_status": runtime_status,
        "conversation_ready": conversation_ready,
        "next_command": next_command,
        "next_reason": next_reason,
    }
    for line in deps.format_init_output_lines(
        report,
        format_preview_value=deps.format_preview_value,
    ):
        print(line)
    if init_start_error is not None:
        assert selected_agent is not None
        print(
            f"Agent start failed for {selected_agent.name!r}. "
            f"Rerun maia agent start {selected_agent.name} after fixing the runtime issue. {init_start_error}",
            file=sys.stderr,
        )
    elif (
        init_start_attempted
        and selected_agent is not None
        and not runtime_running
        and next_command == f"maia agent start {selected_agent.name}"
    ):
        print(
            f"Agent start did not leave {selected_agent.name!r} running. "
            f"Run maia agent logs {selected_agent.name}, then rerun maia agent start {selected_agent.name}.",
            file=sys.stderr,
        )
    if orchestration_exit_code is not None:
        return orchestration_exit_code
    return 0 if conversation_ready else 1


def _format_init_state_line(
    state_name: str,
    ready: bool,
    *,
    format_preview_value: Callable[[str], str],
    **fields: str,
) -> str:
    tokens = ["state", f"name={state_name}", f"ready={_format_init_ready_value(ready)}"]
    for field_name, value in fields.items():
        tokens.append(f"{field_name}={format_preview_value(value)}")
    return " ".join(tokens)


def _format_init_ready_value(ready: bool) -> str:
    return "yes" if ready else "no"
