"""Persistence helpers for the Maia agent registry."""

from __future__ import annotations

import json
from pathlib import Path

from maia.agent_model import AgentRecord
from maia.registry import AgentRegistry
from maia.sqlite_state import SQLiteState

__all__ = ["JsonRegistryStorage"]


class JsonRegistryStorage:
    """Persist registry contents to JSON for export and SQLite for local state."""

    _REQUIRED_RECORD_FIELDS = ("agent_id", "name", "status", "persona")

    def save(self, path: Path | str, registry: AgentRegistry, *, portable: bool = False) -> None:
        """Write the registry to local SQLite state or to a portable JSON snapshot."""

        target = Path(path)
        if self._is_sqlite_path(target) and not portable:
            records = [self._serialize_record(record, portable=False) for record in registry.list()]
            SQLiteState(target).save_agents(records)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "agents": [
                self._serialize_record(record, portable=portable) for record in registry.list()
            ]
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _serialize_record(self, record: AgentRecord, *, portable: bool) -> dict[str, object]:
        """Serialize a record for local persistence or portable export."""

        if not portable:
            return record.to_dict()
        payload = {
            "agent_id": record.agent_id,
            "name": record.name,
            "status": record.status.value,
            "speaking_style": record.speaking_style.value,
            "persona": record.persona,
            "role": record.role,
            "model": record.model,
            "tags": list(record.tags),
        }
        if record.speaking_style.value == "custom" and record.speaking_style_details:
            payload["speaking_style_details"] = record.speaking_style_details
        return payload

    def load(self, path: Path | str) -> AgentRegistry:
        """Load registry contents from local SQLite state or portable JSON."""

        target = Path(path)
        registry = AgentRegistry()

        if self._is_sqlite_path(target):
            try:
                records_data = SQLiteState(target).load_agents()
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid registry SQLite in {target}: {exc.msg}"
                ) from exc
            return self._load_records(registry, records_data, target, source_kind="SQLite")

        if not target.exists():
            return registry

        try:
            raw_data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid registry JSON in {target}: {exc.msg}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid registry JSON in {target}: expected object")

        records_data = raw_data.get("agents")
        if not isinstance(records_data, list):
            raise ValueError(
                f"Invalid registry JSON in {target}: expected 'agents' list"
            )

        return self._load_records(registry, records_data, target, source_kind="JSON")

    def _load_records(
        self,
        registry: AgentRegistry,
        records_data: list[object],
        target: Path,
        *,
        source_kind: str,
    ) -> AgentRegistry:
        for index, item in enumerate(records_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid registry {source_kind} in {target}: agent records must be objects"
                )
            missing_fields = [
                field for field in self._REQUIRED_RECORD_FIELDS if field not in item
            ]
            if missing_fields:
                missing_fields_text = ", ".join(repr(field) for field in missing_fields)
                raise ValueError(
                    f"Invalid registry {source_kind} in {target}: "
                    f"agent record at index {index} is missing required fields: "
                    f"{missing_fields_text}"
                )

            try:
                registry.add(AgentRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid registry {source_kind} in {target}: "
                    f"agent record at index {index} is invalid: {exc}"
                ) from exc

        return registry

    def _is_sqlite_path(self, path: Path) -> bool:
        return path.suffix == ".db"
