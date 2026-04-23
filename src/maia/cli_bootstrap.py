"""Bootstrap command-domain helpers for Maia CLI."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from maia import infra_runtime
from maia.app_state import get_state_db_path

__all__ = [
    "format_doctor_output_lines",
    "format_setup_step_line",
    "handle_doctor",
    "handle_setup",
    "is_doctor_failure",
]


def handle_doctor(*, verbose: bool = False) -> int:
    checks = infra_runtime.collect_doctor_checks(get_state_db_path())
    failed_checks = [check["name"] for check in checks if is_doctor_failure(check)]
    for line in format_doctor_output_lines(
        checks,
        failed_checks,
        state_path=get_state_db_path(),
        verbose=verbose,
    ):
        print(line)
    return 0 if not failed_checks else 1


def handle_setup() -> int:
    steps = infra_runtime.bootstrap_shared_infra(get_state_db_path())
    for step in steps:
        print(format_setup_step_line(step))
    print("Shared infra is ready.")
    print("Next: run maia agent new")
    return 0


def is_doctor_failure(check: dict[str, str]) -> bool:
    return check["status"] != "ok"


def _doctor_next_step(checks: list[dict[str, str]], failed_checks: list[str]) -> str:
    if not failed_checks:
        return "shared infra is ready"
    if "docker_cli" in failed_checks:
        return "install Docker, then run maia doctor again"
    if "docker_daemon" in failed_checks:
        docker_daemon_check = next((check for check in checks if check["name"] == "docker_daemon"), None)
        if docker_daemon_check and "cannot talk to the Docker daemon" in docker_daemon_check["detail"]:
            return "fix Docker permissions for this user, then run maia doctor again"
        return "start Docker, then run maia doctor again"
    if "keryx" in failed_checks:
        return "run maia setup to bootstrap shared infra"
    if "state_db" in failed_checks:
        return "fix local Maia state permissions, then run maia doctor again"
    return "fix the failed checks above, then run maia doctor again"


def _doctor_component_label(name: str) -> str:
    return {
        "docker": "Docker",
        "keryx": "Keryx HTTP API",
        "state_db": "SQLite State DB",
    }[name]


def _doctor_status_token(check: dict[str, str]) -> tuple[str, str]:
    status = check["status"]
    if status == "ok":
        return "✓", "OK"
    if status == "blocked":
        return "•", "BLOCKED"
    return "✗", "FAIL"


def _doctor_color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    isatty = getattr(sys.stdout, "isatty", None)
    return bool(isatty and isatty())


def _style_doctor_token(text: str, token: str) -> str:
    if not _doctor_color_enabled():
        return text
    color = {
        "OK": "32",
        "BLOCKED": "33",
        "FAIL": "31",
    }[token]
    return f"\033[{color}m{text}\033[0m"


def _doctor_check_by_name(checks: list[dict[str, str]], name: str) -> dict[str, str] | None:
    return next((check for check in checks if check["name"] == name), None)


def _format_doctor_summary_lines(checks: list[dict[str, str]], failed_checks: list[str]) -> list[str]:
    lines: list[str] = []
    docker_cli = _doctor_check_by_name(checks, "docker_cli")
    docker_daemon = _doctor_check_by_name(checks, "docker_daemon")
    keryx = _doctor_check_by_name(checks, "keryx")
    state_db = _doctor_check_by_name(checks, "state_db")

    docker_ok = bool(
        docker_cli and docker_cli["status"] == "ok" and docker_daemon and docker_daemon["status"] == "ok"
    )
    if docker_ok:
        icon, token = "✓", "OK"
        lines.append(f"{_style_doctor_token(icon, token)} {_doctor_component_label('docker')} {_style_doctor_token(token, token)}")
    else:
        detail = docker_daemon["detail"] if docker_daemon and docker_daemon["status"] != "ok" else (
            "Docker CLI is missing" if docker_cli and docker_cli["status"] != "ok" else "Docker is not ready"
        )
        icon, token = "✗", "FAIL"
        lines.append(
            f"{_style_doctor_token(icon, token)} {_doctor_component_label('docker')} {_style_doctor_token(token, token)} — {detail}"
        )

    for check_name, check in (("keryx", keryx), ("state_db", state_db)):
        if not check:
            continue
        icon, token = _doctor_status_token(check)
        lines.append(
            f"{_style_doctor_token(icon, token)} {_doctor_component_label(check_name)} {_style_doctor_token(token, token)}"
            + ("" if token == "OK" else f" — {check['detail']}")
        )

    next_step = _doctor_next_step(checks, failed_checks)
    if failed_checks:
        lines.append(f"Next: {next_step}")
    else:
        icon, token = "✓", "OK"
        lines.append(f"{_style_doctor_token(icon, token)} Shared infra ready")
    return lines


def _doctor_detail_lines(checks: list[dict[str, str]], *, state_path: Path | str) -> dict[str, list[str]]:
    docker_cli = _doctor_check_by_name(checks, "docker_cli")
    docker_daemon = _doctor_check_by_name(checks, "docker_daemon")
    docker_detail = "CLI docker; daemon ready via `docker info`"
    if docker_cli and docker_cli["status"] != "ok":
        docker_detail = "CLI docker not found on PATH; daemon probe unavailable without Docker"
    elif docker_daemon and docker_daemon["status"] != "ok":
        docker_detail = f"CLI docker; daemon probe failed: {docker_daemon['detail']}"

    keryx_details = [f"  detail: endpoint={infra_runtime.runtime_keryx_base_url()}"]
    if infra_runtime.using_default_keryx_base_url():
        keryx_details.append(
            "  detail: "
            f"container={infra_runtime.MAIA_KERYX_CONTAINER_NAME} "
            f"image={infra_runtime.MAIA_KERYX_IMAGE} "
            f"host=127.0.0.1:{infra_runtime.MAIA_KERYX_HOST_PORT}->{infra_runtime.MAIA_KERYX_INTERNAL_PORT} "
            f"runtime=python HTTP server from {infra_runtime.keryx_server_container_path()}"
        )
    else:
        keryx_details.append("  detail: runtime=external Keryx HTTP API configured via KERYX_BASE_URL")

    return {
        "docker": [f"  detail: {docker_detail}"],
        "keryx": keryx_details,
        "state_db": [f"  detail: path={state_path}"],
    }


def format_doctor_output_lines(
    checks: list[dict[str, str]],
    failed_checks: list[str],
    *,
    state_path: Path | str,
    verbose: bool,
) -> list[str]:
    lines = _format_doctor_summary_lines(checks, failed_checks)
    if not verbose:
        return lines

    detail_lines = _doctor_detail_lines(checks, state_path=state_path)
    output: list[str] = []
    summary_components = ("docker", "keryx", "state_db")
    for component_name, summary_line in zip(summary_components, lines[: len(summary_components)], strict=False):
        output.append(summary_line)
        output.extend(detail_lines.get(component_name, []))
    output.extend(lines[len(summary_components) :])
    return output


def format_setup_step_line(step: dict[str, str]) -> str:
    action_by_status = {
        "created": "Created",
        "started": "Started",
        "ready": "Ready",
    }
    action = action_by_status.get(step["status"], step["status"].capitalize())
    if step["step"] == "network":
        return f"{action} Maia network {step['detail']}."
    if step["step"] == "volume":
        return f"{action} Maia volume {step['detail']}."
    if step["step"] == "queue":
        return f"{action} RabbitMQ {step['detail']}."
    if step["step"] == "keryx":
        return f"{action} Keryx HTTP API {step['detail']}."
    if step["step"] == "db":
        return f"SQLite State DB is ready at {step['detail']}."
    return f"{action} {step['step']} {step['detail']}."
