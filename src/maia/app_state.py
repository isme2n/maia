"""Application state paths for Maia."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

__all__ = [
    "get_default_export_path",
    "get_exports_dir",
    "get_maia_home",
    "get_registry_path",
    "get_runtime_dir",
]

_MAIA_HOME_DIRNAME = ".maia"
_EXPORTS_DIRNAME = "exports"
_REGISTRY_FILENAME = "registry.json"
_RUNTIME_DIRNAME = "runtime"


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


def get_exports_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory for portable registry snapshots."""

    return get_maia_home(env) / _EXPORTS_DIRNAME


def get_runtime_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory reserved for runtime-only state."""

    return get_maia_home(env) / _RUNTIME_DIRNAME


def get_default_export_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the default path for exporting a portable registry snapshot."""

    return get_exports_dir(env) / _REGISTRY_FILENAME
