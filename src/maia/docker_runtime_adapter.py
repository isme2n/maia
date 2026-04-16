"""Docker CLI-backed runtime adapter for Maia."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from maia.app_state import get_agent_hermes_home
from maia.infra_runtime import MAIA_NETWORK_NAME, runtime_broker_url
from maia.runtime_adapter import (
    RuntimeAdapter,
    RuntimeLogsRequest,
    RuntimeLogsResult,
    RuntimeStartRequest,
    RuntimeStartResult,
    RuntimeState,
    RuntimeStatus,
    RuntimeStatusRequest,
    RuntimeStatusResult,
    RuntimeStopRequest,
    RuntimeStopResult,
)
from maia.runtime_state_storage import RuntimeStateStorage

__all__ = ["DockerRuntimeAdapter"]

_AUTO_DOCKER_BIN = object()


class DockerRuntimeAdapter(RuntimeAdapter):
    """Runtime adapter implemented via the Docker CLI."""

    def __init__(
        self,
        *,
        state_storage: RuntimeStateStorage,
        state_path: Path | str,
        docker_bin: str | None | object = _AUTO_DOCKER_BIN,
    ) -> None:
        self._state_storage = state_storage
        self._state_path = Path(state_path)
        self._docker_bin = shutil.which("docker") if docker_bin is _AUTO_DOCKER_BIN else docker_bin

    def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        docker_bin = self._require_docker_bin()
        spec = request.agent.runtime_spec
        if spec is None:
            raise ValueError("Runtime start requires agent.runtime_spec")
        existing_state = self._load_states().get(request.agent.agent_id)
        hermes_home = get_agent_hermes_home(
            request.agent.agent_id,
            {"HOME": str(self._state_path.parent.parent)},
        )
        hermes_home.mkdir(parents=True, exist_ok=True)
        command = [
            docker_bin,
            "run",
            "-d",
            "--label",
            f"maia.agent_id={request.agent.agent_id}",
            "--network",
            MAIA_NETWORK_NAME,
            "-w",
            spec.workspace,
            "-v",
            f"{hermes_home}:/maia/hermes",
            "-e",
            "HERMES_HOME=/maia/hermes",
        ]
        runtime_env = {"MAIA_BROKER_URL": runtime_broker_url(), **spec.env}
        for key, value in sorted(runtime_env.items()):
            command.extend(["-e", f"{key}={value}"])
        command.append(spec.image)
        command.extend(spec.command)
        result = self._run(command, failure_prefix="Docker start failed")
        runtime_handle = result.stdout.strip()
        if not runtime_handle:
            raise ValueError("Docker start failed: empty runtime handle")
        state = RuntimeState(
            agent_id=request.agent.agent_id,
            runtime_status=RuntimeStatus.RUNNING,
            runtime_handle=runtime_handle,
            setup_status=None if existing_state is None else existing_state.setup_status,
        )
        self._write_state(state)
        return RuntimeStartResult(runtime=state)

    def stop(self, request: RuntimeStopRequest) -> RuntimeStopResult:
        docker_bin = self._require_docker_bin()
        current = self._require_runtime_state(request.agent_id)
        runtime_handle = request.runtime_handle or current.runtime_handle
        if runtime_handle is None:
            raise ValueError(f"Runtime handle for agent {request.agent_id!r} not found")
        self._run([docker_bin, "stop", runtime_handle], failure_prefix="Docker stop failed")
        state = RuntimeState(
            agent_id=request.agent_id,
            runtime_status=RuntimeStatus.STOPPED,
            runtime_handle=runtime_handle,
            setup_status=current.setup_status,
        )
        self._write_state(state)
        return RuntimeStopResult(runtime=state)

    def status(self, request: RuntimeStatusRequest) -> RuntimeStatusResult:
        docker_bin = self._require_docker_bin()
        current = self._require_runtime_state(request.agent_id)
        runtime_handle = current.runtime_handle
        if runtime_handle is None:
            raise ValueError(f"Runtime handle for agent {request.agent_id!r} not found")
        result = self._run(
            [docker_bin, "inspect", "--format", "{{.State.Status}}", runtime_handle],
            failure_prefix="Docker status failed",
        )
        state = RuntimeState(
            agent_id=request.agent_id,
            runtime_status=_parse_docker_status(result.stdout.strip()),
            runtime_handle=runtime_handle,
            setup_status=current.setup_status,
        )
        self._write_state(state)
        return RuntimeStatusResult(runtime=state)

    def logs(self, request: RuntimeLogsRequest) -> RuntimeLogsResult:
        docker_bin = self._require_docker_bin()
        current = self._require_runtime_state(request.agent_id)
        runtime_handle = current.runtime_handle
        if runtime_handle is None:
            raise ValueError(f"Runtime handle for agent {request.agent_id!r} not found")
        status_result = self.status(RuntimeStatusRequest(agent_id=request.agent_id))
        result = self._run(
            [docker_bin, "logs", "--tail", str(request.tail_lines), runtime_handle],
            failure_prefix="Docker logs failed",
        )
        log_stream = result.stdout
        if result.stderr.strip():
            log_stream = f"{log_stream}\n{result.stderr}" if log_stream.strip() else result.stderr
        lines = [line for line in log_stream.splitlines() if line]
        return RuntimeLogsResult(runtime=status_result.runtime, lines=lines)

    def _require_docker_bin(self) -> str:
        if self._docker_bin is None:
            raise ValueError("Docker CLI not found in PATH")
        return self._docker_bin

    def _run(self, command: list[str], *, failure_prefix: str) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as exc:
            detail = exc.strerror or str(exc)
            raise ValueError(f"{failure_prefix}: {detail}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "command failed").strip()
            raise ValueError(f"{failure_prefix}: {detail}")
        return result

    def _load_states(self) -> dict[str, RuntimeState]:
        return self._state_storage.load(self._state_path)

    def _write_state(self, state: RuntimeState) -> None:
        states = self._load_states()
        states[state.agent_id] = state
        self._state_storage.save(self._state_path, states)

    def _require_runtime_state(self, agent_id: str) -> RuntimeState:
        states = self._load_states()
        try:
            return states[agent_id]
        except KeyError as exc:
            raise LookupError(f"Runtime state for agent {agent_id!r} not found") from exc


def _parse_docker_status(value: str) -> RuntimeStatus:
    normalized = value.strip().lower()
    if normalized in {"created", "restarting"}:
        return RuntimeStatus.STARTING
    if normalized == "running":
        return RuntimeStatus.RUNNING
    if normalized in {"removing", "stopping", "paused"}:
        return RuntimeStatus.STOPPING
    if normalized in {"exited", "dead"}:
        return RuntimeStatus.STOPPED
    if normalized == "failed":
        return RuntimeStatus.FAILED
    raise ValueError(f"Unsupported Docker runtime status: {value!r}")
