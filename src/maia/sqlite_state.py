"""SQLite-backed local control-plane state for Maia."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

__all__ = ["SQLiteState"]


class SQLiteState:
    """Persist Maia local control-plane state in a single SQLite database."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def initialize(self) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_states (
                    agent_id TEXT PRIMARY KEY,
                    runtime_status TEXT NOT NULL,
                    runtime_handle TEXT,
                    setup_status TEXT NOT NULL DEFAULT 'unknown',
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS infra_state (
                    name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS collaboration_threads (
                    thread_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS collaboration_messages (
                    message_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS collaboration_handoffs (
                    handoff_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                );
                """
            )
            connection.execute(
                """
                INSERT INTO infra_state(name, status, detail)
                VALUES ('bootstrap', 'pending', 'shared infra not bootstrapped yet')
                ON CONFLICT(name) DO NOTHING
                """
            )
        return self._path

    def load_agents(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM agents ORDER BY position ASC"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_agents(self, records: list[dict[str, Any]]) -> None:
        self.initialize()
        payloads = [json.dumps(record) for record in records]
        with self._connect() as connection:
            connection.execute("DELETE FROM agents")
            connection.executemany(
                "INSERT INTO agents(agent_id, position, payload) VALUES (?, ?, ?)",
                [
                    (record["agent_id"], position, payload)
                    for position, (record, payload) in enumerate(zip(records, payloads, strict=True))
                ],
            )

    def load_runtime_states(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM runtime_states ORDER BY agent_id ASC"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_runtime_states(self, states: list[dict[str, Any]]) -> None:
        self.initialize()
        payloads = [json.dumps(state) for state in states]
        with self._connect() as connection:
            connection.execute("DELETE FROM runtime_states")
            connection.executemany(
                """
                INSERT INTO runtime_states(agent_id, runtime_status, runtime_handle, setup_status, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        state["agent_id"],
                        state["runtime_status"],
                        state.get("runtime_handle"),
                        state.get("setup_status", "unknown"),
                        payload,
                    )
                    for state, payload in zip(states, payloads, strict=True)
                ],
            )

    def load_collaboration(self) -> dict[str, list[dict[str, Any]]]:
        self.initialize()
        with self._connect() as connection:
            threads = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT payload FROM collaboration_threads ORDER BY position ASC"
                ).fetchall()
            ]
            messages = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT payload FROM collaboration_messages ORDER BY position ASC"
                ).fetchall()
            ]
            handoffs = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT payload FROM collaboration_handoffs ORDER BY position ASC"
                ).fetchall()
            ]
        return {
            "threads": threads,
            "messages": messages,
            "handoffs": handoffs,
        }

    def save_collaboration(
        self,
        *,
        threads: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        handoffs: list[dict[str, Any]],
    ) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute("DELETE FROM collaboration_threads")
            connection.execute("DELETE FROM collaboration_messages")
            connection.execute("DELETE FROM collaboration_handoffs")
            connection.executemany(
                "INSERT INTO collaboration_threads(thread_id, position, payload) VALUES (?, ?, ?)",
                [
                    (thread["thread_id"], position, json.dumps(thread))
                    for position, thread in enumerate(threads)
                ],
            )
            connection.executemany(
                "INSERT INTO collaboration_messages(message_id, position, payload) VALUES (?, ?, ?)",
                [
                    (message["message_id"], position, json.dumps(message))
                    for position, message in enumerate(messages)
                ],
            )
            connection.executemany(
                "INSERT INTO collaboration_handoffs(handoff_id, position, payload) VALUES (?, ?, ?)",
                [
                    (handoff["handoff_id"], position, json.dumps(handoff))
                    for position, handoff in enumerate(handoffs)
                ],
            )

    def get_infra_status(self, name: str) -> dict[str, str] | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT name, status, detail FROM infra_state WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        return {"name": row[0], "status": row[1], "detail": row[2]}

    def set_infra_status(self, name: str, *, status: str, detail: str = "") -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO infra_state(name, status, detail)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET status = excluded.status, detail = excluded.detail
                """,
                (name, status, detail),
            )

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
