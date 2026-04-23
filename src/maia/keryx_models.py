"""Keryx domain model primitives for Maia's collaboration plane."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

__all__ = [
    "KeryxAgentSummary",
    "KeryxDeliveryMode",
    "KeryxHandoffRecord",
    "KeryxHandoffStatus",
    "KeryxMessageRecord",
    "KeryxPendingThreadWorkView",
    "KeryxPendingWorkRecord",
    "KeryxSessionRecord",
    "KeryxSessionStatus",
    "KeryxThreadHandoffView",
    "KeryxThreadMessageView",
    "KeryxThreadView",
]

_DEFAULT_CALL_SIGN = object()


def _validate_str(
    value: object,
    *,
    error: str,
    allow_empty: bool = True,
) -> str:
    if not isinstance(value, str):
        raise ValueError(error)
    if not allow_empty and not value:
        raise ValueError(error.replace("expected str", "expected non-empty str"))
    return value


def _validate_optional_str(
    value: object,
    *,
    error: str,
    allow_empty: bool = True,
) -> str | None:
    if value is None:
        return None
    return _validate_str(value, error=error, allow_empty=allow_empty)


def _validate_string_list(value: object, *, error: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ValueError(error)
    return list(value)


def _missing_required_fields(
    data: Mapping[str, Any],
    *,
    required_fields: tuple[str, ...],
    record_name: str,
) -> None:
    missing_fields = [
        field_name for field_name in required_fields if field_name not in data
    ]
    if not missing_fields:
        return
    missing_fields_text = ", ".join(repr(field_name) for field_name in missing_fields)
    raise ValueError(
        f"Invalid {record_name}: missing required fields: {missing_fields_text}"
    )


class KeryxSessionStatus(str, Enum):
    """Supported Keryx session lifecycle states."""

    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"


def _coerce_session_status(value: object) -> "KeryxSessionStatus":
    try:
        return (
            value
            if isinstance(value, KeryxSessionStatus)
            else KeryxSessionStatus(value)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Keryx session status: {value!r}") from exc


class KeryxHandoffStatus(str, Enum):
    """Supported Keryx handoff lifecycle states."""

    OPEN = "open"
    ACCEPTED = "accepted"
    DONE = "done"


def _coerce_handoff_status(value: object) -> "KeryxHandoffStatus":
    try:
        return (
            value
            if isinstance(value, KeryxHandoffStatus)
            else KeryxHandoffStatus(value)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Keryx handoff status: {value!r}") from exc


class KeryxDeliveryMode(str, Enum):
    """Supported delivery intent contract for Keryx messages."""

    AGENT_ONLY = "agent_only"
    USER_DIRECT = "user_direct"


def _coerce_delivery_mode(value: object) -> "KeryxDeliveryMode":
    try:
        return (
            value
            if isinstance(value, KeryxDeliveryMode)
            else KeryxDeliveryMode(value)
        )
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(repr(mode.value) for mode in KeryxDeliveryMode)
        raise ValueError(
            f"Invalid Keryx message delivery_mode: expected one of {allowed}; got {value!r}"
        ) from exc


@dataclass(slots=True)
class KeryxAgentSummary:
    """Serializable roster summary for a Maia agent."""

    agent_id: str
    name: str
    status: str
    setup_status: str
    runtime_status: str
    call_sign: str | object = field(default_factory=lambda: _DEFAULT_CALL_SIGN)
    role: str = ""
    speaking_style: str = "respectful"
    speaking_style_details: str = ""
    persona: str = ""

    def __post_init__(self) -> None:
        self.agent_id = _validate_str(
            self.agent_id,
            error="Invalid Keryx agent summary agent_id: expected str",
            allow_empty=False,
        )
        self.name = _validate_str(
            self.name,
            error="Invalid Keryx agent summary name: expected str",
            allow_empty=False,
        )
        self.call_sign = (
            self.name
            if self.call_sign is _DEFAULT_CALL_SIGN
            else _validate_str(
                self.call_sign,
                error="Invalid Keryx agent summary call_sign: expected str",
                allow_empty=False,
            )
        )
        self.role = _validate_str(
            self.role,
            error="Invalid Keryx agent summary role: expected str",
        )
        self.speaking_style = _validate_str(
            self.speaking_style,
            error="Invalid Keryx agent summary speaking_style: expected str",
            allow_empty=False,
        )
        self.speaking_style_details = _validate_str(
            self.speaking_style_details,
            error="Invalid Keryx agent summary speaking_style_details: expected str",
        )
        self.persona = _validate_str(
            self.persona,
            error="Invalid Keryx agent summary persona: expected str",
        )
        self.status = _validate_str(
            self.status,
            error="Invalid Keryx agent summary status: expected str",
            allow_empty=False,
        )
        self.setup_status = _validate_str(
            self.setup_status,
            error="Invalid Keryx agent summary setup_status: expected str",
            allow_empty=False,
        )
        self.runtime_status = _validate_str(
            self.runtime_status,
            error="Invalid Keryx agent summary runtime_status: expected str",
            allow_empty=False,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the agent summary into plain data."""

        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "call_sign": self.call_sign,
            "role": self.role,
            "speaking_style": self.speaking_style,
            "speaking_style_details": self.speaking_style_details,
            "persona": self.persona,
            "status": self.status,
            "setup_status": self.setup_status,
            "runtime_status": self.runtime_status,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore an agent summary from serialized data."""

        _missing_required_fields(
            data,
            required_fields=(
                "agent_id",
                "name",
                "status",
                "setup_status",
                "runtime_status",
            ),
            record_name="Keryx agent summary",
        )
        call_sign = _DEFAULT_CALL_SIGN
        if "call_sign" in data:
            call_sign = _validate_str(
                data["call_sign"],
                error="Invalid Keryx agent summary call_sign: expected str",
                allow_empty=False,
            )
        role = _validate_str(
            data.get("role", ""),
            error="Invalid Keryx agent summary role: expected str",
        )
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            call_sign=call_sign,
            role=role,
            speaking_style=_validate_str(
                data.get("speaking_style", "respectful"),
                error="Invalid Keryx agent summary speaking_style: expected str",
                allow_empty=False,
            ),
            speaking_style_details=_validate_str(
                data.get("speaking_style_details", ""),
                error="Invalid Keryx agent summary speaking_style_details: expected str",
            ),
            persona=_validate_str(
                data.get("persona", ""),
                error="Invalid Keryx agent summary persona: expected str",
            ),
            status=data["status"],
            setup_status=data["setup_status"],
            runtime_status=data["runtime_status"],
        )


@dataclass(slots=True)
class KeryxSessionRecord:
    """Serializable Keryx collaboration record backing a Maia thread."""

    session_id: str
    topic: str
    participants: list[str]
    created_by: str
    status: KeryxSessionStatus
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        self.session_id = _validate_str(
            self.session_id,
            error="Invalid Keryx session id: expected str",
            allow_empty=False,
        )
        self.topic = _validate_str(
            self.topic,
            error="Invalid Keryx session topic: expected str",
        )
        self.participants = _validate_string_list(
            self.participants,
            error="Invalid Keryx session participants: expected list of non-empty strings",
        )
        self.created_by = _validate_str(
            self.created_by,
            error="Invalid Keryx session created_by: expected str",
            allow_empty=False,
        )
        self.status = _coerce_session_status(self.status)
        self.created_at = _validate_str(
            self.created_at,
            error="Invalid Keryx session created_at: expected str",
            allow_empty=False,
        )
        self.updated_at = _validate_str(
            self.updated_at,
            error="Invalid Keryx session updated_at: expected str",
            allow_empty=False,
        )

    @property
    def thread_id(self) -> str:
        """Return the Maia public thread identifier for this Keryx session."""

        return self.session_id

    def as_thread_view(self) -> "KeryxThreadView":
        """Expose the session through Maia's public thread naming."""

        return KeryxThreadView(
            thread_id=self.session_id,
            topic=self.topic,
            participants=self.participants,
            created_by=self.created_by,
            status=self.status.value,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the session record into plain data."""

        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "participants": list(self.participants),
            "created_by": self.created_by,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a session record from serialized data."""

        _missing_required_fields(
            data,
            required_fields=(
                "session_id",
                "topic",
                "participants",
                "created_by",
                "status",
                "created_at",
                "updated_at",
            ),
            record_name="Keryx session record",
        )
        return cls(
            session_id=data["session_id"],
            topic=data["topic"],
            participants=data["participants"],
            created_by=data["created_by"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass(slots=True)
class KeryxMessageRecord:
    """Serializable Keryx message envelope stored within a Maia thread."""

    message_id: str
    session_id: str
    from_agent: str
    to_agent: str
    kind: str
    body: str
    created_at: str
    delivery_mode: KeryxDeliveryMode = KeryxDeliveryMode.AGENT_ONLY
    reply_to_message_id: str | None = None

    def __post_init__(self) -> None:
        self.message_id = _validate_str(
            self.message_id,
            error="Invalid Keryx message id: expected str",
            allow_empty=False,
        )
        self.session_id = _validate_str(
            self.session_id,
            error="Invalid Keryx message session_id: expected str",
            allow_empty=False,
        )
        self.from_agent = _validate_str(
            self.from_agent,
            error="Invalid Keryx message from_agent: expected str",
            allow_empty=False,
        )
        self.to_agent = _validate_str(
            self.to_agent,
            error="Invalid Keryx message to_agent: expected str",
            allow_empty=False,
        )
        self.kind = _validate_str(
            self.kind,
            error="Invalid Keryx message kind: expected str",
            allow_empty=False,
        )
        self.body = _validate_str(
            self.body,
            error="Invalid Keryx message body: expected str",
        )
        self.created_at = _validate_str(
            self.created_at,
            error="Invalid Keryx message created_at: expected str",
            allow_empty=False,
        )
        self.delivery_mode = _coerce_delivery_mode(self.delivery_mode)
        self.reply_to_message_id = _validate_optional_str(
            self.reply_to_message_id,
            error="Invalid Keryx message reply_to_message_id: expected str",
            allow_empty=False,
        )

    @property
    def thread_id(self) -> str:
        """Return the Maia public thread identifier for this Keryx message."""

        return self.session_id

    def as_thread_view(self) -> "KeryxThreadMessageView":
        """Expose the message through Maia's public thread naming."""

        return KeryxThreadMessageView(
            message_id=self.message_id,
            thread_id=self.session_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            kind=self.kind,
            body=self.body,
            created_at=self.created_at,
            delivery_mode=self.delivery_mode.value,
            reply_to_message_id=self.reply_to_message_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the message record into plain data."""

        payload = {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "kind": self.kind,
            "body": self.body,
            "created_at": self.created_at,
            "delivery_mode": self.delivery_mode.value,
        }
        if self.reply_to_message_id is not None:
            payload["reply_to_message_id"] = self.reply_to_message_id
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a message record from serialized data."""

        _missing_required_fields(
            data,
            required_fields=(
                "message_id",
                "session_id",
                "from_agent",
                "to_agent",
                "kind",
                "body",
                "created_at",
            ),
            record_name="Keryx message record",
        )
        return cls(
            message_id=data["message_id"],
            session_id=data["session_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            kind=data["kind"],
            body=data["body"],
            created_at=data["created_at"],
            delivery_mode=data.get("delivery_mode", KeryxDeliveryMode.AGENT_ONLY.value),
            reply_to_message_id=data.get("reply_to_message_id"),
        )


@dataclass(slots=True)
class KeryxPendingWorkRecord:
    """Serializable Keryx pending-work payload for runtime workers."""

    session: KeryxSessionRecord
    message: KeryxMessageRecord
    handoff: KeryxHandoffRecord

    def __post_init__(self) -> None:
        if not isinstance(self.session, KeryxSessionRecord):
            raise ValueError("Invalid Keryx pending work session: expected KeryxSessionRecord")
        if not isinstance(self.message, KeryxMessageRecord):
            raise ValueError("Invalid Keryx pending work message: expected KeryxMessageRecord")
        if not isinstance(self.handoff, KeryxHandoffRecord):
            raise ValueError("Invalid Keryx pending work handoff: expected KeryxHandoffRecord")
        if self.message.session_id != self.session.session_id:
            raise ValueError("Invalid Keryx pending work: message session_id must match session")
        if self.handoff.session_id != self.session.session_id:
            raise ValueError("Invalid Keryx pending work: handoff session_id must match session")

    @property
    def thread(self) -> KeryxSessionRecord:
        """Return the Maia thread record for this pending work item."""

        return self.session

    def as_thread_view(self) -> "KeryxPendingThreadWorkView":
        """Expose the pending work payload through Maia's public thread naming."""

        return KeryxPendingThreadWorkView(
            thread=self.session.as_thread_view(),
            message=self.message.as_thread_view(),
            handoff=self.handoff.as_thread_view(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session.to_dict(),
            "message": self.message.to_dict(),
            "handoff": self.handoff.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        _missing_required_fields(
            data,
            required_fields=("session", "message", "handoff"),
            record_name="Keryx pending work record",
        )
        session = data["session"]
        message = data["message"]
        handoff = data["handoff"]
        if not isinstance(session, Mapping):
            raise ValueError("Invalid Keryx pending work session: expected object")
        if not isinstance(message, Mapping):
            raise ValueError("Invalid Keryx pending work message: expected object")
        if not isinstance(handoff, Mapping):
            raise ValueError("Invalid Keryx pending work handoff: expected object")
        return cls(
            session=KeryxSessionRecord.from_dict(session),
            message=KeryxMessageRecord.from_dict(message),
            handoff=KeryxHandoffRecord.from_dict(handoff),
        )


@dataclass(slots=True)
class KeryxHandoffRecord:
    """Serializable Keryx handoff metadata linked to a Maia thread."""

    handoff_id: str
    session_id: str
    from_agent: str
    to_agent: str
    kind: str
    status: KeryxHandoffStatus
    summary: str
    location: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        self.handoff_id = _validate_str(
            self.handoff_id,
            error="Invalid Keryx handoff id: expected str",
            allow_empty=False,
        )
        self.session_id = _validate_str(
            self.session_id,
            error="Invalid Keryx handoff session_id: expected str",
            allow_empty=False,
        )
        self.from_agent = _validate_str(
            self.from_agent,
            error="Invalid Keryx handoff from_agent: expected str",
            allow_empty=False,
        )
        self.to_agent = _validate_str(
            self.to_agent,
            error="Invalid Keryx handoff to_agent: expected str",
            allow_empty=False,
        )
        self.kind = _validate_str(
            self.kind,
            error="Invalid Keryx handoff kind: expected str",
            allow_empty=False,
        )
        self.status = _coerce_handoff_status(self.status)
        self.summary = _validate_str(
            self.summary,
            error="Invalid Keryx handoff summary: expected str",
        )
        self.location = _validate_str(
            self.location,
            error="Invalid Keryx handoff location: expected str",
            allow_empty=False,
        )
        self.created_at = _validate_str(
            self.created_at,
            error="Invalid Keryx handoff created_at: expected str",
            allow_empty=False,
        )
        self.updated_at = _validate_str(
            self.updated_at,
            error="Invalid Keryx handoff updated_at: expected str",
            allow_empty=False,
        )

    @property
    def thread_id(self) -> str:
        """Return the Maia public thread identifier for this Keryx handoff."""

        return self.session_id

    def as_thread_view(self) -> "KeryxThreadHandoffView":
        """Expose the handoff through Maia's public thread naming."""

        return KeryxThreadHandoffView(
            handoff_id=self.handoff_id,
            thread_id=self.session_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            kind=self.kind,
            status=self.status.value,
            summary=self.summary,
            location=self.location,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the handoff record into plain data."""

        return {
            "handoff_id": self.handoff_id,
            "session_id": self.session_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "kind": self.kind,
            "status": self.status.value,
            "summary": self.summary,
            "location": self.location,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Restore a handoff record from serialized data."""

        _missing_required_fields(
            data,
            required_fields=(
                "handoff_id",
                "session_id",
                "from_agent",
                "to_agent",
                "kind",
                "status",
                "summary",
                "location",
                "created_at",
                "updated_at",
            ),
            record_name="Keryx handoff record",
        )
        return cls(
            handoff_id=data["handoff_id"],
            session_id=data["session_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            kind=data["kind"],
            status=data["status"],
            summary=data["summary"],
            location=data["location"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass(slots=True)
class KeryxThreadView:
    """Thread-facing Keryx collaboration view for Maia worker/runtime flows."""

    thread_id: str
    topic: str
    participants: list[str]
    created_by: str
    status: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        self.thread_id = _validate_str(
            self.thread_id,
            error="Invalid Keryx thread id: expected str",
            allow_empty=False,
        )
        self.topic = _validate_str(
            self.topic,
            error="Invalid Keryx thread topic: expected str",
        )
        self.participants = _validate_string_list(
            self.participants,
            error="Invalid Keryx thread participants: expected list of non-empty strings",
        )
        self.created_by = _validate_str(
            self.created_by,
            error="Invalid Keryx thread created_by: expected str",
            allow_empty=False,
        )
        self.status = _coerce_session_status(self.status).value
        self.created_at = _validate_str(
            self.created_at,
            error="Invalid Keryx thread created_at: expected str",
            allow_empty=False,
        )
        self.updated_at = _validate_str(
            self.updated_at,
            error="Invalid Keryx thread updated_at: expected str",
            allow_empty=False,
        )


@dataclass(slots=True)
class KeryxThreadMessageView:
    """Thread-facing Keryx message view for Maia worker/runtime flows."""

    message_id: str
    thread_id: str
    from_agent: str
    to_agent: str
    kind: str
    body: str
    created_at: str
    delivery_mode: str = KeryxDeliveryMode.AGENT_ONLY.value
    reply_to_message_id: str | None = None

    def __post_init__(self) -> None:
        self.message_id = _validate_str(
            self.message_id,
            error="Invalid Keryx thread message id: expected str",
            allow_empty=False,
        )
        self.thread_id = _validate_str(
            self.thread_id,
            error="Invalid Keryx thread message thread_id: expected str",
            allow_empty=False,
        )
        self.from_agent = _validate_str(
            self.from_agent,
            error="Invalid Keryx thread message from_agent: expected str",
            allow_empty=False,
        )
        self.to_agent = _validate_str(
            self.to_agent,
            error="Invalid Keryx thread message to_agent: expected str",
            allow_empty=False,
        )
        self.kind = _validate_str(
            self.kind,
            error="Invalid Keryx thread message kind: expected str",
            allow_empty=False,
        )
        self.body = _validate_str(
            self.body,
            error="Invalid Keryx thread message body: expected str",
        )
        self.created_at = _validate_str(
            self.created_at,
            error="Invalid Keryx thread message created_at: expected str",
            allow_empty=False,
        )
        self.delivery_mode = _coerce_delivery_mode(self.delivery_mode).value
        self.reply_to_message_id = _validate_optional_str(
            self.reply_to_message_id,
            error="Invalid Keryx thread message reply_to_message_id: expected str",
            allow_empty=False,
        )

    @classmethod
    def from_message_record(cls, record: KeryxMessageRecord) -> Self:
        return record.as_thread_view()

    def to_message_record(self) -> KeryxMessageRecord:
        return KeryxMessageRecord(
            message_id=self.message_id,
            session_id=self.thread_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            kind=self.kind,
            body=self.body,
            created_at=self.created_at,
            delivery_mode=self.delivery_mode,
            reply_to_message_id=self.reply_to_message_id,
        )


@dataclass(slots=True)
class KeryxThreadHandoffView:
    """Thread-facing Keryx handoff view for Maia worker/runtime flows."""

    handoff_id: str
    thread_id: str
    from_agent: str
    to_agent: str
    kind: str
    status: str
    summary: str
    location: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        self.handoff_id = _validate_str(
            self.handoff_id,
            error="Invalid Keryx thread handoff id: expected str",
            allow_empty=False,
        )
        self.thread_id = _validate_str(
            self.thread_id,
            error="Invalid Keryx thread handoff thread_id: expected str",
            allow_empty=False,
        )
        self.from_agent = _validate_str(
            self.from_agent,
            error="Invalid Keryx thread handoff from_agent: expected str",
            allow_empty=False,
        )
        self.to_agent = _validate_str(
            self.to_agent,
            error="Invalid Keryx thread handoff to_agent: expected str",
            allow_empty=False,
        )
        self.kind = _validate_str(
            self.kind,
            error="Invalid Keryx thread handoff kind: expected str",
            allow_empty=False,
        )
        self.status = _coerce_handoff_status(self.status).value
        self.summary = _validate_str(
            self.summary,
            error="Invalid Keryx thread handoff summary: expected str",
        )
        self.location = _validate_str(
            self.location,
            error="Invalid Keryx thread handoff location: expected str",
            allow_empty=False,
        )
        self.created_at = _validate_str(
            self.created_at,
            error="Invalid Keryx thread handoff created_at: expected str",
            allow_empty=False,
        )
        self.updated_at = _validate_str(
            self.updated_at,
            error="Invalid Keryx thread handoff updated_at: expected str",
            allow_empty=False,
        )

    @classmethod
    def from_handoff_record(cls, record: KeryxHandoffRecord) -> Self:
        return record.as_thread_view()

    def to_handoff_record(self) -> KeryxHandoffRecord:
        return KeryxHandoffRecord(
            handoff_id=self.handoff_id,
            session_id=self.thread_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            kind=self.kind,
            status=self.status,
            summary=self.summary,
            location=self.location,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(slots=True)
class KeryxPendingThreadWorkView:
    """Thread-facing Keryx pending-work view for Maia worker/runtime flows."""

    thread: KeryxThreadView
    message: KeryxThreadMessageView
    handoff: KeryxThreadHandoffView

    def __post_init__(self) -> None:
        if not isinstance(self.thread, KeryxThreadView):
            raise ValueError("Invalid Keryx pending thread work thread: expected KeryxThreadView")
        if not isinstance(self.message, KeryxThreadMessageView):
            raise ValueError(
                "Invalid Keryx pending thread work message: expected KeryxThreadMessageView"
            )
        if not isinstance(self.handoff, KeryxThreadHandoffView):
            raise ValueError(
                "Invalid Keryx pending thread work handoff: expected KeryxThreadHandoffView"
            )
        if self.message.thread_id != self.thread.thread_id:
            raise ValueError(
                "Invalid Keryx pending thread work: message thread_id must match thread"
            )
        if self.handoff.thread_id != self.thread.thread_id:
            raise ValueError(
                "Invalid Keryx pending thread work: handoff thread_id must match thread"
            )

