"""SQLite-backed storage helpers for Keryx Phase 1 records inside Maia's canonical DB."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxPendingWorkRecord,
    KeryxSessionRecord,
)
from maia.sqlite_state import SQLiteState

__all__ = ["KeryxStorage"]


class KeryxStorage:
    """Persist Keryx sessions, messages, and handoffs in Maia's SQLite state DB."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._state = SQLiteState(self._path)

    @property
    def path(self) -> Path:
        return self._path

    def create_session(self, record: KeryxSessionRecord) -> KeryxSessionRecord:
        payload = record.to_dict()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO keryx_sessions(
                    session_id,
                    topic,
                    created_by,
                    status,
                    created_at,
                    updated_at,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.session_id,
                    record.topic,
                    record.created_by,
                    record.status.value,
                    record.created_at,
                    record.updated_at,
                    json.dumps(payload),
                ),
            )
            self._replace_session_participants(
                connection,
                session_id=record.session_id,
                participants=record.participants,
            )
        return record

    def list_sessions(self) -> list[KeryxSessionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, payload
                FROM keryx_sessions
                ORDER BY created_at ASC, session_id ASC
                """
            ).fetchall()
            participant_rows = connection.execute(
                """
                SELECT session_id, participant_agent_id
                FROM keryx_session_participants
                ORDER BY session_id ASC, position ASC
                """
            ).fetchall()

        participants_by_session: dict[str, list[str]] = {}
        for session_id, participant_agent_id in participant_rows:
            participants_by_session.setdefault(session_id, []).append(participant_agent_id)

        return [
            self._deserialize_session_payload(
                payload_text,
                participants=participants_by_session.get(session_id, []),
            )
            for session_id, payload_text in rows
        ]

    def get_session(self, session_id: str) -> KeryxSessionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM keryx_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            participant_rows = connection.execute(
                """
                SELECT participant_agent_id
                FROM keryx_session_participants
                WHERE session_id = ?
                ORDER BY position ASC
                """,
                (session_id,),
            ).fetchall()

        return self._deserialize_session_payload(
            row[0],
            participants=[participant_agent_id for (participant_agent_id,) in participant_rows],
        )

    def update_session(self, record: KeryxSessionRecord) -> KeryxSessionRecord:
        payload = record.to_dict()
        with self._connect() as connection:
            if not self._session_exists(connection, record.session_id):
                raise LookupError(f"Keryx session with id {record.session_id!r} not found")
            connection.execute(
                """
                UPDATE keryx_sessions
                SET topic = ?,
                    created_by = ?,
                    status = ?,
                    created_at = ?,
                    updated_at = ?,
                    payload = ?
                WHERE session_id = ?
                """,
                (
                    record.topic,
                    record.created_by,
                    record.status.value,
                    record.created_at,
                    record.updated_at,
                    json.dumps(payload),
                    record.session_id,
                ),
            )
            self._replace_session_participants(
                connection,
                session_id=record.session_id,
                participants=record.participants,
            )
        return record

    def create_message(self, record: KeryxMessageRecord) -> KeryxMessageRecord:
        with self._connect() as connection:
            if not self._session_exists(connection, record.session_id):
                raise LookupError(f"Keryx session with id {record.session_id!r} not found")
            connection.execute(
                """
                INSERT INTO keryx_messages(message_id, session_id, created_at, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    record.message_id,
                    record.session_id,
                    record.created_at,
                    json.dumps(record.to_dict()),
                ),
            )
        return record

    def list_messages(self, *, session_id: str | None = None) -> list[KeryxMessageRecord]:
        query = (
            """
            SELECT payload
            FROM keryx_messages
            ORDER BY created_at ASC, message_id ASC
            """
        )
        parameters: tuple[str, ...] = ()
        if session_id is not None:
            query = (
                """
                SELECT payload
                FROM keryx_messages
                WHERE session_id = ?
                ORDER BY created_at ASC, message_id ASC
                """
            )
            parameters = (session_id,)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [
            self._deserialize_record_payload(
                payload_text,
                record_type=KeryxMessageRecord,
                resource_name="message",
            )
            for (payload_text,) in rows
        ]

    def create_handoff(self, record: KeryxHandoffRecord) -> KeryxHandoffRecord:
        with self._connect() as connection:
            if not self._session_exists(connection, record.session_id):
                raise LookupError(f"Keryx session with id {record.session_id!r} not found")
            connection.execute(
                """
                INSERT INTO keryx_handoffs(
                    handoff_id,
                    session_id,
                    created_at,
                    updated_at,
                    status,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.handoff_id,
                    record.session_id,
                    record.created_at,
                    record.updated_at,
                    record.status.value,
                    json.dumps(record.to_dict()),
                ),
            )
        return record

    def list_handoffs(self, *, session_id: str | None = None) -> list[KeryxHandoffRecord]:
        query = (
            """
            SELECT payload
            FROM keryx_handoffs
            ORDER BY created_at ASC, handoff_id ASC
            """
        )
        parameters: tuple[str, ...] = ()
        if session_id is not None:
            query = (
                """
                SELECT payload
                FROM keryx_handoffs
                WHERE session_id = ?
                ORDER BY created_at ASC, handoff_id ASC
                """
            )
            parameters = (session_id,)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [
            self._deserialize_record_payload(
                payload_text,
                record_type=KeryxHandoffRecord,
                resource_name="handoff",
            )
            for (payload_text,) in rows
        ]

    def list_pending_work(self, *, agent_id: str) -> list[KeryxPendingWorkRecord]:
        sessions = {record.session_id: record for record in self.list_sessions()}
        messages_by_session: dict[str, list[KeryxMessageRecord]] = {}
        for message in self.list_messages():
            messages_by_session.setdefault(message.session_id, []).append(message)

        pending_work: list[KeryxPendingWorkRecord] = []
        for handoff in self.list_handoffs():
            if handoff.to_agent != agent_id or handoff.status is not KeryxHandoffStatus.OPEN:
                continue
            session = sessions.get(handoff.session_id)
            if session is None:
                continue
            candidate_messages = [
                message
                for message in messages_by_session.get(handoff.session_id, [])
                if message.to_agent == agent_id
            ]
            if not candidate_messages:
                continue
            pending_work.append(
                KeryxPendingWorkRecord(
                    session=session,
                    message=max(
                        candidate_messages,
                        key=lambda item: (item.created_at, item.message_id),
                    ),
                    handoff=handoff,
                )
            )
        pending_work.sort(
            key=lambda item: (item.handoff.created_at, item.handoff.handoff_id)
        )
        return pending_work

    def get_handoff(self, handoff_id: str) -> KeryxHandoffRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM keryx_handoffs WHERE handoff_id = ?",
                (handoff_id,),
            ).fetchone()
        if row is None:
            return None
        return self._deserialize_record_payload(
            row[0],
            record_type=KeryxHandoffRecord,
            resource_name="handoff",
        )

    def update_handoff(self, record: KeryxHandoffRecord) -> KeryxHandoffRecord:
        with self._connect() as connection:
            if not self._handoff_exists(connection, record.handoff_id):
                raise LookupError(f"Keryx handoff with id {record.handoff_id!r} not found")
            if not self._session_exists(connection, record.session_id):
                raise LookupError(f"Keryx session with id {record.session_id!r} not found")
            connection.execute(
                """
                UPDATE keryx_handoffs
                SET session_id = ?,
                    created_at = ?,
                    updated_at = ?,
                    status = ?,
                    payload = ?
                WHERE handoff_id = ?
                """,
                (
                    record.session_id,
                    record.created_at,
                    record.updated_at,
                    record.status.value,
                    json.dumps(record.to_dict()),
                    record.handoff_id,
                ),
            )
        return record

    def _connect(self) -> sqlite3.Connection:
        self._state.initialize()
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _replace_session_participants(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: str,
        participants: list[str],
    ) -> None:
        connection.execute(
            "DELETE FROM keryx_session_participants WHERE session_id = ?",
            (session_id,),
        )
        connection.executemany(
            """
            INSERT INTO keryx_session_participants(session_id, position, participant_agent_id)
            VALUES (?, ?, ?)
            """,
            [
                (session_id, position, participant_agent_id)
                for position, participant_agent_id in enumerate(participants)
            ],
        )

    def _deserialize_session_payload(
        self,
        payload_text: str,
        *,
        participants: list[str],
    ) -> KeryxSessionRecord:
        payload = self._load_payload_json(payload_text, resource_name="session")
        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid Keryx session SQLite in {self._path}: expected object payload"
            )
        return KeryxSessionRecord.from_dict({**payload, "participants": participants})

    def _deserialize_record_payload(
        self,
        payload_text: str,
        *,
        record_type: type[KeryxMessageRecord] | type[KeryxHandoffRecord],
        resource_name: str,
    ) -> KeryxMessageRecord | KeryxHandoffRecord:
        payload = self._load_payload_json(payload_text, resource_name=resource_name)
        if not isinstance(payload, dict):
            raise ValueError(
                f"Invalid Keryx {resource_name} SQLite in {self._path}: expected object payload"
            )
        return record_type.from_dict(payload)

    def _load_payload_json(self, payload_text: str, *, resource_name: str) -> object:
        try:
            return json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid Keryx {resource_name} SQLite in {self._path}: {exc.msg}"
            ) from exc

    def _session_exists(self, connection: sqlite3.Connection, session_id: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM keryx_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row is not None

    def _message_exists(self, connection: sqlite3.Connection, message_id: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM keryx_messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return row is not None

    def _handoff_exists(self, connection: sqlite3.Connection, handoff_id: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM keryx_handoffs WHERE handoff_id = ?",
            (handoff_id,),
        ).fetchone()
        return row is not None
