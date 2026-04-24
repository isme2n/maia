from __future__ import annotations

import subprocess
from subprocess import CompletedProcess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from maia.hermes_runtime_worker import (
    HttpKeryxClient,
    WorkerConfig,
    build_prompt,
    default_hermes_runner,
    load_config_from_env,
    process_once,
    run_forever,
    start_gateway_bridge,
    stop_gateway_bridge,
)
from maia.keryx_models import (
    KeryxAgentSummary,
    KeryxHandoffStatus,
    KeryxMessageKind,
    KeryxPendingThreadWorkView,
    KeryxThreadHandoffView,
    KeryxThreadMessageView,
    KeryxThreadView,
)


class FakeKeryxClient:
    def __init__(self, pending_items: list[KeryxPendingThreadWorkView]) -> None:
        self._pending_items = list(pending_items)
        self.roster = [
            KeryxAgentSummary(
                agent_id="planner",
                name="planner",
                role="planner",
                call_sign="planner",
                speaking_style="respectful",
                persona="Careful planner who summarizes tradeoffs clearly.",
                status="running",
                setup_status="complete",
                runtime_status="running",
            ),
            KeryxAgentSummary(
                agent_id="reviewer",
                name="reviewer",
                role="reviewer",
                call_sign="planner",
                speaking_style="custom",
                speaking_style_details="Respond in warm, concise Korean.",
                persona="Sharp reviewer focused on direct code feedback.",
                status="running",
                setup_status="complete",
                runtime_status="running",
            ),
        ]
        self.thread_messages = {
            item.thread.thread_id: [item.message] for item in pending_items
        }
        self.thread_handoffs = {
            item.thread.thread_id: [item.handoff] for item in pending_items
        }
        self.created_messages: list[KeryxThreadMessageView] = []
        self.updated_handoffs: list[KeryxThreadHandoffView] = []

    def list_agents(self) -> list[KeryxAgentSummary]:
        return list(self.roster)

    def list_pending_work(
        self,
        *,
        agent_id: str,
        limit: int = 1,
    ) -> list[KeryxPendingThreadWorkView]:
        return [
            item
            for item in self._pending_items
            if item.handoff.to_agent == agent_id
        ][:limit]

    def list_thread_messages(self, thread_id: str) -> list[KeryxThreadMessageView]:
        return list(self.thread_messages[thread_id])

    def list_thread_handoffs(self, thread_id: str) -> list[KeryxThreadHandoffView]:
        return list(self.thread_handoffs[thread_id])

    def create_thread_message(
        self,
        thread_id: str,
        record: KeryxThreadMessageView,
    ) -> KeryxThreadMessageView:
        assert record.thread_id == thread_id
        self.created_messages.append(record)
        self.thread_messages.setdefault(thread_id, []).append(record)
        return record

    def update_thread_handoff(
        self,
        handoff_id: str,
        record: KeryxThreadHandoffView,
    ) -> KeryxThreadHandoffView:
        assert record.handoff_id == handoff_id
        self.updated_handoffs.append(record)
        self.thread_handoffs[record.thread_id] = [record]
        return record


class FakeBridgeProcess:
    def __init__(
        self,
        *,
        returncode: int | None = None,
        timeout_on_terminate: bool = False,
    ) -> None:
        self.command: list[str] | None = None
        self.returncode = returncode
        self.timeout_on_terminate = timeout_on_terminate
        self.terminated = False
        self.killed = False
        self.wait_calls: list[float | None] = []

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if self.timeout_on_terminate:
            self.timeout_on_terminate = False
            raise subprocess.TimeoutExpired(self.command or ["python"], timeout or 0)
        if self.returncode is None:
            self.returncode = -15 if self.terminated else 0
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def _message() -> KeryxThreadMessageView:
    return KeryxThreadMessageView(
        message_id="msg-001",
        thread_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind=KeryxMessageKind.REQUEST.value,
        body="Please review the latest patch.",
        created_at="2026-04-16T00:00:00Z",
    )


def _pending_work() -> KeryxPendingThreadWorkView:
    thread = KeryxThreadView(
        thread_id="thread-001",
        topic="runtime review",
        participants=["planner", "reviewer"],
        created_by="planner",
        status="active",
        created_at="2026-04-17T02:00:00Z",
        updated_at="2026-04-17T02:02:00Z",
    )
    handoff = KeryxThreadHandoffView(
        handoff_id="handoff-001",
        thread_id=thread.thread_id,
        from_agent="planner",
        to_agent="reviewer",
        kind="file",
        status=KeryxHandoffStatus.OPEN.value,
        summary="Patch review note",
        location="/tmp/review.md",
        created_at="2026-04-17T02:02:00Z",
        updated_at="2026-04-17T02:02:00Z",
    )
    return KeryxPendingThreadWorkView(thread=thread, message=_message(), handoff=handoff)


def test_process_once_publishes_reply_and_marks_handoff_done() -> None:
    keryx_client = FakeKeryxClient([_pending_work()])
    seen_prompts: list[str] = []

    def hermes_runner(prompt: str, *, config: WorkerConfig) -> str:
        seen_prompts.append(prompt)
        assert config.agent_id == "reviewer"
        return "Looks good. Ship it."

    processed = process_once(
        WorkerConfig(
            agent_id="reviewer",
            agent_name="Reviewer",
            keryx_base_url="http://keryx.test",
        ),
        keryx_client=keryx_client,
        hermes_runner=hermes_runner,
    )

    assert processed is True
    assert seen_prompts and "Please review the latest patch." in seen_prompts[0]
    assert len(keryx_client.created_messages) == 1
    reply = keryx_client.created_messages[0]
    assert reply.thread_id == "thread-001"
    assert reply.from_agent == "reviewer"
    assert reply.to_agent == "planner"
    assert reply.reply_to_message_id == "msg-001"
    assert reply.kind == KeryxMessageKind.ANSWER.value
    assert reply.body == "Looks good. Ship it."
    assert not hasattr(reply, "session_id")
    assert len(keryx_client.updated_handoffs) == 1
    assert keryx_client.updated_handoffs[0].handoff_id == "handoff-001"
    assert keryx_client.updated_handoffs[0].status == KeryxHandoffStatus.DONE.value
    assert not hasattr(keryx_client.updated_handoffs[0], "session_id")


def test_process_once_leaves_work_unmodified_when_hermes_fails() -> None:
    keryx_client = FakeKeryxClient([_pending_work()])

    def hermes_runner(prompt: str, *, config: WorkerConfig) -> str:
        raise RuntimeError("model is not configured")

    processed = process_once(
        WorkerConfig(
            agent_id="reviewer",
            agent_name="Reviewer",
            keryx_base_url="http://keryx.test",
        ),
        keryx_client=keryx_client,
        hermes_runner=hermes_runner,
    )

    assert processed is False
    assert keryx_client.created_messages == []
    assert keryx_client.updated_handoffs == []


def test_process_once_returns_false_for_empty_pending_work() -> None:
    keryx_client = FakeKeryxClient([])

    processed = process_once(
        WorkerConfig(
            agent_id="reviewer",
            agent_name="Reviewer",
            keryx_base_url="http://keryx.test",
        ),
        keryx_client=keryx_client,
        hermes_runner=lambda prompt, *, config: "unused",
    )

    assert processed is False
    assert keryx_client.created_messages == []
    assert keryx_client.updated_handoffs == []


def test_default_hermes_runner_uses_quiet_chat_mode() -> None:
    config = WorkerConfig(agent_id="reviewer", agent_name="Reviewer", hermes_bin="hermes")
    with patch(
        "maia.hermes_runtime_worker.subprocess.run",
        return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
    ) as run_mock:
        reply = default_hermes_runner("hello", config=config)

    assert reply == "ok"
    assert run_mock.call_args.args[0] == ["hermes", "chat", "-Q", "-q", "hello"]


def test_load_config_from_env_requires_keryx_base_url() -> None:
    with pytest.raises(ValueError, match="KERYX_BASE_URL is required"):
        load_config_from_env(
            {
                "MAIA_AGENT_ID": "reviewer",
                "MAIA_AGENT_NAME": "Reviewer",
            }
        )


def test_load_config_from_env_derives_token_only_gateway_status(tmp_path: Path) -> None:
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("TELEGRAM_BOT_TOKEN=test-token\n", encoding="utf-8")

    config = load_config_from_env(
        {
            "MAIA_AGENT_ID": "reviewer",
            "MAIA_AGENT_NAME": "Reviewer",
            "KERYX_BASE_URL": "http://keryx.test",
            "HERMES_HOME": str(hermes_home),
        }
    )

    assert config.gateway_setup_status == "token-only"


@pytest.mark.parametrize("gateway_setup_status", ["complete", "token-only"])
def test_start_gateway_bridge_launches_for_start_ready_gateway_status(
    gateway_setup_status: str,
) -> None:
    process = FakeBridgeProcess()
    commands: list[list[str]] = []
    config = WorkerConfig(
        agent_id="reviewer",
        agent_name="Reviewer",
        keryx_base_url="http://keryx.test",
        gateway_setup_status=gateway_setup_status,
        gateway_bridge_command=("python", "-m", "maia.hermes_gateway_bridge"),
    )

    started = start_gateway_bridge(
        config,
        popen_factory=lambda command: commands.append(command) or process,
    )

    assert started is process
    assert commands == [["python", "-m", "maia.hermes_gateway_bridge"]]


def test_start_gateway_bridge_skips_incomplete_gateway_status() -> None:
    config = WorkerConfig(
        agent_id="reviewer",
        agent_name="Reviewer",
        keryx_base_url="http://keryx.test",
        gateway_setup_status="incomplete",
    )

    started = start_gateway_bridge(
        config,
        popen_factory=lambda command: pytest.fail(f"unexpected bridge launch: {command}"),
    )

    assert started is None


def test_stop_gateway_bridge_kills_unresponsive_child() -> None:
    process = FakeBridgeProcess(timeout_on_terminate=True)

    stop_gateway_bridge(process, timeout_seconds=3.5)

    assert process.terminated is True
    assert process.killed is True
    assert process.wait_calls == [3.5, 3.5]


def test_run_forever_stops_gateway_bridge_on_shutdown() -> None:
    process = FakeBridgeProcess()
    config = WorkerConfig(
        agent_id="reviewer",
        agent_name="Reviewer",
        keryx_base_url="http://keryx.test",
        gateway_setup_status="token-only",
        gateway_bridge_command=("python", "-m", "maia.hermes_gateway_bridge"),
        gateway_bridge_shutdown_seconds=1.25,
    )

    def popen_factory(command: list[str]) -> FakeBridgeProcess:
        process.command = command
        return process

    def sleep_fn(seconds: float) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_forever(
            config,
            keryx_client=FakeKeryxClient([]),
            hermes_runner=lambda prompt, *, config: "unused",
            sleep_fn=sleep_fn,
            popen_factory=popen_factory,
        )

    assert process.command == ["python", "-m", "maia.hermes_gateway_bridge"]
    assert process.terminated is True
    assert process.killed is False
    assert process.wait_calls == [1.25]


def test_run_forever_raises_when_gateway_bridge_exits_early() -> None:
    process = FakeBridgeProcess(returncode=17)
    config = WorkerConfig(
        agent_id="reviewer",
        agent_name="Reviewer",
        keryx_base_url="http://keryx.test",
        gateway_setup_status="complete",
    )

    with pytest.raises(RuntimeError, match="Gateway bridge exited unexpectedly with code 17"):
        run_forever(
            config,
            keryx_client=FakeKeryxClient([]),
            hermes_runner=lambda prompt, *, config: "unused",
            sleep_fn=lambda seconds: None,
            popen_factory=lambda command: process,
        )


def test_build_prompt_includes_keryx_runtime_context() -> None:
    pending_work = _pending_work()
    prompt = build_prompt(
        WorkerConfig(
            agent_id="reviewer",
            agent_name="Reviewer",
            keryx_base_url="http://keryx.test",
        ),
        pending_work,
        roster=FakeKeryxClient([pending_work]).list_agents(),
        recent_messages=[pending_work.message],
        recent_handoffs=[pending_work.handoff],
    )

    assert "Current Maia context:" in prompt
    assert "You are Reviewer." in prompt
    assert "agent_id=reviewer" in prompt
    assert 'Call the user "planner".' in prompt
    assert "Use a custom speaking style." in prompt
    assert "Custom speaking style details: Respond in warm, concise Korean." in prompt
    assert "Persona: Sharp reviewer focused on direct code feedback." in prompt
    assert "Known team roster:" in prompt
    assert "planner (agent_id=planner, role=planner, runtime=running)" in prompt
    assert "reviewer (agent_id=reviewer, role=reviewer, runtime=running)" in prompt
    assert "Active thread:" in prompt
    assert "thread_id=thread-001" in prompt
    assert "Recent thread messages:" in prompt
    assert "Recent handoffs for this thread:" in prompt
    assert "Reply as this agent to the incoming Maia thread message below." in prompt
    assert "thread_id: thread-001" in prompt
    assert "Active session:" not in prompt
    assert "session_id:" not in prompt
    assert "message_body:" in prompt
    assert not hasattr(pending_work.thread, "session_id")


def test_http_keryx_client_surfaces_http_errors() -> None:
    client = HttpKeryxClient("http://127.0.0.1:9")

    with pytest.raises(ValueError, match="Keryx request failed"):
        client.list_agents()
