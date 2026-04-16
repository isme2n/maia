from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
from maia.docker_runtime_adapter import DockerRuntimeAdapter
from maia.runtime_adapter import (
    RuntimeLogsRequest,
    RuntimeStartRequest,
    RuntimeState,
    RuntimeStatus,
    RuntimeStatusRequest,
    RuntimeStopRequest,
)
from maia.runtime_spec import RuntimeSpec
from maia.runtime_state_storage import RuntimeStateStorage


def _build_agent() -> AgentRecord:
    return AgentRecord(
        agent_id="agent-001",
        name="reviewer",
        status=AgentStatus.STOPPED,
        persona="strict",
        runtime_spec=RuntimeSpec(
            image="ghcr.io/example/reviewer:latest",
            workspace="/workspace/reviewer",
            command=["python", "-m", "reviewer"],
            env={"MAIA_ENV": "test"},
        ),
    )


def _write_fake_docker(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import json, sys\n"
        "state_path = Path(__file__).with_name('fake-docker-state.json')\n"
        "if state_path.exists():\n"
        "    state = json.loads(state_path.read_text(encoding='utf-8'))\n"
        "else:\n"
        "    state = {'containers': {}, 'counter': 0}\n"
        "args = sys.argv[1:]\n"
        "def save():\n"
        "    state_path.write_text(json.dumps(state), encoding='utf-8')\n"
        "if args == ['--version']:\n"
        "    print('Docker version 27.0.0')\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['run', '-d']:\n"
        "    state['counter'] += 1\n"
        "    handle = f\"runtime-{state['counter']:03d}\"\n"
        "    state['containers'][handle] = {'status': 'running', 'logs': ['line 1', 'line 2']}\n"
        "    save()\n"
        "    print(handle)\n"
        "    raise SystemExit(0)\n"
        "if args[:1] == ['stop']:\n"
        "    handle = args[1]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    state['containers'][handle]['status'] = 'exited'\n"
        "    save()\n"
        "    print(handle)\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['inspect', '--format']:\n"
        "    handle = args[3]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    print(state['containers'][handle]['status'])\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['logs', '--tail']:\n"
        "    handle = args[3]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    tail = int(args[2])\n"
        "    for line in state['containers'][handle]['logs'][-tail:]:\n"
        "        print(line)\n"
        "    raise SystemExit(0)\n"
        "print('unsupported command', file=sys.stderr)\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_runtime_state_storage_round_trip(tmp_path: Path) -> None:
    storage = RuntimeStateStorage()
    path = tmp_path / "runtime" / "runtime-state.json"
    states = {
        "agent-001": RuntimeState(
            agent_id="agent-001",
            runtime_status=RuntimeStatus.RUNNING,
            runtime_handle="runtime-001",
        )
    }

    storage.save(path, states)
    restored = storage.load(path)

    assert restored == states


def test_docker_runtime_adapter_start_status_logs_stop_flow(tmp_path: Path) -> None:
    fake_docker = tmp_path / "docker"
    _write_fake_docker(fake_docker)
    state_path = tmp_path / "runtime-state.json"
    adapter = DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=state_path,
        docker_bin=str(fake_docker),
    )

    start_result = adapter.start(RuntimeStartRequest(agent=_build_agent()))
    assert start_result.runtime.agent_id == "agent-001"
    assert start_result.runtime.runtime_status is RuntimeStatus.RUNNING
    assert start_result.runtime.runtime_handle == "runtime-001"

    status_result = adapter.status(RuntimeStatusRequest(agent_id="agent-001"))
    assert status_result.runtime.runtime_status is RuntimeStatus.RUNNING
    assert status_result.runtime.runtime_handle == "runtime-001"

    logs_result = adapter.logs(RuntimeLogsRequest(agent_id="agent-001", tail_lines=1))
    assert logs_result.runtime.runtime_status is RuntimeStatus.RUNNING
    assert logs_result.lines == ["line 2"]

    stop_result = adapter.stop(RuntimeStopRequest(agent_id="agent-001"))
    assert stop_result.runtime.runtime_status is RuntimeStatus.STOPPED
    assert stop_result.runtime.runtime_handle == "runtime-001"

    stored = RuntimeStateStorage().load(state_path)
    assert stored["agent-001"].runtime_status is RuntimeStatus.STOPPED


def test_docker_runtime_adapter_missing_docker_error(tmp_path: Path) -> None:
    adapter = DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=tmp_path / "runtime-state.json",
        docker_bin=None,
    )

    with pytest.raises(ValueError, match="Docker CLI not found in PATH"):
        adapter.start(RuntimeStartRequest(agent=_build_agent()))


def test_docker_runtime_adapter_missing_runtime_state_error(tmp_path: Path) -> None:
    fake_docker = tmp_path / "docker"
    _write_fake_docker(fake_docker)
    adapter = DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=tmp_path / "runtime-state.json",
        docker_bin=str(fake_docker),
    )

    with pytest.raises(LookupError, match="Runtime state for agent 'agent-001' not found"):
        adapter.status(RuntimeStatusRequest(agent_id="agent-001"))


def test_docker_runtime_adapter_maps_paused_to_stopping() -> None:
    from maia.docker_runtime_adapter import _parse_docker_status

    assert _parse_docker_status("paused") is RuntimeStatus.STOPPING


def test_docker_runtime_adapter_surfaces_command_failures(tmp_path: Path) -> None:
    failing_docker = tmp_path / "docker"
    failing_docker.write_text(
        "#!/bin/sh\n"
        "echo 'boom' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    failing_docker.chmod(0o755)
    adapter = DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=tmp_path / "runtime-state.json",
        docker_bin=str(failing_docker),
    )

    with pytest.raises(ValueError, match="Docker start failed: boom"):
        adapter.start(RuntimeStartRequest(agent=_build_agent()))


def test_docker_runtime_adapter_collects_successful_stderr_logs(tmp_path: Path) -> None:
    docker_script = tmp_path / "docker"
    docker_script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['inspect', '--format']:\n"
        "    print('running')\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['logs', '--tail']:\n"
        "    print('stderr line', file=sys.stderr)\n"
        "    raise SystemExit(0)\n"
        "print('ok')\n"
        "raise SystemExit(0)\n",
        encoding='utf-8',
    )
    docker_script.chmod(0o755)
    state_path = tmp_path / "runtime-state.json"
    RuntimeStateStorage().save(
        state_path,
        {
            "agent-001": RuntimeState(
                agent_id="agent-001",
                runtime_status=RuntimeStatus.RUNNING,
                runtime_handle="runtime-001",
            )
        },
    )
    adapter = DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=state_path,
        docker_bin=str(docker_script),
    )

    result = adapter.logs(RuntimeLogsRequest(agent_id="agent-001", tail_lines=10))

    assert result.lines == ["stderr line"]


def test_docker_runtime_adapter_syncs_exited_container_to_stopped(tmp_path: Path) -> None:
    fake_docker = tmp_path / "docker"
    _write_fake_docker(fake_docker)
    state_path = tmp_path / "runtime-state.json"
    adapter = DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=state_path,
        docker_bin=str(fake_docker),
    )

    start_result = adapter.start(RuntimeStartRequest(agent=_build_agent()))
    assert start_result.runtime.runtime_handle == "runtime-001"

    fake_state_path = tmp_path / "fake-docker-state.json"
    fake_state = json.loads(fake_state_path.read_text(encoding="utf-8"))
    fake_state["containers"]["runtime-001"]["status"] = "exited"
    fake_state_path.write_text(json.dumps(fake_state), encoding="utf-8")

    status_result = adapter.status(RuntimeStatusRequest(agent_id="agent-001"))

    assert status_result.runtime.runtime_status is RuntimeStatus.STOPPED
    assert RuntimeStateStorage().load(state_path)["agent-001"].runtime_status is RuntimeStatus.STOPPED
