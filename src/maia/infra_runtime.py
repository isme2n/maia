"""Shared infra doctor/setup helpers for Maia."""

from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
from pathlib import Path
import shutil
from urllib.parse import urlparse

from maia.sqlite_state import SQLiteState

__all__ = [
    "MAIA_NETWORK_NAME",
    "MAIA_QUEUE_CONTAINER_NAME",
    "MAIA_QUEUE_IMAGE",
    "MAIA_QUEUE_VOLUME_NAME",
    "bootstrap_shared_infra",
    "collect_doctor_checks",
    "runtime_broker_url",
]

MAIA_NETWORK_NAME = "maia"
MAIA_QUEUE_CONTAINER_NAME = "maia-rabbitmq"
MAIA_QUEUE_VOLUME_NAME = "maia-rabbitmq-data"
MAIA_QUEUE_IMAGE = "rabbitmq:3.13-alpine"


def runtime_broker_url() -> str:
    """Return the broker URL runtime containers should use for live Maia delivery."""

    configured = os.environ.get("MAIA_BROKER_URL", "").strip()
    if configured:
        return configured
    user = "guest"
    password = "guest"
    return f"amqp://{user}:{password}@{MAIA_QUEUE_CONTAINER_NAME}:5672/%2F"


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
                "name": "queue",
                "status": "blocked",
                "detail": "Queue health needs a working Docker daemon",
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
    checks.append(_collect_queue_check(docker_bin, docker_daemon_check))
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
        volume_action = _ensure_docker_resource(
            docker_bin,
            inspect_command=[docker_bin, "volume", "inspect", MAIA_QUEUE_VOLUME_NAME],
            create_command=[docker_bin, "volume", "create", MAIA_QUEUE_VOLUME_NAME],
        )
        queue_action = _ensure_queue_container(docker_bin)
    except ValueError as exc:
        sqlite_state.set_infra_status("bootstrap", status="failed", detail=str(exc))
        raise

    sqlite_state.set_infra_status("network", status="ready", detail=MAIA_NETWORK_NAME)
    sqlite_state.set_infra_status("queue_volume", status="ready", detail=MAIA_QUEUE_VOLUME_NAME)
    sqlite_state.set_infra_status("queue", status="ready", detail=MAIA_QUEUE_CONTAINER_NAME)
    sqlite_state.set_infra_status("state_db", status="ready", detail=str(target))
    sqlite_state.set_infra_status("bootstrap", status="ready", detail="shared infra is ready")

    return [
        {"step": "network", "status": network_action, "detail": MAIA_NETWORK_NAME},
        {"step": "volume", "status": volume_action, "detail": MAIA_QUEUE_VOLUME_NAME},
        {"step": "queue", "status": queue_action, "detail": MAIA_QUEUE_CONTAINER_NAME},
        {"step": "db", "status": "ready", "detail": str(target)},
    ]


def _collect_queue_check(docker_bin: str, docker_daemon_check: dict[str, str]) -> dict[str, str]:
    if docker_daemon_check["status"] != "ok":
        return {
            "name": "queue",
            "status": "blocked",
            "detail": "Queue health needs a working Docker daemon",
            "remediation": "Fix Docker first, then run maia doctor again",
        }

    result = _run_command(
        [docker_bin, "inspect", "--format", "{{.State.Status}}", MAIA_QUEUE_CONTAINER_NAME]
    )
    if result.returncode != 0:
        external_queue_check = _collect_external_queue_check()
        if external_queue_check is not None:
            return external_queue_check
        return {
            "name": "queue",
            "status": "missing",
            "detail": f"RabbitMQ container {MAIA_QUEUE_CONTAINER_NAME} is not running",
            "remediation": "Run maia setup to bootstrap shared infra",
        }

    status = result.stdout.strip().lower()
    if status == "running":
        return {
            "name": "queue",
            "status": "ok",
            "detail": f"RabbitMQ container {MAIA_QUEUE_CONTAINER_NAME} is running",
            "remediation": "No action needed",
        }
    return {
        "name": "queue",
        "status": "fail",
        "detail": f"RabbitMQ container {MAIA_QUEUE_CONTAINER_NAME} is {status or 'not ready'}",
        "remediation": "Run maia setup to restart the shared queue",
    }


def _collect_external_queue_check() -> dict[str, str] | None:
    broker_url = os.environ.get("MAIA_BROKER_URL", "").strip()
    if not broker_url:
        return None

    parsed = urlparse(broker_url)
    try:
        port = parsed.port
    except ValueError:
        return {
            "name": "queue",
            "status": "fail",
            "detail": "MAIA_BROKER_URL needs a numeric port",
            "remediation": "Use a full AMQP URL like amqp://user:***@host:5672/vhost",
        }
    if not parsed.hostname:
        return {
            "name": "queue",
            "status": "fail",
            "detail": "MAIA_BROKER_URL needs a hostname",
            "remediation": "Use a full AMQP URL like amqp://user:***@host:5672/vhost",
        }
    if port is None:
        port = 5671 if parsed.scheme == "amqps" else 5672

    try:
        with socket.create_connection((parsed.hostname, port), timeout=2):
            pass
    except OSError as exc:
        detail = exc.strerror or str(exc)
        return {
            "name": "queue",
            "status": "fail",
            "detail": detail,
            "remediation": "Start the external RabbitMQ service or run maia setup for the local shared queue",
        }

    return {
        "name": "queue",
        "status": "ok",
        "detail": f"RabbitMQ is reachable at {parsed.hostname}:{port}",
        "remediation": "No action needed",
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


def _ensure_queue_container(docker_bin: str) -> str:
    inspect_result = _run_command(
        [docker_bin, "inspect", "--format", "{{.State.Status}}", MAIA_QUEUE_CONTAINER_NAME]
    )
    if inspect_result.returncode == 0:
        status = inspect_result.stdout.strip().lower()
        if status == "running":
            return "ready"
        start_result = _run_command([docker_bin, "start", MAIA_QUEUE_CONTAINER_NAME])
        if start_result.returncode != 0:
            detail = (start_result.stderr or start_result.stdout or "command failed").strip()
            raise ValueError(detail)
        return "started"

    run_result = _run_command(
        [
            docker_bin,
            "run",
            "-d",
            "--name",
            MAIA_QUEUE_CONTAINER_NAME,
            "--network",
            MAIA_NETWORK_NAME,
            "-v",
            f"{MAIA_QUEUE_VOLUME_NAME}:/var/lib/rabbitmq",
            MAIA_QUEUE_IMAGE,
        ]
    )
    if run_result.returncode != 0:
        detail = (run_result.stderr or run_result.stdout or "command failed").strip()
        raise ValueError(detail)
    return "started"


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        return subprocess.CompletedProcess(command, 1, "", detail)
