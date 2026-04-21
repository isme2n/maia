"""Shared infra doctor/setup helpers for Maia."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path
import shutil

from maia.runtime_spec import RuntimeSpec
from maia.sqlite_state import SQLiteState

__all__ = [
    "MAIA_KERYX_BASE_URL",
    "MAIA_KERYX_CONTAINER_NAME",
    "MAIA_KERYX_HOST_PORT",
    "MAIA_KERYX_IMAGE",
    "MAIA_KERYX_INTERNAL_PORT",
    "MAIA_NETWORK_NAME",
    "bootstrap_shared_infra",
    "collect_doctor_checks",
    "default_agent_runtime_spec",
    "runtime_keryx_base_url",
]

MAIA_NETWORK_NAME = "maia"
MAIA_KERYX_CONTAINER_NAME = "maia-keryx"
MAIA_KERYX_IMAGE = "python:3.11-alpine"
MAIA_KERYX_INTERNAL_PORT = 8765
MAIA_KERYX_HOST_PORT = 8765
MAIA_KERYX_BASE_URL = f"http://{MAIA_KERYX_CONTAINER_NAME}:{MAIA_KERYX_INTERNAL_PORT}"
MAIA_HERMES_WORKER_IMAGE = "maia-local/hermes-worker:latest"
MAIA_HERMES_WORKER_WORKSPACE = "/opt/maia"


def default_agent_runtime_spec(agent_name: str) -> RuntimeSpec:
    """Return the default Hermes worker runtime spec for first-run agents."""

    _ = agent_name
    return RuntimeSpec(
        image=MAIA_HERMES_WORKER_IMAGE,
        workspace=MAIA_HERMES_WORKER_WORKSPACE,
        command=[],
        env={},
    )


def runtime_keryx_base_url() -> str:
    configured = os.environ.get("KERYX_BASE_URL", "").strip()
    if configured:
        return configured
    return MAIA_KERYX_BASE_URL


def collect_doctor_checks(state_path: Path | str) -> list[dict[str, str]]:
    """Collect shared-infra readiness checks for doctor."""

    target = Path(state_path)
    checks: list[dict[str, str]] = []
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        checks.append(
            {
                "name": "docker_cli",
                "status": "missing",
                "detail": "Docker is not installed or not on PATH",
                "remediation": "Install Docker on this host to use runtime commands",
            }
        )
        checks.append(
            {
                "name": "docker_daemon",
                "status": "missing",
                "detail": "Docker can't run because Docker is missing",
                "remediation": "Install Docker, then start the Docker service",
            }
        )
        checks.append(
            {
                "name": "keryx",
                "status": "blocked",
                "detail": "Keryx HTTP API health needs a working Docker daemon",
                "remediation": "Fix Docker first, then run maia doctor again",
            }
        )
        checks.append(_collect_state_db_check(target))
        return checks

    checks.append(
        _run_probe(
            "docker_cli",
            [docker_bin, "--version"],
            success_detail=docker_bin,
            success_remediation="No action needed",
            failure_remediation="Make sure the Docker binary is installed and available on PATH",
        )
    )
    docker_daemon_check = _run_probe(
        "docker_daemon",
        [docker_bin, "info"],
        success_detail="Docker is ready",
        success_remediation="No action needed",
        failure_remediation="Start Docker or fix Docker access permissions",
    )
    checks.append(docker_daemon_check)
    checks.append(_collect_keryx_check(docker_bin, docker_daemon_check))
    checks.append(_collect_state_db_check(target))
    return checks


def bootstrap_shared_infra(state_path: Path | str) -> list[dict[str, str]]:
    """Ensure shared Maia infra exists and is ready."""

    target = Path(state_path)
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        raise ValueError("Docker is not installed or not on PATH")

    docker_daemon_check = _run_probe(
        "docker_daemon",
        [docker_bin, "info"],
        success_detail="Docker is ready",
        success_remediation="No action needed",
        failure_remediation="Start Docker or fix Docker access permissions",
    )
    if docker_daemon_check["status"] != "ok":
        raise ValueError(docker_daemon_check["detail"])

    sqlite_state = SQLiteState(target)
    try:
        sqlite_state.initialize()
    except (OSError, sqlite3.Error) as exc:
        raise ValueError(_state_db_unreadable_message(target)) from exc
    sqlite_state.set_infra_status("bootstrap", status="pending", detail="shared infra bootstrap in progress")

    try:
        network_action = _ensure_docker_resource(
            docker_bin,
            inspect_command=[docker_bin, "network", "inspect", MAIA_NETWORK_NAME],
            create_command=[docker_bin, "network", "create", MAIA_NETWORK_NAME],
        )
        keryx_action = _ensure_keryx_container(docker_bin, target)
    except ValueError as exc:
        sqlite_state.set_infra_status("bootstrap", status="failed", detail=str(exc))
        raise

    sqlite_state.set_infra_status("network", status="ready", detail=MAIA_NETWORK_NAME)
    sqlite_state.set_infra_status("keryx", status="ready", detail=runtime_keryx_base_url())
    sqlite_state.set_infra_status("state_db", status="ready", detail=str(target))
    sqlite_state.set_infra_status("bootstrap", status="ready", detail="shared infra is ready")

    return [
        {"step": "network", "status": network_action, "detail": MAIA_NETWORK_NAME},
        {"step": "keryx", "status": keryx_action, "detail": runtime_keryx_base_url()},
        {"step": "db", "status": "ready", "detail": str(target)},
    ]


def _collect_keryx_check(docker_bin: str, docker_daemon_check: dict[str, str]) -> dict[str, str]:
    if docker_daemon_check["status"] != "ok":
        return {
            "name": "keryx",
            "status": "blocked",
            "detail": "Keryx HTTP API health needs a working Docker daemon",
            "remediation": "Fix Docker first, then run maia doctor again",
        }

    result = _run_command(
        [docker_bin, "inspect", "--format", "{{.State.Status}}", MAIA_KERYX_CONTAINER_NAME]
    )
    if result.returncode != 0:
        return {
            "name": "keryx",
            "status": "missing",
            "detail": f"Keryx HTTP API endpoint {runtime_keryx_base_url()} is not running",
            "remediation": "Run maia setup to bootstrap shared infra",
        }

    status = result.stdout.strip().lower()
    if status == "running":
        return {
            "name": "keryx",
            "status": "ok",
            "detail": f"Keryx HTTP API endpoint {runtime_keryx_base_url()} is running",
            "remediation": "No action needed",
        }
    return {
        "name": "keryx",
        "status": "fail",
        "detail": f"Keryx HTTP API container {MAIA_KERYX_CONTAINER_NAME} is {status or 'not ready'}",
        "remediation": "Run maia setup to restart the shared Keryx HTTP API",
    }


def _collect_state_db_check(state_path: Path) -> dict[str, str]:
    try:
        SQLiteState(state_path).initialize()
    except (OSError, sqlite3.Error):
        return {
            "name": "state_db",
            "status": "fail",
            "detail": _state_db_unreadable_message(state_path),
            "remediation": "Repair or replace the local Maia state DB, then run maia doctor again",
        }
    return {
        "name": "state_db",
        "status": "ok",
        "detail": str(state_path),
        "remediation": "No action needed",
    }


def _state_db_unreadable_message(state_path: Path) -> str:
    return f"Maia state DB at {state_path} is unreadable"


def _run_probe(
    name: str,
    command: list[str],
    *,
    success_detail: str,
    success_remediation: str,
    failure_remediation: str,
) -> dict[str, str]:
    result = _run_command(command)
    if result.returncode == 0:
        return {
            "name": name,
            "status": "ok",
            "detail": success_detail,
            "remediation": success_remediation,
        }

    detail = (result.stderr or result.stdout or "probe failed").strip()
    if name == "docker_daemon" and "permission denied" in detail.lower():
        detail = "Docker is installed, but this user cannot talk to the Docker daemon"
        failure_remediation = "Start Docker and make sure your user has permission to use it"
    return {
        "name": name,
        "status": "fail",
        "detail": detail,
        "remediation": failure_remediation,
    }


def _ensure_docker_resource(
    docker_bin: str,
    *,
    inspect_command: list[str],
    create_command: list[str],
) -> str:
    inspect_result = _run_command(inspect_command)
    if inspect_result.returncode == 0:
        return "ready"
    create_result = _run_command(create_command)
    if create_result.returncode != 0:
        detail = (create_result.stderr or create_result.stdout or "command failed").strip()
        raise ValueError(detail)
    return "created"


def _ensure_keryx_container(docker_bin: str, state_path: Path) -> str:
    inspect_result = _run_command(
        [docker_bin, "inspect", "--format", "{{.State.Status}}", MAIA_KERYX_CONTAINER_NAME]
    )
    if inspect_result.returncode == 0:
        if not _keryx_container_matches_state_path(docker_bin, state_path):
            remove_result = _run_command([docker_bin, "rm", "-f", MAIA_KERYX_CONTAINER_NAME])
            if remove_result.returncode != 0:
                detail = (remove_result.stderr or remove_result.stdout or "command failed").strip()
                raise ValueError(detail)
            run_result = _run_command(_keryx_run_command(docker_bin, state_path))
            if run_result.returncode != 0:
                detail = (run_result.stderr or run_result.stdout or "command failed").strip()
                raise ValueError(detail)
            return "restarted"
        status = inspect_result.stdout.strip().lower()
        if status == "running":
            return "ready"
        start_result = _run_command([docker_bin, "start", MAIA_KERYX_CONTAINER_NAME])
        if start_result.returncode != 0:
            detail = (start_result.stderr or start_result.stdout or "command failed").strip()
            raise ValueError(detail)
        return "started"

    run_result = _run_command(_keryx_run_command(docker_bin, state_path))
    if run_result.returncode != 0:
        detail = (run_result.stderr or run_result.stdout or "command failed").strip()
        raise ValueError(detail)
    return "started"


def _keryx_container_matches_state_path(docker_bin: str, state_path: Path) -> bool:
    mounts_result = _run_command(
        [
            docker_bin,
            "inspect",
            "--format",
            "{{range .Mounts}}{{println .Source \"|\" .Destination}}{{end}}",
            MAIA_KERYX_CONTAINER_NAME,
        ]
    )
    if mounts_result.returncode != 0:
        return False
    expected_source = state_path.resolve()
    for raw_line in mounts_result.stdout.splitlines():
        source, separator, destination = raw_line.partition("|")
        if separator and destination.strip() == "/maia/control/state.db":
            if Path(source.strip()).resolve() == expected_source:
                return True
    return False


def _keryx_run_command(docker_bin: str, state_path: Path) -> list[str]:
    source_root = Path(__file__).resolve().parents[1]
    return [
        docker_bin,
        "run",
        "-d",
        "--name",
        MAIA_KERYX_CONTAINER_NAME,
        "--network",
        MAIA_NETWORK_NAME,
        "-p",
        f"127.0.0.1:{MAIA_KERYX_HOST_PORT}:{MAIA_KERYX_INTERNAL_PORT}",
        "-v",
        f"{source_root}:/opt/maia/src:ro",
        "-v",
        f"{state_path}:/maia/control/state.db",
        "-e",
        "PYTHONPATH=/opt/maia/src",
        MAIA_KERYX_IMAGE,
        "python",
        "-c",
        (
            "from maia.keryx_server import create_keryx_http_server; "
            f"server = create_keryx_http_server(host='0.0.0.0', port={MAIA_KERYX_INTERNAL_PORT}, "
            "state_db_path='/maia/control/state.db'); "
            "server.serve_forever()"
        ),
    ]


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        return subprocess.CompletedProcess(command, 1, "", detail)
