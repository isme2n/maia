"""Persistence helpers for Maia runtime state."""

from __future__ import annotations

import json
from pathlib import Path

from maia.app_state import get_runtime_state_path
from maia.runtime_adapter import RuntimeState
from maia.sqlite_state import SQLiteState

__all__ = ["RuntimeStateStorage"]


class RuntimeStateStorage:
    """Persist runtime states to local SQLite state or transitional JSON files."""

    def load(self, path: Path | str) -> dict[str, RuntimeState]:
        target = Path(path)
        if self._is_sqlite_path(target):
            try:
                items = SQLiteState(target).load_runtime_states()
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid runtime state SQLite in {target}: {exc.msg}"
                ) from exc
            return self._deserialize_runtime_states(items, target, source_kind="SQLite")
        if not target.exists():
            return {}
        try:
            raw_data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid runtime state JSON in {target}: {exc.msg}") from exc
        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid runtime state JSON in {target}: expected object")
        items = raw_data.get("runtimes")
        if not isinstance(items, list):
            raise ValueError(f"Invalid runtime state JSON in {target}: expected 'runtimes' list")
        return self._deserialize_runtime_states(items, target, source_kind="JSON")

    def save(self, path: Path | str, states: dict[str, RuntimeState]) -> None:
        target = Path(path)
        if self._is_sqlite_path(target):
            records = [states[agent_id].to_dict() for agent_id in sorted(states)]
            SQLiteState(target).save_runtime_states(records)
            cache_path = self._json_cache_path(target)
            self._write_json_payload(cache_path, {"runtimes": records})
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "runtimes": [states[agent_id].to_dict() for agent_id in sorted(states)]
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def remove(self, path: Path | str, agent_id: str) -> None:
        states = self.load(path)
        if agent_id not in states:
            return
        del states[agent_id]
        self.save(path, states)

    def prune(self, path: Path | str, valid_agent_ids: set[str]) -> None:
        states = self.load(path)
        pruned = {
            agent_id: state
            for agent_id, state in states.items()
            if agent_id in valid_agent_ids
        }
        if pruned == states and (self._is_sqlite_path(Path(path)) or Path(path).exists()):
            return
        self.save(path, pruned)

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

    def _json_cache_path(self, state_db_path: Path) -> Path:
        return get_runtime_state_path({"HOME": str(state_db_path.parent.parent)})

    def _write_json_payload(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        labeled_payload = {
            "_maia_local_state": True,
            "_maia_storage_kind": "transitional-json-cache",
            **payload,
        }
        path.write_text(json.dumps(labeled_payload, indent=2) + "\n", encoding="utf-8")
