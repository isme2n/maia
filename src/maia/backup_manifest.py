"""Portable backup manifest helpers for Maia registry snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import socket
import sys

from maia import __version__
from maia.team_metadata import TeamMetadata, default_team_metadata

__all__ = [
    "BackupManifest",
    "load_backup_manifest",
    "write_backup_manifest",
]

_MANIFEST_KIND = "maia-backup-manifest"
_MANIFEST_VERSION = 1
_PORTABLE_SCOPE_VERSION = 3
_SUPPORTED_SCOPE_VERSIONS = {1, 2, 3}
_PORTABLE_STATE_KINDS = ["registry", "team-metadata", "agent-profile-metadata"]
_RUNTIME_ONLY_PATHS = ["runtime/"]
_RUNTIME_ONLY_STATE_KINDS = ["processes", "locks", "cache", "live-sessions"]


@dataclass(frozen=True)
class BackupManifest:
    """Description of a portable Maia backup bundle."""

    kind: str
    version: int
    scope_version: int
    created_at: str
    label: str
    description: str
    created_by: str
    maia_version: str
    source_host: str
    source_platform: str
    source_registry_path: str
    registry_file: str
    portable_paths: list[str]
    portable_state_kinds: list[str]
    runtime_only_paths: list[str]
    runtime_only_state_kinds: list[str]
    agents: int
    team_name: str
    team_description: str
    team_tags: list[str]
    default_agent_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "version": self.version,
            "scope_version": self.scope_version,
            "created_at": self.created_at,
            "label": self.label,
            "description": self.description,
            "created_by": self.created_by,
            "maia_version": self.maia_version,
            "source_host": self.source_host,
            "source_platform": self.source_platform,
            "source_registry_path": self.source_registry_path,
            "registry_file": self.registry_file,
            "portable_paths": self.portable_paths,
            "portable_state_kinds": self.portable_state_kinds,
            "runtime_only_paths": self.runtime_only_paths,
            "runtime_only_state_kinds": self.runtime_only_state_kinds,
            "agents": self.agents,
            "team_name": self.team_name,
            "team_description": self.team_description,
            "team_tags": self.team_tags,
            "default_agent_id": self.default_agent_id,
        }


def write_backup_manifest(
    export_path: Path | str,
    agent_count: int,
    *,
    label: str | None = None,
    description: str | None = None,
    source_registry_path: Path | str | None = None,
    team_metadata: TeamMetadata | None = None,
) -> Path:
    """Write a manifest next to an exported registry snapshot and return its path."""

    registry_path = Path(export_path)
    manifest_path = registry_path.parent / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_registry = Path(source_registry_path) if source_registry_path is not None else registry_path
    metadata = default_team_metadata() if team_metadata is None else team_metadata
    manifest = BackupManifest(
        kind=_MANIFEST_KIND,
        version=_MANIFEST_VERSION,
        scope_version=_PORTABLE_SCOPE_VERSION,
        created_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        label=label or registry_path.stem,
        description=description or f"Portable Maia export with {agent_count} agent(s)",
        created_by="maia-cli",
        maia_version=__version__,
        source_host=socket.gethostname(),
        source_platform=sys.platform,
        source_registry_path=str(source_registry),
        registry_file=registry_path.name,
        portable_paths=[registry_path.name],
        portable_state_kinds=list(_PORTABLE_STATE_KINDS),
        runtime_only_paths=list(_RUNTIME_ONLY_PATHS),
        runtime_only_state_kinds=list(_RUNTIME_ONLY_STATE_KINDS),
        agents=agent_count,
        team_name=metadata.team_name,
        team_description=metadata.team_description,
        team_tags=list(metadata.team_tags),
        default_agent_id=metadata.default_agent_id,
    )
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    return manifest_path


def load_backup_manifest(path: Path | str) -> BackupManifest:
    """Load and validate a Maia backup manifest from JSON."""

    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: {exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid backup manifest JSON in {manifest_path}: expected object")

    required_fields = {
        "kind": str,
        "version": int,
        "scope_version": int,
        "created_at": str,
        "registry_file": str,
        "portable_paths": list,
        "portable_state_kinds": list,
        "runtime_only_paths": list,
        "runtime_only_state_kinds": list,
        "agents": int,
    }
    optional_string_fields = (
        "label",
        "description",
        "created_by",
        "maia_version",
        "source_host",
        "source_platform",
        "source_registry_path",
        "team_name",
        "team_description",
        "default_agent_id",
    )
    for field_name, expected_type in required_fields.items():
        if field_name not in payload:
            raise ValueError(
                f"Invalid backup manifest JSON in {manifest_path}: missing {field_name!r}"
            )
        if not isinstance(payload[field_name], expected_type):
            raise ValueError(
                f"Invalid backup manifest JSON in {manifest_path}: "
                f"field {field_name!r} must be {expected_type.__name__}"
            )

    for field_name in optional_string_fields:
        if field_name in payload and not isinstance(payload[field_name], str):
            raise ValueError(
                f"Invalid backup manifest JSON in {manifest_path}: "
                f"field {field_name!r} must be str"
            )

    if payload["kind"] != _MANIFEST_KIND:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: unsupported kind {payload['kind']!r}"
        )
    if payload["version"] != _MANIFEST_VERSION:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: unsupported version {payload['version']!r}"
        )
    if payload["scope_version"] not in _SUPPORTED_SCOPE_VERSIONS:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: unsupported scope_version {payload['scope_version']!r}"
        )
    if not payload["registry_file"]:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: registry_file must not be empty"
        )
    if payload["registry_file"] in {".", ".."} or "/" in payload["registry_file"]:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: registry_file must be a file name"
        )
    if any(
        not isinstance(item, str) or not item for item in payload["portable_paths"]
    ):
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            "portable_paths must contain only non-empty strings"
        )
    if any(
        not isinstance(item, str) or not item
        for item in payload["portable_state_kinds"]
    ):
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            "portable_state_kinds must contain only non-empty strings"
        )
    if any(
        not isinstance(item, str) or not item for item in payload["runtime_only_paths"]
    ):
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            "runtime_only_paths must contain only non-empty strings"
        )
    if any(
        not isinstance(item, str) or not item
        for item in payload["runtime_only_state_kinds"]
    ):
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            "runtime_only_state_kinds must contain only non-empty strings"
        )
    if payload["registry_file"] not in payload["portable_paths"]:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            "portable_paths must include registry_file"
        )
    if "team_tags" in payload and (
        not isinstance(payload["team_tags"], list)
        or any(not isinstance(item, str) or not item for item in payload["team_tags"])
    ):
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: team_tags must contain only non-empty strings"
        )
    portable_path_list = payload["portable_paths"]
    runtime_only_path_list = payload["runtime_only_paths"]
    if portable_path_list != [payload["registry_file"]]:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            f"portable_paths must match {[payload['registry_file']]!r}"
        )
    if runtime_only_path_list != _RUNTIME_ONLY_PATHS:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            f"runtime_only_paths must match {_RUNTIME_ONLY_PATHS!r}"
        )
    portable_state_kind_list = payload["portable_state_kinds"]
    runtime_only_state_kind_list = payload["runtime_only_state_kinds"]
    if payload["scope_version"] == 1:
        expected_portable_state_kinds = ["registry"]
    elif payload["scope_version"] == 2:
        expected_portable_state_kinds = ["registry", "team-metadata"]
    else:
        expected_portable_state_kinds = _PORTABLE_STATE_KINDS
    if portable_state_kind_list != expected_portable_state_kinds:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            f"portable_state_kinds must match {expected_portable_state_kinds!r}"
        )
    if runtime_only_state_kind_list != _RUNTIME_ONLY_STATE_KINDS:
        raise ValueError(
            f"Invalid backup manifest JSON in {manifest_path}: "
            f"runtime_only_state_kinds must match {_RUNTIME_ONLY_STATE_KINDS!r}"
        )

    return BackupManifest(
        kind=payload["kind"],
        version=payload["version"],
        scope_version=payload["scope_version"],
        created_at=payload["created_at"],
        label=payload.get("label", Path(payload["registry_file"]).stem),
        description=payload.get(
            "description",
            f"Portable Maia export with {payload['agents']} agent(s)",
        ),
        created_by=payload.get("created_by", "maia-cli"),
        maia_version=payload.get("maia_version", "unknown"),
        source_host=payload.get("source_host", "unknown"),
        source_platform=payload.get("source_platform", "unknown"),
        source_registry_path=payload.get(
            "source_registry_path",
            payload["registry_file"],
        ),
        registry_file=payload["registry_file"],
        portable_paths=list(payload["portable_paths"]),
        portable_state_kinds=list(payload["portable_state_kinds"]),
        runtime_only_paths=list(payload["runtime_only_paths"]),
        runtime_only_state_kinds=list(payload["runtime_only_state_kinds"]),
        agents=payload["agents"],
        team_name=payload.get("team_name", ""),
        team_description=payload.get("team_description", ""),
        team_tags=list(payload.get("team_tags", [])),
        default_agent_id=payload.get("default_agent_id", ""),
    )
