from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.broker import (
    BrokerAckResult,
    BrokerDeliveryStatus,
    BrokerMessageEnvelope,
    BrokerPullResult,
    BrokerPublishResult,
    MessageBroker,
)
from maia.message_model import MessageKind, MessageRecord


def _build_message(message_id: str = "msg-001") -> MessageRecord:
    return MessageRecord(
        message_id=message_id,
        thread_id="thread-001",
        from_agent="planner",
        to_agent="reviewer",
        kind=MessageKind.QUESTION,
        body="Can you review the broker contract?",
        created_at="2026-04-15T11:00:00Z",
    )


def test_broker_delivery_status_values() -> None:
    assert BrokerDeliveryStatus.QUEUED.value == "queued"
    assert BrokerDeliveryStatus.DELIVERED.value == "delivered"
    assert BrokerDeliveryStatus.ACKNOWLEDGED.value == "acknowledged"
    assert BrokerDeliveryStatus.EMPTY.value == "empty"


def test_broker_message_envelope_round_trip() -> None:
    envelope = BrokerMessageEnvelope(
        message=_build_message(),
        receipt_handle="delivery-001",
    )

    restored = BrokerMessageEnvelope.from_dict(envelope.to_dict())

    assert restored == envelope
    assert restored.to_dict() == {
        "message": {
            "message_id": "msg-001",
            "thread_id": "thread-001",
            "from_agent": "planner",
            "to_agent": "reviewer",
            "kind": "question",
            "body": "Can you review the broker contract?",
            "created_at": "2026-04-15T11:00:00Z",
        },
        "receipt_handle": "delivery-001",
        "delivery_attempt": 1,
    }


def test_broker_message_envelope_round_trip_with_receipt_handle() -> None:
    envelope = BrokerMessageEnvelope(
        message=_build_message("msg-002"),
        delivery_attempt=2,
        receipt_handle="delivery-002",
    )

    restored = BrokerMessageEnvelope.from_dict(envelope.to_dict())

    assert restored == envelope
    assert restored.to_dict() == {
        "message": {
            "message_id": "msg-002",
            "thread_id": "thread-001",
            "from_agent": "planner",
            "to_agent": "reviewer",
            "kind": "question",
            "body": "Can you review the broker contract?",
            "created_at": "2026-04-15T11:00:00Z",
        },
        "delivery_attempt": 2,
        "receipt_handle": "delivery-002",
    }


def test_broker_message_envelope_missing_message_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid broker envelope: missing required fields: 'message'",
    ):
        BrokerMessageEnvelope.from_dict({"receipt_handle": "delivery-001"})


def test_broker_message_envelope_missing_receipt_handle_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid broker envelope: missing required fields: 'receipt_handle'",
    ):
        BrokerMessageEnvelope.from_dict({"message": _build_message().to_dict()})


def test_broker_message_envelope_invalid_receipt_handle_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid broker envelope receipt_handle: expected str",
    ):
        BrokerMessageEnvelope(
            message=_build_message(),
            receipt_handle=123,
        )


def test_broker_message_envelope_invalid_delivery_attempt_error() -> None:
    with pytest.raises(
        ValueError,
        match=r"Invalid broker envelope delivery_attempt: expected int >= 1",
    ):
        BrokerMessageEnvelope(
            message=_build_message(),
            receipt_handle="delivery-001",
            delivery_attempt=0,
        )


def test_broker_publish_result_round_trip() -> None:
    result = BrokerPublishResult(
        status=BrokerDeliveryStatus.QUEUED,
        message_id="msg-001",
    )

    restored = BrokerPublishResult.from_dict(result.to_dict())

    assert restored == result
    assert restored.to_dict() == {
        "status": "queued",
        "message_id": "msg-001",
    }


def test_broker_pull_result_round_trip_and_copies_messages_list() -> None:
    messages = [
        BrokerMessageEnvelope(
            message=_build_message(),
            receipt_handle="delivery-001",
        )
    ]

    result = BrokerPullResult(
        status=BrokerDeliveryStatus.DELIVERED,
        messages=messages,
    )

    assert result.messages is not messages

    messages.append(
        BrokerMessageEnvelope(
            message=_build_message("msg-002"),
            receipt_handle="delivery-002",
        )
    )

    restored = BrokerPullResult.from_dict(result.to_dict())

    assert len(result.messages) == 1
    assert restored == result
    assert restored.to_dict() == {
        "status": "delivered",
        "messages": [
            {
                "message": {
                    "message_id": "msg-001",
                    "thread_id": "thread-001",
                    "from_agent": "planner",
                    "to_agent": "reviewer",
                    "kind": "question",
                    "body": "Can you review the broker contract?",
                    "created_at": "2026-04-15T11:00:00Z",
                },
                "delivery_attempt": 1,
                "receipt_handle": "delivery-001",
            }
        ],
    }


def test_broker_ack_result_round_trip() -> None:
    result = BrokerAckResult(
        status=BrokerDeliveryStatus.ACKNOWLEDGED,
        message_id="msg-001",
        receipt_handle="delivery-001",
    )

    restored = BrokerAckResult.from_dict(result.to_dict())

    assert restored == result
    assert restored.to_dict() == {
        "status": "acknowledged",
        "message_id": "msg-001",
        "receipt_handle": "delivery-001",
    }


def test_broker_publish_result_invalid_status_error() -> None:
    with pytest.raises(ValueError, match="Invalid broker status: 'lost'"):
        BrokerPublishResult.from_dict(
            {
                "status": "lost",
                "message_id": "msg-001",
            }
        )


def test_broker_publish_result_rejects_non_queued_status() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid broker publish result status: expected BrokerDeliveryStatus.QUEUED",
    ):
        BrokerPublishResult(
            status=BrokerDeliveryStatus.DELIVERED,
            message_id="msg-001",
        )


@pytest.mark.parametrize(
    ("status", "messages", "match"),
    [
        (
            BrokerDeliveryStatus.QUEUED,
            [],
            "Invalid broker pull result status: expected BrokerDeliveryStatus.DELIVERED or BrokerDeliveryStatus.EMPTY",
        ),
        (
            BrokerDeliveryStatus.DELIVERED,
            [],
            "Invalid broker pull result messages: expected at least one message when status is BrokerDeliveryStatus.DELIVERED",
        ),
        (
            BrokerDeliveryStatus.EMPTY,
            [
                BrokerMessageEnvelope(
                    message=_build_message(),
                    receipt_handle="delivery-001",
                )
            ],
            "Invalid broker pull result messages: expected no messages when status is BrokerDeliveryStatus.EMPTY",
        ),
    ],
)
def test_broker_pull_result_rejects_invalid_status_combinations(
    status: BrokerDeliveryStatus,
    messages: list[BrokerMessageEnvelope],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        BrokerPullResult(
            status=status,
            messages=messages,
        )


def test_broker_ack_result_rejects_non_acknowledged_status() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid broker ack result status: expected BrokerDeliveryStatus.ACKNOWLEDGED",
    ):
        BrokerAckResult(
            status=BrokerDeliveryStatus.DELIVERED,
            message_id="msg-001",
            receipt_handle="delivery-001",
        )


def test_message_broker_interface_contract() -> None:
    class StubBroker(MessageBroker):
        def publish(self, message: MessageRecord) -> BrokerPublishResult:
            return BrokerPublishResult(
                status=BrokerDeliveryStatus.QUEUED,
                message_id=message.message_id,
            )

        def pull(self, *, agent_id: str, limit: int = 1) -> BrokerPullResult:
            assert agent_id == "reviewer"
            assert limit == 1
            return BrokerPullResult(
                status=BrokerDeliveryStatus.DELIVERED,
                messages=[
                    BrokerMessageEnvelope(
                        message=_build_message(),
                        receipt_handle="delivery-001",
                    )
                ],
            )

        def ack(self, envelope: BrokerMessageEnvelope) -> BrokerAckResult:
            return BrokerAckResult(
                status=BrokerDeliveryStatus.ACKNOWLEDGED,
                message_id=envelope.message.message_id,
                receipt_handle=envelope.receipt_handle,
            )

    assert inspect.isabstract(MessageBroker)
    assert MessageBroker.__abstractmethods__ == {"ack", "publish", "pull"}
    assert tuple(inspect.signature(MessageBroker.publish).parameters) == ("self", "message")
    assert tuple(inspect.signature(MessageBroker.pull).parameters) == (
        "self",
        "agent_id",
        "limit",
    )
    assert inspect.signature(MessageBroker.pull).parameters["agent_id"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert inspect.signature(MessageBroker.pull).parameters["limit"].default == 1
    assert tuple(inspect.signature(MessageBroker.ack).parameters) == ("self", "envelope")

    broker = StubBroker()
    message = _build_message()

    publish_result = broker.publish(message)
    pull_result = broker.pull(agent_id="reviewer")
    ack_result = broker.ack(pull_result.messages[0])

    assert publish_result.status is BrokerDeliveryStatus.QUEUED
    assert pull_result.status is BrokerDeliveryStatus.DELIVERED
    assert ack_result.status is BrokerDeliveryStatus.ACKNOWLEDGED
