"""Application state paths for Maia."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

__all__ = ["get_maia_home", "get_registry_path"]

_MAIA_HOME_DIRNAME = ".maia"
_REGISTRY_FILENAME = "registry.json"


def get_maia_home(env: Mapping[str, str] | None = None) -> Path:
    """Return the Maia home directory for the current environment."""

    source_env = os.environ if env is None else env
    home = source_env.get("HOME")
    if home:
        return Path(home).expanduser() / _MAIA_HOME_DIRNAME
    return Path.home() / _MAIA_HOME_DIRNAME


def get_registry_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the default registry file path."""

    return get_maia_home(env) / _REGISTRY_FILENAME
