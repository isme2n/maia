"""Team-level metadata helpers for Maia portable state."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

__all__ = [
    "TeamMetadata",
    "default_team_metadata",
    "load_team_metadata",
    "save_team_metadata",
]


@dataclass(frozen=True)
class TeamMetadata:
    team_name: str
    team_description: str
    team_tags: list[str]
    default_agent_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "team_name": self.team_name,
            "team_description": self.team_description,
            "team_tags": list(self.team_tags),
            "default_agent_id": self.default_agent_id,
        }


def default_team_metadata() -> TeamMetadata:
    return TeamMetadata(
        team_name="",
        team_description="",
        team_tags=[],
        default_agent_id="",
    )


def load_team_metadata(path: Path | str) -> TeamMetadata:
    metadata_path = Path(path)
    if not metadata_path.exists():
        return default_team_metadata()
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid team metadata JSON in {metadata_path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid team metadata JSON in {metadata_path}: expected object")

    team_name = payload.get("team_name", "")
    team_description = payload.get("team_description", "")
    team_tags = payload.get("team_tags", [])
    default_agent_id = payload.get("default_agent_id", "")

    if not isinstance(team_name, str):
        raise ValueError(f"Invalid team metadata JSON in {metadata_path}: 'team_name' must be str")
    if not isinstance(team_description, str):
        raise ValueError(
            f"Invalid team metadata JSON in {metadata_path}: 'team_description' must be str"
        )
    if not isinstance(default_agent_id, str):
        raise ValueError(
            f"Invalid team metadata JSON in {metadata_path}: 'default_agent_id' must be str"
        )
    if not isinstance(team_tags, list) or any(not isinstance(item, str) or not item for item in team_tags):
        raise ValueError(
            f"Invalid team metadata JSON in {metadata_path}: 'team_tags' must be a list of non-empty strings"
        )

    return TeamMetadata(
        team_name=team_name,
        team_description=team_description,
        team_tags=list(team_tags),
        default_agent_id=default_agent_id,
    )


def save_team_metadata(path: Path | str, metadata: TeamMetadata) -> Path:
    metadata_path = Path(path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2) + "\n", encoding="utf-8")
    return metadata_path
