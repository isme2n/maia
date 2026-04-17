"""Minimal broker-driven Hermes runtime worker for Maia containers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import os
import subprocess
import sys
import time
import uuid

from maia.agent_context import build_runtime_context, format_runtime_context_for_prompt
from maia.broker import BrokerDeliveryStatus, BrokerMessageEnvelope, MessageBroker
from maia.message_model import MessageKind, MessageRecord
from maia.rabbitmq_broker import RabbitMQBroker

__all__ = [
    "WorkerConfig",
    "build_prompt",
    "default_hermes_runner",
    "load_config_from_env",
    "main",
    "process_once",
    "run_forever",
]


@dataclass(slots=True)
class WorkerConfig:
    agent_id: str
    agent_name: str
    broker_url: str = ""
    state_db_path: str = ""
    poll_seconds: float = 2.0
    max_messages_per_poll: int = 1
    hermes_bin: str = "hermes"
    reply_kind: MessageKind = MessageKind.ANSWER


HermesRunner = Callable[[str], str] | Callable[[str, "WorkerConfig"], str]


def load_config_from_env(env: dict[str, str] | None = None) -> WorkerConfig:
    source = os.environ if env is None else env
    agent_id = source.get("MAIA_AGENT_ID", "").strip()
    if not agent_id:
        raise ValueError("MAIA_AGENT_ID is required")
    broker_url = source.get("MAIA_BROKER_URL", "").strip()
    if not broker_url:
        raise ValueError("MAIA_BROKER_URL is required")
    state_db_path = source.get("MAIA_STATE_DB_PATH", "").strip()
    if not state_db_path:
        raise ValueError("MAIA_STATE_DB_PATH is required")
    agent_name = source.get("MAIA_AGENT_NAME", "").strip() or agent_id
    return WorkerConfig(
        agent_id=agent_id,
        agent_name=agent_name,
        broker_url=broker_url,
        state_db_path=state_db_path,
        poll_seconds=float(source.get("MAIA_POLL_SECONDS", "2")),
        max_messages_per_poll=int(source.get("MAIA_MAX_MESSAGES_PER_POLL", "1")),
        hermes_bin=source.get("MAIA_HERMES_BIN", "hermes").strip() or "hermes",
        reply_kind=MessageKind(source.get("MAIA_HERMES_REPLY_KIND", MessageKind.ANSWER.value)),
    )


def build_prompt(config: WorkerConfig, envelope: BrokerMessageEnvelope) -> str:
    message = envelope.message
    context_block = ""
    if config.state_db_path:
        try:
            runtime_context = build_runtime_context(
                config.state_db_path,
                agent_id=config.agent_id,
                incoming_message=message,
            )
        except ValueError as exc:
            raise ValueError(f"Maia runtime context is unavailable: {exc}") from exc
        context_block = f"{format_runtime_context_for_prompt(runtime_context)}\n\n"
    return (
        f"You are Maia agent {config.agent_name} (agent_id={config.agent_id}).\n\n"
        f"{context_block}"
        "Reply as this agent to the incoming Maia thread message below.\n"
        "Keep the answer direct and useful. Return only the reply body.\n\n"
        f"thread_id: {message.thread_id}\n"
        f"from_agent: {message.from_agent}\n"
        f"to_agent: {message.to_agent}\n"
        f"message_kind: {message.kind.value}\n"
        f"message_id: {message.message_id}\n"
        f"message_body:\n{message.body}\n"
    )


def default_hermes_runner(prompt: str, *, config: WorkerConfig) -> str:
    completed = subprocess.run(
        [config.hermes_bin, "chat", "-Q", "-q", prompt],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "hermes command failed").strip()
        raise ValueError(f"Hermes runtime query failed: {detail}")
    reply = completed.stdout.strip()
    if not reply:
        raise ValueError("Hermes runtime query failed: empty response")
    return reply


def process_once(
    config: WorkerConfig,
    *,
    broker: MessageBroker,
    hermes_runner: Callable[..., str] = default_hermes_runner,
) -> bool:
    pull_result = broker.pull(agent_id=config.agent_id, limit=config.max_messages_per_poll)
    if pull_result.status is BrokerDeliveryStatus.EMPTY or not pull_result.messages:
        return False

    processed_any = False
    for envelope in pull_result.messages:
        try:
            prompt = build_prompt(config, envelope)
            reply_body = hermes_runner(prompt, config=config)
        except Exception as exc:
            if hasattr(broker, "close"):
                broker.close()
            print(f"worker agent_id={config.agent_id} status=hermes-error detail={exc}", file=sys.stderr)
            return False
        reply = MessageRecord(
            message_id=_new_id(),
            thread_id=envelope.message.thread_id,
            from_agent=config.agent_id,
            to_agent=envelope.message.from_agent,
            kind=config.reply_kind,
            body=reply_body,
            created_at=_timestamp_now(),
            reply_to_message_id=envelope.message.message_id,
        )
        broker.publish(reply)
        broker.ack(envelope)
        processed_any = True
    return processed_any


def run_forever(
    config: WorkerConfig,
    *,
    broker: MessageBroker,
    hermes_runner: Callable[..., str] = default_hermes_runner,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    while True:
        processed = process_once(config, broker=broker, hermes_runner=hermes_runner)
        if not processed:
            sleep_fn(config.poll_seconds)


def main() -> int:
    config = load_config_from_env()
    with RabbitMQBroker(broker_url=config.broker_url) as broker:
        run_forever(config, broker=broker)
    return 0


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _timestamp_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
