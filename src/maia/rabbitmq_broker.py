"""RabbitMQ-backed broker adapter for Maia message delivery."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from maia.broker import (
    BrokerAckResult,
    BrokerDeliveryStatus,
    BrokerMessageEnvelope,
    BrokerPullResult,
    BrokerPublishResult,
    MessageBroker,
)
from maia.message_model import MessageRecord

__all__ = ["RabbitMQBroker"]


class RabbitMQBroker(MessageBroker):
    """Message broker implementation backed by RabbitMQ via pika."""

    def __init__(
        self,
        *,
        broker_url: str | None = None,
        connection_parameters: object | None = None,
        queue_prefix: str = "maia.inbox",
        pika_module: object | None = None,
        connection_factory: Callable[[object], Any] | None = None,
    ) -> None:
        if broker_url is None and connection_parameters is None:
            raise ValueError(
                "RabbitMQ broker requires broker_url or connection_parameters"
            )
        if broker_url is not None and (not isinstance(broker_url, str) or not broker_url):
            raise ValueError("RabbitMQ broker broker_url must be a non-empty string")
        if not isinstance(queue_prefix, str) or not queue_prefix:
            raise ValueError("RabbitMQ broker queue_prefix must be a non-empty string")

        self._queue_prefix = queue_prefix
        self._pika = pika_module
        self._connection_factory = connection_factory
        self._broker_url = broker_url
        self._connection_parameters = connection_parameters
        self._connection: Any | None = None
        self._channel: Any | None = None

    def publish(self, message: MessageRecord) -> BrokerPublishResult:
        return self.publish_with_metadata(message, thread_topic=None)

    def publish_with_metadata(
        self,
        message: MessageRecord,
        *,
        thread_topic: str | None,
    ) -> BrokerPublishResult:
        if not isinstance(message, MessageRecord):
            raise ValueError("RabbitMQ publish requires MessageRecord")

        queue_name = self.queue_name_for_agent(message.to_agent)
        channel = self._get_channel()
        body = self._dump_message(message)
        properties = self._build_message_properties(message, thread_topic=thread_topic)

        try:
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=body,
                properties=properties,
            )
        except Exception as exc:  # pragma: no cover - exercised via stubs in tests
            raise self._value_error("publish failed", exc) from exc

        return BrokerPublishResult(
            status=BrokerDeliveryStatus.QUEUED,
            message_id=message.message_id,
        )

    def pull(self, *, agent_id: str, limit: int = 1) -> BrokerPullResult:
        envelopes_with_metadata = self.pull_with_metadata(agent_id=agent_id, limit=limit)
        messages = [item[0] for item in envelopes_with_metadata]
        if not messages:
            return BrokerPullResult(status=BrokerDeliveryStatus.EMPTY)
        return BrokerPullResult(
            status=BrokerDeliveryStatus.DELIVERED,
            messages=messages,
        )

    def pull_with_metadata(
        self,
        *,
        agent_id: str,
        limit: int = 1,
    ) -> list[tuple[BrokerMessageEnvelope, dict[str, str]]]:
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("RabbitMQ pull requires non-empty agent_id")
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("RabbitMQ pull requires limit >= 1")

        queue_name = self.queue_name_for_agent(agent_id)
        channel = self._get_channel()
        messages: list[tuple[BrokerMessageEnvelope, dict[str, str]]] = []

        try:
            channel.queue_declare(queue=queue_name, passive=True)
        except Exception as exc:
            if self._is_missing_queue_error(exc):
                return []
            raise self._value_error(
                f"pull failed for queue {queue_name!r}", exc
            ) from exc

        try:
            for _ in range(limit):
                method_frame, header_frame, body = channel.basic_get(
                    queue=queue_name,
                    auto_ack=False,
                )
                if method_frame is None:
                    break
                messages.append(
                    self._build_envelope_and_metadata(
                        method_frame=method_frame,
                        header_frame=header_frame,
                        body=body,
                    )
                )
        except ValueError:
            raise
        except Exception as exc:
            raise self._value_error(
                f"pull failed for queue {queue_name!r}", exc
            ) from exc

        return messages

    def ack(self, envelope: BrokerMessageEnvelope) -> BrokerAckResult:
        if not isinstance(envelope, BrokerMessageEnvelope):
            raise ValueError("RabbitMQ ack requires BrokerMessageEnvelope")
        if not envelope.receipt_handle:
            raise ValueError("RabbitMQ ack requires envelope receipt_handle")

        try:
            delivery_tag = int(envelope.receipt_handle)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "RabbitMQ ack requires numeric receipt_handle"
            ) from exc
        if delivery_tag < 1:
            raise ValueError("RabbitMQ ack requires receipt_handle >= 1")

        try:
            self._get_channel().basic_ack(delivery_tag=delivery_tag)
        except Exception as exc:
            raise self._value_error("ack failed", exc) from exc

        return BrokerAckResult(
            status=BrokerDeliveryStatus.ACKNOWLEDGED,
            message_id=envelope.message.message_id,
            receipt_handle=envelope.receipt_handle,
        )

    def close(self) -> None:
        channel = self._channel
        self._channel = None
        if channel is not None and getattr(channel, "is_open", True):
            channel.close()

        connection = self._connection
        self._connection = None
        if connection is not None and getattr(connection, "is_open", True):
            connection.close()

    def __enter__(self) -> "RabbitMQBroker":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def queue_name_for_agent(self, agent_id: str) -> str:
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("RabbitMQ broker agent_id must be a non-empty string")
        return f"{self._queue_prefix}.{agent_id}"

    def _build_envelope_and_metadata(
        self,
        *,
        method_frame: Any,
        header_frame: Any,
        body: object,
    ) -> tuple[BrokerMessageEnvelope, dict[str, str]]:
        delivery_tag = getattr(method_frame, "delivery_tag", None)
        if not isinstance(delivery_tag, int) or delivery_tag < 1:
            raise ValueError("RabbitMQ delivery is missing a valid delivery_tag")

        payload = self._load_payload(body)
        try:
            message = MessageRecord.from_dict(payload)
        except ValueError as exc:
            raise ValueError(f"RabbitMQ delivery payload is malformed: {exc}") from exc

        delivery_attempt = self._delivery_attempt_for(
            method_frame=method_frame,
            header_frame=header_frame,
        )
        metadata = self._metadata_from_header_frame(header_frame)
        return (
            BrokerMessageEnvelope(
                message=message,
                receipt_handle=str(delivery_tag),
                delivery_attempt=delivery_attempt,
            ),
            metadata,
        )

    def _build_envelope(
        self,
        *,
        method_frame: Any,
        header_frame: Any,
        body: object,
    ) -> BrokerMessageEnvelope:
        return self._build_envelope_and_metadata(
            method_frame=method_frame,
            header_frame=header_frame,
            body=body,
        )[0]

    def _delivery_attempt_for(self, *, method_frame: Any, header_frame: Any) -> int:
        headers = getattr(header_frame, "headers", None)
        if isinstance(headers, dict):
            count = headers.get("x-delivery-count")
            if isinstance(count, int) and count >= 1:
                return count
        return 2 if bool(getattr(method_frame, "redelivered", False)) else 1

    def _dump_message(self, message: MessageRecord) -> bytes:
        return json.dumps(message.to_dict(), sort_keys=True).encode("utf-8")

    def _load_payload(self, body: object) -> dict[str, Any]:
        if isinstance(body, bytes):
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    "RabbitMQ delivery payload is malformed: body is not valid UTF-8"
                ) from exc
        elif isinstance(body, str):
            text = body
        else:
            raise ValueError(
                "RabbitMQ delivery payload is malformed: body must be bytes or str"
            )

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "RabbitMQ delivery payload is malformed: body is not valid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise ValueError(
                "RabbitMQ delivery payload is malformed: expected message object"
            )
        return payload

    def _build_message_properties(
        self,
        message: MessageRecord,
        *,
        thread_topic: str | None,
    ) -> object | None:
        pika_module = self._get_pika_module()
        properties_type = getattr(pika_module, "BasicProperties", None)
        if properties_type is None:
            return None
        headers: dict[str, str] = {}
        if thread_topic is not None:
            headers["maia_thread_topic"] = thread_topic
        return properties_type(
            content_type="application/json",
            delivery_mode=2,
            message_id=message.message_id,
            type=message.kind.value,
            headers=headers,
        )

    def _metadata_from_header_frame(self, header_frame: Any) -> dict[str, str]:
        headers = getattr(header_frame, "headers", None)
        if not isinstance(headers, dict):
            return {}
        metadata: dict[str, str] = {}
        thread_topic = headers.get("maia_thread_topic")
        if isinstance(thread_topic, str):
            metadata["thread_topic"] = thread_topic
        return metadata

    def _get_channel(self) -> Any:
        if self._channel is not None and getattr(self._channel, "is_open", True):
            return self._channel

        connection = self._connection
        if connection is None or not getattr(connection, "is_open", True):
            self._connection = self._open_connection()
            connection = self._connection

        try:
            self._channel = connection.channel()
        except Exception as exc:
            raise self._value_error("connection failed while opening channel", exc) from exc
        return self._channel

    def _open_connection(self) -> Any:
        parameters = self._resolve_connection_parameters()
        try:
            if self._connection_factory is not None:
                return self._connection_factory(parameters)
            pika_module = self._get_pika_module()
            return pika_module.BlockingConnection(parameters)
        except Exception as exc:
            raise self._value_error("connection failed", exc) from exc

    def _resolve_connection_parameters(self) -> object:
        if self._connection_parameters is not None:
            return self._connection_parameters

        pika_module = self._get_pika_module()
        parameters_type = getattr(pika_module, "URLParameters", None)
        if parameters_type is None:
            raise ValueError("RabbitMQ broker pika.URLParameters is unavailable")
        return parameters_type(self._broker_url)

    def _get_pika_module(self) -> object:
        if self._pika is not None:
            return self._pika
        try:
            import pika  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ValueError(
                "RabbitMQ broker requires the 'pika' package; install maia[rabbitmq]"
            ) from exc
        self._pika = pika
        return pika

    def _is_missing_queue_error(self, exc: Exception) -> bool:
        reply_code = getattr(exc, "reply_code", None)
        if reply_code == 404:
            return True
        return "not found" in str(exc).lower()

    def _value_error(self, prefix: str, exc: Exception) -> ValueError:
        return ValueError(f"RabbitMQ broker {prefix}: {exc}")
