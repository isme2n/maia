from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.broker import BrokerDeliveryStatus, BrokerMessageEnvelope
from maia.message_model import MessageKind, MessageRecord
from maia.rabbitmq_broker import RabbitMQBroker


def _build_message(message_id: str = "msg-001", *, to_agent: str = "reviewer") -> MessageRecord:
    return MessageRecord(
        message_id=message_id,
        thread_id="thread-001",
        from_agent="planner",
        to_agent=to_agent,
        kind=MessageKind.QUESTION,
        body="Can you review the broker adapter?",
        created_at="2026-04-15T11:00:00Z",
    )


class FakeBrokerError(Exception):
    def __init__(self, message: str, *, reply_code: int | None = None) -> None:
        super().__init__(message)
        self.reply_code = reply_code


@dataclass
class FakeBasicProperties:
    content_type: str
    delivery_mode: int
    message_id: str
    type: str
    headers: dict[str, str]


class FakePika:
    BasicProperties = FakeBasicProperties

    @staticmethod
    def URLParameters(value: str) -> str:
        return f"url::{value}"


class FakeChannel:
    def __init__(self) -> None:
        self.is_open = True
        self.queue_declare_calls: list[dict[str, object]] = []
        self.basic_publish_calls: list[dict[str, object]] = []
        self.basic_get_results: list[tuple[object, object, object]] = []
        self.basic_get_calls: list[dict[str, object]] = []
        self.basic_ack_calls: list[dict[str, object]] = []
        self.queue_declare_error: Exception | None = None
        self.basic_publish_error: Exception | None = None
        self.basic_get_error: Exception | None = None
        self.basic_ack_error: Exception | None = None
        self.closed = False

    def queue_declare(self, **kwargs: object) -> None:
        self.queue_declare_calls.append(kwargs)
        if self.queue_declare_error is not None:
            raise self.queue_declare_error

    def basic_publish(self, **kwargs: object) -> None:
        self.basic_publish_calls.append(kwargs)
        if self.basic_publish_error is not None:
            raise self.basic_publish_error

    def basic_get(self, **kwargs: object) -> tuple[object, object, object]:
        self.basic_get_calls.append(kwargs)
        if self.basic_get_error is not None:
            raise self.basic_get_error
        if self.basic_get_results:
            return self.basic_get_results.pop(0)
        return (None, None, None)

    def basic_ack(self, **kwargs: object) -> None:
        self.basic_ack_calls.append(kwargs)
        if self.basic_ack_error is not None:
            raise self.basic_ack_error

    def close(self) -> None:
        self.closed = True
        self.is_open = False


class FakeConnection:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel
        self.is_open = True
        self.closed = False
        self.channel_calls = 0

    def channel(self) -> FakeChannel:
        self.channel_calls += 1
        return self._channel

    def close(self) -> None:
        self.closed = True
        self.is_open = False


def _build_broker(channel: FakeChannel | None = None) -> tuple[RabbitMQBroker, FakeChannel, FakeConnection]:
    fake_channel = channel or FakeChannel()
    fake_connection = FakeConnection(fake_channel)
    broker = RabbitMQBroker(
        broker_url="amqp://guest:guest@localhost:5672/%2F",
        pika_module=FakePika(),
        connection_factory=lambda parameters: fake_connection,
    )
    return broker, fake_channel, fake_connection


def test_publish_declares_agent_queue_and_returns_publish_result() -> None:
    broker, channel, _connection = _build_broker()

    result = broker.publish(_build_message())

    assert result.status is BrokerDeliveryStatus.QUEUED
    assert result.message_id == "msg-001"
    assert channel.queue_declare_calls == [
        {"queue": "maia.inbox.reviewer", "durable": True}
    ]
    publish_call = channel.basic_publish_calls[0]
    assert publish_call["exchange"] == ""
    assert publish_call["routing_key"] == "maia.inbox.reviewer"
    assert publish_call["body"] == (
        b'{"body": "Can you review the broker adapter?", "created_at": '
        b'"2026-04-15T11:00:00Z", "from_agent": "planner", "kind": '
        b'"question", "message_id": "msg-001", "thread_id": '
        b'"thread-001", "to_agent": "reviewer"}'
    )
    assert publish_call["properties"] == FakeBasicProperties(
        content_type="application/json",
        delivery_mode=2,
        message_id="msg-001",
        type="question",
        headers={},
    )


def test_publish_with_thread_topic_sets_message_headers() -> None:
    broker, channel, _connection = _build_broker()

    result = broker.publish_with_metadata(_build_message(), thread_topic="phase 6 review")

    assert result.status is BrokerDeliveryStatus.QUEUED
    publish_call = channel.basic_publish_calls[0]
    assert publish_call["properties"].headers == {"maia_thread_topic": "phase 6 review"}


def test_pull_returns_delivered_envelope_with_delivery_attempt() -> None:
    broker, channel, _connection = _build_broker()
    channel.basic_get_results = [
        (
            SimpleNamespace(delivery_tag=7, redelivered=True),
            SimpleNamespace(headers={"x-delivery-count": 3, "maia_thread_topic": "phase 6 review"}),
            (
                b'{"message_id":"msg-001","thread_id":"thread-001","from_agent":"planner",'
                b'"to_agent":"reviewer","kind":"question","body":"Can you review the broker adapter?",'
                b'"created_at":"2026-04-15T11:00:00Z"}'
            ),
        ),
        (None, None, None),
    ]

    result = broker.pull(agent_id="reviewer", limit=2)

    assert result.status is BrokerDeliveryStatus.DELIVERED
    assert len(result.messages) == 1
    envelope = result.messages[0]
    assert envelope == BrokerMessageEnvelope(
        message=_build_message(),
        receipt_handle="7",
        delivery_attempt=3,
    )
    assert channel.queue_declare_calls == [
        {"queue": "maia.inbox.reviewer", "passive": True}
    ]
    assert channel.basic_get_calls == [
        {"queue": "maia.inbox.reviewer", "auto_ack": False},
        {"queue": "maia.inbox.reviewer", "auto_ack": False},
    ]


def test_pull_with_metadata_returns_thread_topic() -> None:
    broker, channel, _connection = _build_broker()
    channel.basic_get_results = [
        (
            SimpleNamespace(delivery_tag=7, redelivered=False),
            SimpleNamespace(headers={"maia_thread_topic": "phase 6 review"}),
            (
                b'{"message_id":"msg-001","thread_id":"thread-001","from_agent":"planner",'
                b'"to_agent":"reviewer","kind":"question","body":"Can you review the broker adapter?",'
                b'"created_at":"2026-04-15T11:00:00Z"}'
            ),
        ),
        (None, None, None),
    ]

    pulled = broker.pull_with_metadata(agent_id="reviewer", limit=1)

    assert pulled[0][1] == {"thread_topic": "phase 6 review"}


def test_pull_missing_queue_returns_empty_result() -> None:
    broker, channel, _connection = _build_broker()
    channel.queue_declare_error = FakeBrokerError("NOT_FOUND - no queue", reply_code=404)

    result = broker.pull(agent_id="reviewer")

    assert result.status is BrokerDeliveryStatus.EMPTY
    assert result.messages == []
    assert channel.basic_get_calls == []


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (b"not-json", "body is not valid JSON"),
        (b"[]", "expected message object"),
        (b"\x80\x81", "body is not valid UTF-8"),
        (
            b'{"thread_id":"thread-001"}',
            "Invalid message record: missing required fields",
        ),
    ],
)
def test_pull_surfaces_malformed_payload_as_value_error(body: bytes, match: str) -> None:
    broker, channel, _connection = _build_broker()
    channel.basic_get_results = [
        (SimpleNamespace(delivery_tag=7, redelivered=False, headers={}), None, body)
    ]

    with pytest.raises(ValueError, match=match):
        broker.pull(agent_id="reviewer")


def test_ack_requires_numeric_receipt_handle_and_returns_ack_result() -> None:
    broker, channel, _connection = _build_broker()
    envelope = BrokerMessageEnvelope(message=_build_message(), receipt_handle="9")

    result = broker.ack(envelope)

    assert result.status is BrokerDeliveryStatus.ACKNOWLEDGED
    assert result.message_id == "msg-001"
    assert result.receipt_handle == "9"
    assert channel.basic_ack_calls == [{"delivery_tag": 9}]


def test_ack_rejects_non_numeric_receipt_handle() -> None:
    broker, _channel, _connection = _build_broker()
    envelope = BrokerMessageEnvelope(message=_build_message(), receipt_handle="delivery-9")

    with pytest.raises(ValueError, match="numeric receipt_handle"):
        broker.ack(envelope)


def test_ack_rejects_receipt_handle_below_one() -> None:
    broker, _channel, _connection = _build_broker()
    envelope = BrokerMessageEnvelope(message=_build_message(), receipt_handle="0")

    with pytest.raises(ValueError, match=r"receipt_handle >= 1"):
        broker.ack(envelope)


def test_connection_failures_are_operator_facing_value_errors() -> None:
    broker = RabbitMQBroker(
        broker_url="amqp://guest:guest@localhost:5672/%2F",
        pika_module=FakePika(),
        connection_factory=lambda parameters: (_ for _ in ()).throw(
            FakeBrokerError("socket unavailable")
        ),
    )

    with pytest.raises(ValueError, match="RabbitMQ broker connection failed: socket unavailable"):
        broker.publish(_build_message())


def test_close_releases_channel_then_connection() -> None:
    broker, _channel, _connection = _build_broker()
    broker.publish(_build_message())
    channel = broker._channel
    connection = broker._connection
    assert channel is not None
    assert connection is not None

    broker.close()

    assert channel.closed is True
    assert connection.closed is True
    assert broker._channel is None
    assert broker._connection is None


def test_context_manager_closes_resources() -> None:
    fake_channel = FakeChannel()
    fake_connection = FakeConnection(fake_channel)

    with RabbitMQBroker(
        broker_url="amqp://guest:guest@localhost:5672/%2F",
        pika_module=FakePika(),
        connection_factory=lambda parameters: fake_connection,
    ) as broker:
        broker.publish(_build_message())

    assert fake_channel.closed is True
    assert fake_connection.closed is True
