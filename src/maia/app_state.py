"""Application state paths for Maia."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

__all__ = [
    "get_agent_dir",
    "get_agent_hermes_home",
    "get_agents_dir",
    "get_collaboration_path",
    "get_default_export_path",
    "get_exports_dir",
    "get_maia_home",
    "get_registry_path",
    "get_runtime_dir",
    "get_runtime_state_path",
    "get_state_db_path",
    "get_team_metadata_path",
]

_AGENT_HERMES_HOME_DIRNAME = "hermes"
_AGENTS_DIRNAME = "agents"
_MAIA_HOME_DIRNAME = ".maia"
_COLLABORATION_FILENAME = "collaboration.json"
_DEFAULT_BUNDLE_FILENAME = "maia-state.maia"
_EXPORTS_DIRNAME = "exports"
_REGISTRY_FILENAME = "registry.json"
_RUNTIME_DIRNAME = "runtime"
_RUNTIME_STATE_FILENAME = "runtime-state.json"
_STATE_DB_FILENAME = "state.db"
_TEAM_METADATA_FILENAME = "team.json"


def get_maia_home(env: Mapping[str, str] | None = None) -> Path:
    """Return the Maia home directory for the current environment."""

    source_env = os.environ if env is None else env
    home = source_env.get("HOME")
    if home:
        return Path(home).expanduser() / _MAIA_HOME_DIRNAME
    return Path.home() / _MAIA_HOME_DIRNAME


def get_agents_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory for per-agent Maia state."""

    return get_maia_home(env) / _AGENTS_DIRNAME


def get_agent_dir(agent_id: str, env: Mapping[str, str] | None = None) -> Path:
    """Return the Maia directory for one agent."""

    return get_agents_dir(env) / agent_id


def get_agent_hermes_home(agent_id: str, env: Mapping[str, str] | None = None) -> Path:
    """Return the dedicated Hermes home path for one agent."""

    return get_agent_dir(agent_id, env) / _AGENT_HERMES_HOME_DIRNAME


def get_registry_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the transitional local registry cache path."""

    return get_maia_home(env) / _REGISTRY_FILENAME


def get_collaboration_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the transitional local collaboration cache path."""

    return get_maia_home(env) / _COLLABORATION_FILENAME


def get_exports_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory for portable registry snapshots."""

    return get_maia_home(env) / _EXPORTS_DIRNAME


def get_default_export_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the default path for exporting a portable Maia bundle."""

    return get_exports_dir(env) / _DEFAULT_BUNDLE_FILENAME


def get_runtime_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory for runtime-only state."""

    return get_maia_home(env) / _RUNTIME_DIRNAME


def get_runtime_state_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the transitional local runtime state cache path."""

    return get_runtime_dir(env) / _RUNTIME_STATE_FILENAME


def get_state_db_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the local SQLite control-plane state path."""

    return get_maia_home(env) / _STATE_DB_FILENAME


def get_team_metadata_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the default path for team-level metadata."""

    return get_maia_home(env) / _TEAM_METADATA_FILENAME
