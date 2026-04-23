"""Helpers for Maia's canonical `maia init` flow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from maia import infra_runtime
from maia.agent_model import AgentRecord, AgentStatus
from maia.cli_bootstrap import format_setup_step_line, is_doctor_failure
from maia.runtime_adapter import RuntimeStatus, RuntimeState
from maia.team_metadata import TeamMetadata

__all__ = [
    "derive_init_next_step",
    "derive_init_runtime_status",
    "ensure_init_infra_ready",
    "format_init_output_lines",
    "init_infra_ready",
    "init_runtime_start_capable",
    "select_init_agent",
]


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
