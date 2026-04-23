"""Canonical public install/onboarding contract for Maia."""

from __future__ import annotations

from maia import __version__

__all__ = [
    "HERMES_INSTALL_SCRIPT_URL",
    "MAIA_GIT_INSTALL_SPEC",
    "MAIA_INSTALL_CURL_COMMAND",
    "MAIA_INSTALL_REF",
    "MAIA_INSTALL_SCRIPT_URL",
    "MAIA_REPOSITORY_SLUG",
]

MAIA_REPOSITORY_SLUG = "isme2n/maia"
MAIA_INSTALL_REF = f"v{__version__}"
MAIA_INSTALL_SCRIPT_URL = (
    f"https://raw.githubusercontent.com/{MAIA_REPOSITORY_SLUG}/{MAIA_INSTALL_REF}/scripts/install.sh"
)
MAIA_INSTALL_CURL_COMMAND = f"curl -fsSL {MAIA_INSTALL_SCRIPT_URL} | bash"
MAIA_GIT_INSTALL_SPEC = f"git+https://github.com/{MAIA_REPOSITORY_SLUG}.git@{MAIA_INSTALL_REF}"
HERMES_INSTALL_SCRIPT_URL = (
    "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh"
)
