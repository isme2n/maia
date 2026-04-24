"""Persistence helpers for Maia runtime state."""

from __future__ import annotations

import json
from pathlib import Path

from maia.runtime_adapter import RuntimeState
from maia.sqlite_state import SQLiteState

__all__ = ["RuntimeStateStorage"]


class RuntimeStateStorage:
    """Persist runtime states to Maia's local SQLite state DB."""

    def load(self, path: Path | str) -> dict[str, RuntimeState]:
        target = self._require_sqlite_path(path)
        try:
            items = SQLiteState(target).load_runtime_states()
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid runtime state SQLite in {target}: {exc.msg}"
            ) from exc
        return self._deserialize_runtime_states(items, target, source_kind="SQLite")

    def save(self, path: Path | str, states: dict[str, RuntimeState]) -> None:
        target = self._require_sqlite_path(path)
        records = [states[agent_id].to_dict() for agent_id in sorted(states)]
        SQLiteState(target).save_runtime_states(records)

    def remove(self, path: Path | str, agent_id: str) -> None:
        target = self._require_sqlite_path(path)
        states = self.load(target)
        if agent_id not in states:
            return
        del states[agent_id]
        self.save(target, states)

    def _deserialize_runtime_states(
        self,
        items: list[object],
        target: Path,
        *,
        source_kind: str,
    ) -> dict[str, RuntimeState]:
        states: dict[str, RuntimeState] = {}
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid runtime state {source_kind} in {target}: runtime records must be objects"
                )
            try:
                state = RuntimeState.from_dict(item)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid runtime state {source_kind} in {target}: runtime record at index {index} is invalid: {exc}"
                ) from exc
            states[state.agent_id] = state
        return states

    def _is_sqlite_path(self, path: Path) -> bool:
        return path.suffix == ".db"

    def _require_sqlite_path(self, path: Path | str) -> Path:
        target = Path(path)
        if not self._is_sqlite_path(target):
            raise ValueError(f"Runtime state storage requires a SQLite DB path: {target}")
        return target
