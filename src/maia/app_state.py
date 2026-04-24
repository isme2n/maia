"""Application state paths for Maia."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

__all__ = [
    "get_agent_dir",
    "get_agent_hermes_home",
    "get_agents_dir",
    "get_default_export_path",
    "get_exports_dir",
    "get_maia_home",
    "get_state_db_path",
    "get_team_metadata_path",
]

_AGENT_HERMES_HOME_DIRNAME = "hermes"
_AGENTS_DIRNAME = "agents"
_MAIA_HOME_DIRNAME = ".maia"
_DEFAULT_BUNDLE_FILENAME = "maia-state.maia"
_EXPORTS_DIRNAME = "exports"
_STATE_DB_FILENAME = "maia.db"
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


def get_exports_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory for portable registry snapshots."""

    return get_maia_home(env) / _EXPORTS_DIRNAME


def get_default_export_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the default path for exporting a portable Maia bundle."""

    return get_exports_dir(env) / _DEFAULT_BUNDLE_FILENAME


def get_state_db_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the local SQLite control-plane state path."""

    return get_maia_home(env) / _STATE_DB_FILENAME


def get_team_metadata_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the default path for team-level metadata."""

    return get_maia_home(env) / _TEAM_METADATA_FILENAME
