from __future__ import annotations

from subprocess import CompletedProcess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from maia.broker import BrokerDeliveryStatus, BrokerMessageEnvelope, BrokerPullResult
from maia.message_model import MessageKind, MessageRecord
from maia.hermes_runtime_worker import WorkerConfig, default_hermes_runner, process_once


class FakeBroker:
    def __init__(self, envelopes: list[BrokerMessageEnvelope]) -> None:
        self._envelopes = list(envelopes)
        self.published: list[MessageRecord] = []
        self.acked: list[str] = []
        self.close_calls = 0

    def pull(self, *, agent_id: str, limit: int = 1) -> BrokerPullResult:
        messages = self._envelopes[:limit]
        self._envelopes = self._envelopes[limit:]
        if not messages:
            return BrokerPullResult(status=BrokerDeliveryStatus.EMPTY, messages=[])
        return BrokerPullResult(status=BrokerDeliveryStatus.DELIVERED, messages=messages)

    def publish(self, message: MessageRecord):
        self.published.append(message)
        return None

    def ack(self, envelope: BrokerMessageEnvelope):
        self.acked.append(envelope.receipt_handle)
        return None

    def close(self) -> None:
        self.close_calls += 1


def _message() -> MessageRecord:
    return MessageRecord(
        message_id="msg-001",
        thread_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind=MessageKind.REQUEST,
        body="Please review the latest patch.",
        created_at="2026-04-16T00:00:00Z",
    )


def test_process_once_publishes_reply_and_acks() -> None:
    envelope = BrokerMessageEnvelope(message=_message(), receipt_handle="7", delivery_attempt=1)
    broker = FakeBroker([envelope])
    seen_prompts: list[str] = []

    def hermes_runner(prompt: str, *, config: WorkerConfig) -> str:
        seen_prompts.append(prompt)
        assert config.agent_id == "reviewer"
        return "Looks good. Ship it."

    processed = process_once(
        WorkerConfig(agent_id="reviewer", agent_name="Reviewer"),
        broker=broker,
        hermes_runner=hermes_runner,
    )

    assert processed is True
    assert seen_prompts and "Please review the latest patch." in seen_prompts[0]
    assert len(broker.published) == 1
    reply = broker.published[0]
    assert reply.thread_id == "thread-001"
    assert reply.from_agent == "reviewer"
    assert reply.to_agent == "planner"
    assert reply.reply_to_message_id == "msg-001"
    assert reply.kind is MessageKind.ANSWER
    assert reply.body == "Looks good. Ship it."
    assert broker.acked == ["7"]


def test_process_once_leaves_message_unacked_when_hermes_fails() -> None:
    envelope = BrokerMessageEnvelope(message=_message(), receipt_handle="7", delivery_attempt=1)
    broker = FakeBroker([envelope])

    def hermes_runner(prompt: str, *, config: WorkerConfig) -> str:
        raise RuntimeError("model is not configured")

    processed = process_once(
        WorkerConfig(agent_id="reviewer", agent_name="Reviewer"),
        broker=broker,
        hermes_runner=hermes_runner,
    )

    assert processed is False
    assert broker.published == []
    assert broker.acked == []
    assert broker.close_calls == 1


def test_process_once_returns_false_for_empty_pull() -> None:
    broker = FakeBroker([])

    processed = process_once(
        WorkerConfig(agent_id="reviewer", agent_name="Reviewer"),
        broker=broker,
        hermes_runner=lambda prompt, *, config: "unused",
    )

    assert processed is False
    assert broker.published == []
    assert broker.acked == []


def test_default_hermes_runner_uses_quiet_chat_mode() -> None:
    config = WorkerConfig(agent_id="reviewer", agent_name="Reviewer", hermes_bin="hermes")
    with patch("maia.hermes_runtime_worker.subprocess.run", return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr="")) as run_mock:
        reply = default_hermes_runner("hello", config=config)

    assert reply == "ok"
    assert run_mock.call_args.args[0] == ["hermes", "chat", "-Q", "-q", "hello"]
