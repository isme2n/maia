"""Legacy collaboration snapshot helpers for Maia.

These helpers are retained only for transitional caches and non-active
compatibility tests. Maia's active collaboration contract is Keryx-backed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from maia.app_state import get_collaboration_path
from maia.handoff_model import HandoffRecord
from maia.message_model import MessageRecord, ThreadRecord
from maia.sqlite_state import SQLiteState

__all__ = ["CollaborationState", "CollaborationStorage"]


@dataclass(slots=True)
class CollaborationState:
    threads: list[ThreadRecord]
    messages: list[MessageRecord]
    handoffs: list[HandoffRecord] = field(default_factory=list)


class CollaborationStorage:
    """Persist legacy collaboration snapshots to SQLite or transitional JSON cache files."""

    def save(
        self,
        path: Path | str,
        *,
        threads: list[ThreadRecord],
        messages: list[MessageRecord],
        handoffs: list[HandoffRecord] | None = None,
    ) -> None:
        target = Path(path)
        if self._is_sqlite_path(target):
            effective_handoffs = handoffs
            if effective_handoffs is None:
                effective_handoffs = self.load(target).handoffs
            thread_payloads = [thread.to_dict() for thread in threads]
            message_payloads = [message.to_dict() for message in messages]
            handoff_payloads = [handoff.to_dict() for handoff in effective_handoffs or []]
            SQLiteState(target).save_collaboration(
                threads=thread_payloads,
                messages=message_payloads,
                handoffs=handoff_payloads,
            )
            cache_path = self._json_cache_path(target)
            self._write_json_payload(
                cache_path,
                {
                    "threads": thread_payloads,
                    "messages": message_payloads,
                    "handoffs": handoff_payloads,
                },
            )
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if handoffs is None and target.exists():
            handoffs = self.load(target).handoffs
        payload = {
            "threads": [thread.to_dict() for thread in threads],
            "messages": [message.to_dict() for message in messages],
            "handoffs": [handoff.to_dict() for handoff in handoffs or []],
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def load(self, path: Path | str) -> CollaborationState:
        target = Path(path)
        if self._is_sqlite_path(target):
            try:
                raw_data = SQLiteState(target).load_collaboration()
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid collaboration SQLite in {target}: {exc.msg}"
                ) from exc
            return self._deserialize(raw_data, target, source_kind="SQLite")
        if not target.exists():
            return CollaborationState(threads=[], messages=[], handoffs=[])
        try:
            raw_data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid collaboration JSON in {target}: {exc.msg}") from exc

        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid collaboration JSON in {target}: expected object")
        return self._deserialize(raw_data, target, source_kind="JSON")

    def _deserialize(
        self,
        raw_data: dict[str, object],
        target: Path,
        *,
        source_kind: str,
    ) -> CollaborationState:
        threads_data = raw_data.get("threads")
        messages_data = raw_data.get("messages")
        handoffs_data = raw_data.get("handoffs", [])
        if not isinstance(threads_data, list):
            raise ValueError(
                f"Invalid collaboration {source_kind} in {target}: expected 'threads' list"
            )
        if not isinstance(messages_data, list):
            raise ValueError(
                f"Invalid collaboration {source_kind} in {target}: expected 'messages' list"
            )
        if not isinstance(handoffs_data, list):
            raise ValueError(
                f"Invalid collaboration {source_kind} in {target}: expected 'handoffs' list"
            )

        threads: list[ThreadRecord] = []
        for index, item in enumerate(threads_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid collaboration {source_kind} in {target}: thread records must be objects"
                )
            try:
                threads.append(ThreadRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid collaboration {source_kind} in {target}: thread record at index {index} is invalid: {exc}"
                ) from exc

        messages: list[MessageRecord] = []
        for index, item in enumerate(messages_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid collaboration {source_kind} in {target}: message records must be objects"
                )
            try:
                messages.append(MessageRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid collaboration {source_kind} in {target}: message record at index {index} is invalid: {exc}"
                ) from exc

        handoffs: list[HandoffRecord] = []
        for index, item in enumerate(handoffs_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid collaboration {source_kind} in {target}: handoff records must be objects"
                )
            try:
                handoffs.append(HandoffRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid collaboration {source_kind} in {target}: handoff record at index {index} is invalid: {exc}"
                ) from exc

        return CollaborationState(threads=threads, messages=messages, handoffs=handoffs)

    def _is_sqlite_path(self, path: Path) -> bool:
        return path.suffix == ".db"

    def _json_cache_path(self, state_db_path: Path) -> Path:
        return get_collaboration_path({"HOME": str(state_db_path.parent.parent)})

    def _write_json_payload(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        labeled_payload = {
            "_maia_local_state": True,
            "_maia_storage_kind": "transitional-json-cache",
            **payload,
        }
        path.write_text(json.dumps(labeled_payload, indent=2) + "\n", encoding="utf-8")
