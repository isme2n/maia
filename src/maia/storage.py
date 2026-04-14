"""JSON-backed persistence for the agent registry."""

from __future__ import annotations

import json
from pathlib import Path

from maia.agent_model import AgentRecord
from maia.registry import AgentRegistry

__all__ = ["JsonRegistryStorage"]


class JsonRegistryStorage:
    """Persist registry contents to and from a JSON file."""

    _REQUIRED_RECORD_FIELDS = ("agent_id", "name", "status", "persona")

    def save(self, path: Path | str, registry: AgentRegistry) -> None:
        """Write the registry as a single JSON object."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"agents": [record.to_dict() for record in registry.list()]}
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def load(self, path: Path | str) -> AgentRegistry:
        """Load registry contents from a JSON file, or return an empty registry."""

        target = Path(path)
        registry = AgentRegistry()

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

        for index, item in enumerate(records_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid registry JSON in {target}: agent records must be objects"
                )
            missing_fields = [
                field for field in self._REQUIRED_RECORD_FIELDS if field not in item
            ]
            if missing_fields:
                missing_fields_text = ", ".join(repr(field) for field in missing_fields)
                raise ValueError(
                    f"Invalid registry JSON in {target}: "
                    f"agent record at index {index} is missing required fields: "
                    f"{missing_fields_text}"
                )

            try:
                registry.add(AgentRecord.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid registry JSON in {target}: "
                    f"agent record at index {index} is invalid: {exc}"
                ) from exc

        return registry
