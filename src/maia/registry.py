"""In-memory registry for agent records."""

from __future__ import annotations

from dataclasses import replace

from maia.agent_model import AgentRecord, AgentSetupStatus, AgentStatus, RuntimeSpec

__all__ = ["AgentRegistry"]


class AgentRegistry:
    """Manage agent records in insertion order."""

    def __init__(self) -> None:
        self._records: dict[str, AgentRecord] = {}
        self._order: list[str] = []

    def add(self, record: AgentRecord) -> None:
        """Store a new record, preserving insertion order."""

        if record.agent_id in self._records:
            raise ValueError(f"Agent with id {record.agent_id!r} already exists")

        self._records[record.agent_id] = _clone_record(record)
        self._order.append(record.agent_id)

    def get(self, agent_id: str) -> AgentRecord:
        """Return a copy of the stored record for the given id."""

        return _clone_record(self._require(agent_id))

    def list(self) -> list[AgentRecord]:
        """Return all stored records in insertion order."""

        return [_clone_record(self._records[agent_id]) for agent_id in self._order]

    def set_status(self, agent_id: str, status: AgentStatus) -> AgentRecord:
        """Update the status for an existing record and return the new value."""

        record = self._require(agent_id)
        updated = replace(record, status=status)
        self._records[agent_id] = updated
        return _clone_record(updated)

    def set_persona(self, agent_id: str, persona: str) -> AgentRecord:
        """Update the persona for an existing record and return the new value."""

        record = self._require(agent_id)
        updated = replace(record, persona=persona)
        self._records[agent_id] = updated
        return _clone_record(updated)

    def set_speaking_style(
        self,
        agent_id: str,
        *,
        speaking_style: str,
        speaking_style_details: str,
    ) -> AgentRecord:
        """Update speaking-style metadata for an existing record."""

        record = self._require(agent_id)
        updated = replace(
            record,
            speaking_style=speaking_style,
            speaking_style_details=speaking_style_details,
        )
        self._records[agent_id] = updated
        return _clone_record(updated)

    def set_has_started(self, agent_id: str, has_started: bool) -> AgentRecord:
        """Update whether the agent has started before and return the new value."""

        record = self._require(agent_id)
        updated = replace(record, has_started=has_started)
        self._records[agent_id] = updated
        return _clone_record(updated)

    def set_profile_metadata(
        self,
        agent_id: str,
        *,
        role: str | None = None,
        model: str | None = None,
        tags: list[str] | None = None,
    ) -> AgentRecord:
        """Update agent profile metadata and return the new value."""

        record = self._require(agent_id)
        updated = replace(
            record,
            role=record.role if role is None else role,
            model=record.model if model is None else model,
            tags=list(record.tags) if tags is None else list(tags),
        )
        self._records[agent_id] = updated
        return _clone_record(updated)

    def set_runtime_spec(
        self,
        agent_id: str,
        runtime_spec: RuntimeSpec | None,
    ) -> AgentRecord:
        """Replace the runtime spec for an existing record and return the new value."""

        record = self._require(agent_id)
        updated = replace(
            record,
            runtime_spec=runtime_spec,
            setup_status=(
                AgentSetupStatus.CONFIGURED
                if runtime_spec is not None
                else AgentSetupStatus.NOT_CONFIGURED
            ),
            has_started=(record.has_started if runtime_spec == record.runtime_spec else False),
        )
        self._records[agent_id] = updated
        return _clone_record(updated)

    def remove(self, agent_id: str) -> AgentRecord:
        """Remove an existing record and return the removed value."""

        record = self._require(agent_id)
        del self._records[agent_id]
        self._order.remove(agent_id)
        return _clone_record(record)

    def _require(self, agent_id: str) -> AgentRecord:
        try:
            return self._records[agent_id]
        except KeyError as exc:
            raise LookupError(f"Agent with id {agent_id!r} not found") from exc


def _clone_record(record: AgentRecord) -> AgentRecord:
    return replace(record, tags=list(record.tags))
