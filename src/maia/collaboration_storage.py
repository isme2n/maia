"""JSON-backed persistence for Maia collaboration state."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from maia.message_model import MessageRecord, ThreadRecord

__all__ = ["CollaborationState", "CollaborationStorage"]


@dataclass(slots=True)
class CollaborationState:
    threads: list[ThreadRecord]
    messages: list[MessageRecord]


class CollaborationStorage:
    """Persist threads and messages to a single JSON file."""

    def save(
        self,
        path: Path | str,
        *,
        threads: list[ThreadRecord],
        messages: list[MessageRecord],
    ) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "threads": [thread.to_dict() for thread in threads],
            "messages": [message.to_dict() for message in messages],
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def load(self, path: Path | str) -> CollaborationState:
        target = Path(path)
        if not target.exists():
            return CollaborationState(threads=[], messages=[])
        try:
            raw_data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid collaboration JSON in {target}: {exc.msg}") from exc

        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid collaboration JSON in {target}: expected object")

        threads_data = raw_data.get("threads")
        messages_data = raw_data.get("messages")
        if not isinstance(threads_data, list):
            raise ValueError(
                f"Invalid collaboration JSON in {target}: expected 'threads' list"
            )
        if not isinstance(messages_data, list):
            raise ValueError(
                f"Invalid collaboration JSON in {target}: expected 'messages' list"
            )

        threads: list[ThreadRecord] = []
        for index, item in enumerate(threads_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid collaboration JSON in {target}: thread records must be objects"
                )
            try:
                threads.append(ThreadRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid collaboration JSON in {target}: thread record at index {index} is invalid: {exc}"
                ) from exc

        messages: list[MessageRecord] = []
        for index, item in enumerate(messages_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid collaboration JSON in {target}: message records must be objects"
                )
            try:
                messages.append(MessageRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid collaboration JSON in {target}: message record at index {index} is invalid: {exc}"
                ) from exc

        return CollaborationState(threads=threads, messages=messages)
