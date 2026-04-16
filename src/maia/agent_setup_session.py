"""Agent-specific Hermes setup passthrough helpers for Maia."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess

from maia.app_state import get_agent_hermes_home

__all__ = ["AgentSetupSessionResult", "run_agent_setup_session"]


@dataclass(slots=True)
class AgentSetupSessionResult:
    """Outcome from running an agent-scoped `hermes setup` session."""

    exit_code: int
    hermes_home: Path
    setup_status: str


def run_agent_setup_session(*, agent_id: str, agent_name: str) -> AgentSetupSessionResult:
    """Run `hermes setup` in an agent-scoped Hermes home and return the outcome."""

    hermes_bin = shutil.which("hermes")
    if hermes_bin is None:
        raise ValueError(
            f"Can't open Hermes setup for {agent_name!r} because the Hermes CLI was not found in PATH"
        )

    hermes_home = get_agent_hermes_home(agent_id)
    hermes_home.mkdir(parents=True, exist_ok=True)

    child_env = os.environ.copy()
    child_env["HERMES_HOME"] = str(hermes_home)
    child_env["MAIA_AGENT_ID"] = agent_id
    child_env["MAIA_AGENT_NAME"] = agent_name

    try:
        completed = subprocess.run([hermes_bin, "setup"], env=child_env, check=False)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValueError(
            f"Can't open Hermes setup for {agent_name!r}: {detail}"
        ) from exc

    exit_code = completed.returncode if completed.returncode >= 0 else 128 + abs(completed.returncode)
    return AgentSetupSessionResult(
        exit_code=exit_code,
        hermes_home=hermes_home,
        setup_status="complete" if exit_code == 0 else "incomplete",
    )
