"""Broker contract primitives for Maia message transport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from maia.message_model import MessageRecord

__all__ = [
    "BrokerAckResult",
    "BrokerDeliveryStatus",
    "BrokerMessageEnvelope",
    "BrokerPullResult",
    "BrokerPublishResult",
    "MessageBroker",
]


def _validate_str(value: object, *, error: str) -> None:
    if not isinstance(value, str):
        raise ValueError(error)


def _validate_delivery_attempt(value: object) -> int:
    if not isinstance(value, int) or value < 1:
        raise ValueError("Invalid broker envelope delivery_attempt: expected int >= 1")
    return value


def _parse_broker_status(value: object) -> "BrokerDeliveryStatus":
    try:
        return (
            value
            if isinstance(value, BrokerDeliveryStatus)
            else BrokerDeliveryStatus(value)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid broker status: {value!r}") from exc


def _validate_message_record(value: object) -> None:
    if not isinstance(value, MessageRecord):
        raise ValueError("Invalid broker envelope message: expected MessageRecord")


def _validate_envelope_list(value: object) -> list["BrokerMessageEnvelope"]:
    if not isinstance(value, list) or any(
        not isinstance(item, BrokerMessageEnvelope) for item in value
    ):
        raise ValueError(
            "Invalid broker pull result messages: expected list[BrokerMessageEnvelope]"
        )
    return list(value)


def _load_message_record(data: object) -> MessageRecord:
    if not isinstance(data, Mapping):
        raise ValueError("Invalid broker envelope message: expected object")
    return MessageRecord.from_dict(data)


def _load_envelope_list(data: object) -> list["BrokerMessageEnvelope"]:
    if not isinstance(data, list) or any(not isinstance(item, Mapping) for item in data):
        raise ValueError("Invalid broker pull result messages: expected list[object]")
    return [BrokerMessageEnvelope.from_dict(item) for item in data]


def _validate_publish_status(value: object) -> "BrokerDeliveryStatus":
    if not isinstance(value, BrokerDeliveryStatus):
        raise ValueError("Invalid broker publish result status: expected BrokerDeliveryStatus")
    if value is not BrokerDeliveryStatus.QUEUED:
        raise ValueError(
            "Invalid broker publish result status: expected BrokerDeliveryStatus.QUEUED"
        )
    return value


def _validate_pull_status(value: object) -> "BrokerDeliveryStatus":
    if not isinstance(value, BrokerDeliveryStatus):
        raise ValueError("Invalid broker pull result status: expected BrokerDeliveryStatus")
    if value not in {BrokerDeliveryStatus.DELIVERED, BrokerDeliveryStatus.EMPTY}:
        raise ValueError(
            "Invalid broker pull result status: expected BrokerDeliveryStatus.DELIVERED or BrokerDeliveryStatus.EMPTY"
        )
    return value


def _validate_ack_status(value: object) -> "BrokerDeliveryStatus":
    if not isinstance(value, BrokerDeliveryStatus):
        raise ValueError("Invalid broker ack result status: expected BrokerDeliveryStatus")
    if value is not BrokerDeliveryStatus.ACKNOWLEDGED:
        raise ValueError(
            "Invalid broker ack result status: expected BrokerDeliveryStatus.ACKNOWLEDGED"
        )
    return value


class BrokerDeliveryStatus(str, Enum):
    """Transport lifecycle states surfaced by broker operations."""

    QUEUED = "queued"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    EMPTY = "empty"


@dataclass(slots=True)
class BrokerMessageEnvelope:
    """Broker delivery wrapper around Maia's public message model."""

    message: MessageRecord
    receipt_handle: str
    delivery_attempt: int = 1

    def __post_init__(self) -> None:
        _validate_message_record(self.message)
        _validate_str(
            self.receipt_handle,
            error="Invalid broker envelope receipt_handle: expected str",
        )
        self.delivery_attempt = _validate_delivery_attempt(self.delivery_attempt)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the broker envelope into plain data."""

        return {
            "message": self.message.to_dict(),
            "receipt_handle": self.receipt_handle,
            "delivery_attempt": self.delivery_attempt,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a broker envelope from serialized data."""

        missing_fields = [
            field_name for field_name in ("message", "receipt_handle") if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid broker envelope: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            message=_load_message_record(data["message"]),
            receipt_handle=data["receipt_handle"],
            delivery_attempt=data.get("delivery_attempt", 1),
        )


@dataclass(slots=True)
class BrokerPublishResult:
    """Broker response for a publish operation."""

    status: BrokerDeliveryStatus
    message_id: str

    def __post_init__(self) -> None:
        self.status = _validate_publish_status(self.status)
        _validate_str(
            self.message_id,
            error="Invalid broker publish result message_id: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the publish result into plain data."""

        return {
            "status": self.status.value,
            "message_id": self.message_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a publish result from serialized data."""

        missing_fields = [
            field_name for field_name in ("status", "message_id") if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid broker publish result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            status=_parse_broker_status(data["status"]),
            message_id=data["message_id"],
        )


@dataclass(slots=True)
class BrokerPullResult:
    """Broker response for pulling messages from an agent inbox."""

    status: BrokerDeliveryStatus
    messages: list[BrokerMessageEnvelope] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.status = _validate_pull_status(self.status)
        self.messages = _validate_envelope_list(self.messages)
        if self.status is BrokerDeliveryStatus.DELIVERED and not self.messages:
            raise ValueError(
                "Invalid broker pull result messages: expected at least one message when status is BrokerDeliveryStatus.DELIVERED"
            )
        if self.status is BrokerDeliveryStatus.EMPTY and self.messages:
            raise ValueError(
                "Invalid broker pull result messages: expected no messages when status is BrokerDeliveryStatus.EMPTY"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pull result into plain data."""

        return {
            "status": self.status.value,
            "messages": [message.to_dict() for message in self.messages],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a pull result from serialized data."""

        missing_fields = [
            field_name for field_name in ("status", "messages") if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid broker pull result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            status=_parse_broker_status(data["status"]),
            messages=_load_envelope_list(data["messages"]),
        )


@dataclass(slots=True)
class BrokerAckResult:
    """Broker response for acknowledging a pulled delivery."""

    status: BrokerDeliveryStatus
    message_id: str
    receipt_handle: str

    def __post_init__(self) -> None:
        self.status = _validate_ack_status(self.status)
        _validate_str(self.message_id, error="Invalid broker ack result message_id: expected str")
        _validate_str(
            self.receipt_handle,
            error="Invalid broker ack result receipt_handle: expected str",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the ack result into plain data."""

        return {
            "status": self.status.value,
            "message_id": self.message_id,
            "receipt_handle": self.receipt_handle,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore an ack result from serialized data."""

        missing_fields = [
            field_name
            for field_name in ("status", "message_id", "receipt_handle")
            if field_name not in data
        ]
        if missing_fields:
            missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
            raise ValueError(
                "Invalid broker ack result: missing required fields: "
                f"{missing_fields_text}"
            )

        return cls(
            status=_parse_broker_status(data["status"]),
            message_id=data["message_id"],
            receipt_handle=data["receipt_handle"],
        )


class MessageBroker(ABC):
    """Abstract broker contract for Maia's message plane."""

    @abstractmethod
    def publish(self, message: MessageRecord) -> BrokerPublishResult:
        """Publish a Maia message into the broker."""

    @abstractmethod
    def pull(self, *, agent_id: str, limit: int = 1) -> BrokerPullResult:
        """Pull pending broker deliveries for an agent inbox."""

    @abstractmethod
    def ack(self, envelope: BrokerMessageEnvelope) -> BrokerAckResult:
        """Acknowledge a previously pulled broker delivery."""
