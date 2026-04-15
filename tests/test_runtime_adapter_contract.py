from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord, AgentStatus
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
from maia.runtime_spec import RuntimeSpec


def _build_agent(*, with_runtime_spec: bool = True) -> AgentRecord:
    return AgentRecord(
        agent_id="agent-001",
        name="reviewer",
        status=AgentStatus.STOPPED,
        persona="strict",
        runtime_spec=(
            RuntimeSpec(
                image="ghcr.io/example/reviewer:latest",
                workspace="/workspace/reviewer",
                command=["python", "-m", "reviewer"],
                env={"MAIA_ENV": "test"},
            )
            if with_runtime_spec
            else None
        ),
    )


def _build_runtime_state(
    runtime_status: RuntimeStatus = RuntimeStatus.RUNNING,
) -> RuntimeState:
    return RuntimeState(
        agent_id="agent-001",
        runtime_status=runtime_status,
        runtime_handle="runtime-001",
    )


def test_runtime_status_values() -> None:
    assert RuntimeStatus.STARTING.value == "starting"
    assert RuntimeStatus.RUNNING.value == "running"
    assert RuntimeStatus.STOPPING.value == "stopping"
    assert RuntimeStatus.STOPPED.value == "stopped"
    assert RuntimeStatus.FAILED.value == "failed"


def test_runtime_state_round_trip_with_runtime_handle() -> None:
    state = _build_runtime_state()

    restored = RuntimeState.from_dict(state.to_dict())

    assert restored == state
    assert restored.to_dict() == {
        "agent_id": "agent-001",
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
    }


def test_runtime_state_round_trip_without_runtime_handle() -> None:
    state = RuntimeState(
        agent_id="agent-001",
        runtime_status=RuntimeStatus.RUNNING,
    )

    restored = RuntimeState.from_dict(state.to_dict())

    assert restored == state
    assert restored.runtime_handle is None
    assert restored.to_dict() == {
        "agent_id": "agent-001",
        "runtime_status": "running",
    }


def test_runtime_state_invalid_runtime_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid runtime status: 'paused'"):
        RuntimeState.from_dict(
            {
                "agent_id": "agent-001",
                "runtime_status": "paused",
            }
        )


def test_runtime_start_request_round_trip_and_copies_agent_record() -> None:
    agent = _build_agent()
    request = RuntimeStartRequest(agent=agent)

    assert request.agent is not agent
    assert request.agent.runtime_spec is not agent.runtime_spec

    agent.runtime_spec.command.append("--debug")
    agent.runtime_spec.env["MAIA_TRACE"] = "1"

    restored = RuntimeStartRequest.from_dict(request.to_dict())

    assert request.agent.runtime_spec.command == ["python", "-m", "reviewer"]
    assert request.agent.runtime_spec.env == {"MAIA_ENV": "test"}
    assert restored == request


def test_runtime_start_request_requires_runtime_spec() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid runtime start request agent runtime_spec: expected RuntimeSpec",
    ):
        RuntimeStartRequest(agent=_build_agent(with_runtime_spec=False))


@pytest.mark.parametrize(
    ("request_type", "payload", "expected"),
    [
        (
            RuntimeStopRequest,
            {"agent_id": "agent-001", "runtime_handle": "runtime-001"},
            {"agent_id": "agent-001", "runtime_handle": "runtime-001"},
        ),
        (
            RuntimeStatusRequest,
            {"agent_id": "agent-001"},
            {"agent_id": "agent-001"},
        ),
        (
            RuntimeLogsRequest,
            {"agent_id": "agent-001"},
            {"agent_id": "agent-001", "tail_lines": 100},
        ),
    ],
)
def test_runtime_request_round_trip_defaults(
    request_type: type[RuntimeStopRequest | RuntimeStatusRequest | RuntimeLogsRequest],
    payload: dict[str, object],
    expected: dict[str, object],
) -> None:
    request = request_type.from_dict(payload)

    assert request.to_dict() == expected


def test_runtime_logs_request_invalid_tail_lines_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid runtime logs request tail_lines: expected int >= 1",
    ):
        RuntimeLogsRequest(agent_id="agent-001", tail_lines=0)


def test_runtime_stop_request_invalid_runtime_handle_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid runtime stop request runtime_handle: expected str",
    ):
        RuntimeStopRequest(agent_id="agent-001", runtime_handle=123)


def test_runtime_result_round_trip_models() -> None:
    start = RuntimeStartResult(runtime=_build_runtime_state(RuntimeStatus.STARTING))
    stop = RuntimeStopResult(runtime=_build_runtime_state(RuntimeStatus.STOPPED))
    status = RuntimeStatusResult(runtime=_build_runtime_state(RuntimeStatus.RUNNING))
    logs = RuntimeLogsResult(
        runtime=_build_runtime_state(RuntimeStatus.RUNNING),
        lines=["line 1", "line 2"],
    )

    restored_start = RuntimeStartResult.from_dict(start.to_dict())
    restored_stop = RuntimeStopResult.from_dict(stop.to_dict())
    restored_status = RuntimeStatusResult.from_dict(status.to_dict())
    restored_logs = RuntimeLogsResult.from_dict(logs.to_dict())

    assert restored_start == start
    assert restored_stop == stop
    assert restored_status == status
    assert restored_logs == logs


def test_runtime_logs_result_copies_lines_list() -> None:
    lines = ["line 1"]
    result = RuntimeLogsResult(
        runtime=_build_runtime_state(),
        lines=lines,
    )

    assert result.lines is not lines

    lines.append("line 2")

    assert result.lines == ["line 1"]


def test_runtime_logs_result_invalid_lines_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid runtime logs result lines: expected list\[str\]",
    ):
        RuntimeLogsResult(
            runtime=_build_runtime_state(),
            lines=["line 1", 2],
        )


def test_runtime_adapter_interface_contract() -> None:
    class StubRuntimeAdapter(RuntimeAdapter):
        def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
            return RuntimeStartResult(
                runtime=RuntimeState(
                    agent_id=request.agent.agent_id,
                    runtime_status=RuntimeStatus.STARTING,
                    runtime_handle="runtime-001",
                )
            )

        def stop(self, request: RuntimeStopRequest) -> RuntimeStopResult:
            return RuntimeStopResult(
                runtime=RuntimeState(
                    agent_id=request.agent_id,
                    runtime_status=RuntimeStatus.STOPPED,
                    runtime_handle=request.runtime_handle,
                )
            )

        def status(self, request: RuntimeStatusRequest) -> RuntimeStatusResult:
            return RuntimeStatusResult(
                runtime=RuntimeState(
                    agent_id=request.agent_id,
                    runtime_status=RuntimeStatus.RUNNING,
                    runtime_handle="runtime-001",
                )
            )

        def logs(self, request: RuntimeLogsRequest) -> RuntimeLogsResult:
            return RuntimeLogsResult(
                runtime=RuntimeState(
                    agent_id=request.agent_id,
                    runtime_status=RuntimeStatus.RUNNING,
                    runtime_handle="runtime-001",
                ),
                lines=[f"tail={request.tail_lines}"],
            )

    assert inspect.isabstract(RuntimeAdapter)
    assert RuntimeAdapter.__abstractmethods__ == {"logs", "start", "status", "stop"}
    assert tuple(inspect.signature(RuntimeAdapter.start).parameters) == ("self", "request")
    assert tuple(inspect.signature(RuntimeAdapter.stop).parameters) == ("self", "request")
    assert tuple(inspect.signature(RuntimeAdapter.status).parameters) == ("self", "request")
    assert tuple(inspect.signature(RuntimeAdapter.logs).parameters) == ("self", "request")

    adapter = StubRuntimeAdapter()
    start_result = adapter.start(RuntimeStartRequest(agent=_build_agent()))
    stop_result = adapter.stop(
        RuntimeStopRequest(agent_id="agent-001", runtime_handle="runtime-001")
    )
    status_result = adapter.status(RuntimeStatusRequest(agent_id="agent-001"))
    logs_result = adapter.logs(RuntimeLogsRequest(agent_id="agent-001", tail_lines=10))

    assert start_result.runtime.runtime_status is RuntimeStatus.STARTING
    assert stop_result.runtime.runtime_status is RuntimeStatus.STOPPED
    assert status_result.runtime.runtime_status is RuntimeStatus.RUNNING
    assert logs_result.lines == ["tail=10"]
