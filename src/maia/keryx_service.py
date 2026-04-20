"""Keryx service-layer operations backed by Maia's canonical SQLite DB."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

from maia.agent_model import AgentRecord
from maia.app_state import get_state_db_path
from maia.keryx_models import (
    KeryxAgentSummary,
    KeryxHandoffRecord,
    KeryxMessageRecord,
    KeryxPendingWorkRecord,
    KeryxSessionRecord,
    KeryxThreadHandoffView,
    KeryxThreadMessageView,
    KeryxThreadView,
)
from maia.keryx_storage import KeryxStorage
from maia.runtime_adapter import RuntimeState, RuntimeStatus
from maia.runtime_state_storage import RuntimeStateStorage
from maia.storage import JsonRegistryStorage

__all__ = [
    "KeryxResourceNotFoundError",
    "KeryxService",
    "KeryxServiceError",
]


class KeryxServiceError(Exception):
    """Base error for Keryx service-layer failures."""


class KeryxResourceNotFoundError(KeryxServiceError, LookupError):
    """Raised when a requested Keryx resource does not exist."""


class KeryxService:
    """Expose Keryx Phase 1 operations on top of Maia's canonical SQLite DB."""

    def __init__(self, state_db_path: Path | str | None = None) -> None:
        self._state_db_path = (
            get_state_db_path()
            if state_db_path is None
            else Path(state_db_path)
        )
        self._registry_storage = JsonRegistryStorage()
        self._runtime_state_storage = RuntimeStateStorage()
        self._keryx_storage = KeryxStorage(self._state_db_path)

    @property
    def state_db_path(self) -> Path:
        return self._state_db_path

    def list_roster(self) -> list[KeryxAgentSummary]:
        registry = self._registry_storage.load(self._state_db_path)
        runtime_states = self._runtime_state_storage.load(self._state_db_path)
        return [
            self._build_agent_summary(record, runtime_states.get(record.agent_id))
            for record in registry.list()
        ]

    def list_sessions(self) -> list[KeryxSessionRecord]:
        return self._keryx_storage.list_sessions()

    def list_threads(self) -> list[KeryxThreadView]:
        """Return Maia thread views backed by stored Keryx sessions."""

        return [record.as_thread_view() for record in self.list_sessions()]

    def list_pending_work(self, agent_id: str) -> list[KeryxPendingWorkRecord]:
        return self._keryx_storage.list_pending_work(agent_id=agent_id)

    def create_session(self, record: KeryxSessionRecord) -> KeryxSessionRecord:
        return self._keryx_storage.create_session(record)

    def get_session(self, session_id: str) -> KeryxSessionRecord:
        record = self._keryx_storage.get_session(session_id)
        if record is None:
            self._raise_not_found("session", session_id)
        return record

    def get_thread(self, thread_id: str) -> KeryxThreadView:
        record = self._keryx_storage.get_session(thread_id)
        if record is None:
            self._raise_not_found("thread", thread_id)
        return record.as_thread_view()

    def update_session(
        self,
        session_id: str,
        record: KeryxSessionRecord,
    ) -> KeryxSessionRecord:
        self._require_matching_id(
            resource_name="Keryx session",
            field_name="session_id",
            expected=session_id,
            actual=record.session_id,
        )
        try:
            return self._keryx_storage.update_session(record)
        except LookupError as exc:
            self._translate_lookup_error(exc)

    def list_session_messages(self, session_id: str) -> list[KeryxMessageRecord]:
        self.get_session(session_id)
        return self._keryx_storage.list_messages(session_id=session_id)

    def list_thread_messages(self, thread_id: str) -> list[KeryxThreadMessageView]:
        self.get_thread(thread_id)
        return [
            record.as_thread_view()
            for record in self._keryx_storage.list_messages(session_id=thread_id)
        ]

    def create_session_message(
        self,
        session_id: str,
        record: KeryxMessageRecord,
    ) -> KeryxMessageRecord:
        self._require_matching_id(
            resource_name="Keryx message",
            field_name="session_id",
            expected=session_id,
            actual=record.session_id,
        )
        self.get_session(session_id)
        try:
            return self._keryx_storage.create_message(record)
        except LookupError as exc:
            self._translate_lookup_error(exc)

    def list_session_handoffs(self, session_id: str) -> list[KeryxHandoffRecord]:
        self.get_session(session_id)
        return self._keryx_storage.list_handoffs(session_id=session_id)

    def list_handoffs(self) -> list[KeryxHandoffRecord]:
        return self._keryx_storage.list_handoffs()

    def list_thread_handoffs(self, thread_id: str) -> list[KeryxThreadHandoffView]:
        self.get_thread(thread_id)
        return [
            record.as_thread_view()
            for record in self._keryx_storage.list_handoffs(session_id=thread_id)
        ]

    def create_session_handoff(
        self,
        session_id: str,
        record: KeryxHandoffRecord,
    ) -> KeryxHandoffRecord:
        self._require_matching_id(
            resource_name="Keryx handoff",
            field_name="session_id",
            expected=session_id,
            actual=record.session_id,
        )
        self.get_session(session_id)
        try:
            return self._keryx_storage.create_handoff(record)
        except LookupError as exc:
            self._translate_lookup_error(exc)

    def create_thread_handoff(
        self,
        thread_id: str,
        record: KeryxThreadHandoffView | KeryxHandoffRecord,
    ) -> KeryxThreadHandoffView:
        handoff_record = (
            record.to_handoff_record()
            if isinstance(record, KeryxThreadHandoffView)
            else record
        )
        self._require_matching_id(
            resource_name="Keryx handoff",
            field_name="thread_id",
            expected=thread_id,
            actual=handoff_record.thread_id,
        )
        self.get_thread(thread_id)
        try:
            created = self._keryx_storage.create_handoff(handoff_record)
        except LookupError as exc:
            self._translate_lookup_error(exc)
        return created.as_thread_view()

    def get_session_handoff(
        self,
        session_id: str,
        handoff_id: str,
    ) -> KeryxHandoffRecord:
        self.get_session(session_id)
        record = self._keryx_storage.get_handoff(handoff_id)
        if record is None or record.session_id != session_id:
            self._raise_nested_not_found(
                resource_name="handoff",
                resource_id=handoff_id,
                parent_name="session",
                parent_id=session_id,
            )
        return record

    def update_session_handoff(
        self,
        session_id: str,
        handoff_id: str,
        record: KeryxHandoffRecord,
    ) -> KeryxHandoffRecord:
        self._require_matching_id(
            resource_name="Keryx handoff",
            field_name="session_id",
            expected=session_id,
            actual=record.session_id,
        )
        self._require_matching_id(
            resource_name="Keryx handoff",
            field_name="handoff_id",
            expected=handoff_id,
            actual=record.handoff_id,
        )
        self.get_session_handoff(session_id, handoff_id)
        try:
            return self._keryx_storage.update_handoff(record)
        except LookupError as exc:
            self._translate_lookup_error(exc)

    def get_handoff(self, handoff_id: str) -> KeryxHandoffRecord:
        record = self._keryx_storage.get_handoff(handoff_id)
        if record is None:
            self._raise_not_found("handoff", handoff_id)
        return record

    def update_handoff(
        self,
        handoff_id: str,
        record: KeryxHandoffRecord,
    ) -> KeryxHandoffRecord:
        self._require_matching_id(
            resource_name="Keryx handoff",
            field_name="handoff_id",
            expected=handoff_id,
            actual=record.handoff_id,
        )
        try:
            return self._keryx_storage.update_handoff(record)
        except LookupError as exc:
            self._translate_lookup_error(exc)

    def _build_agent_summary(
        self,
        record: AgentRecord,
        runtime_state: RuntimeState | None,
    ) -> KeryxAgentSummary:
        return KeryxAgentSummary(
            agent_id=record.agent_id,
            name=record.name,
            call_sign=record.call_sign,
            role=record.role,
            status=record.status.value,
            setup_status=(
                record.setup_status.value
                if runtime_state is None or runtime_state.setup_status is None
                else runtime_state.setup_status
            ),
            runtime_status=(
                RuntimeStatus.STOPPED.value
                if runtime_state is None
                else runtime_state.runtime_status.value
            ),
        )

    def _require_matching_id(
        self,
        *,
        resource_name: str,
        field_name: str,
        expected: str,
        actual: str,
    ) -> None:
        if expected != actual:
            raise ValueError(
                f"{resource_name} {field_name} must match route id {expected!r}"
            )

    def _translate_lookup_error(self, exc: LookupError) -> NoReturn:
        raise KeryxResourceNotFoundError(str(exc)) from exc

    def _raise_not_found(self, resource_name: str, resource_id: str) -> NoReturn:
        raise KeryxResourceNotFoundError(
            f"Keryx {resource_name} with id {resource_id!r} not found"
        )

    def _raise_nested_not_found(
        self,
        *,
        resource_name: str,
        resource_id: str,
        parent_name: str,
        parent_id: str,
    ) -> NoReturn:
        raise KeryxResourceNotFoundError(
            f"Keryx {resource_name} with id {resource_id!r} "
            f"not found in {parent_name} {parent_id!r}"
        )
