"""Agent-specific Hermes setup passthrough helpers for Maia."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess

from maia.app_state import get_agent_hermes_home
from maia.keryx_skill import ensure_keryx_skill_installed

__all__ = [
    "AgentSetupSessionResult",
    "derive_gateway_setup_status",
    "run_agent_setup_session",
]


_GATEWAY_ENV_SPECS: tuple[tuple[str, str, str | None], ...] = (
    ("TELEGRAM_BOT_TOKEN", "Telegram", "TELEGRAM_HOME_CHANNEL"),
    ("DISCORD_BOT_TOKEN", "Discord", "DISCORD_HOME_CHANNEL"),
    ("SLACK_BOT_TOKEN", "Slack", "SLACK_HOME_CHANNEL"),
    ("MATTERMOST_TOKEN", "Mattermost", "MATTERMOST_HOME_CHANNEL"),
    ("BLUEBUBBLES_SERVER_URL", "BlueBubbles", "BLUEBUBBLES_HOME_CHANNEL"),
    ("SIGNAL_HTTP_URL", "Signal", None),
    ("EMAIL_ADDRESS", "Email", None),
    ("TWILIO_ACCOUNT_SID", "SMS", None),
    ("MATRIX_ACCESS_TOKEN", "Matrix", None),
    ("MATRIX_PASSWORD", "Matrix", None),
    ("WHATSAPP_ENABLED", "WhatsApp", None),
    ("DINGTALK_CLIENT_ID", "DingTalk", None),
    ("FEISHU_APP_ID", "Feishu", None),
    ("WECOM_BOT_ID", "WeCom", None),
    ("WECOM_CALLBACK_CORP_ID", "WeCom Callback", None),
    ("WEIXIN_ACCOUNT_ID", "Weixin", None),
    ("WEBHOOK_ENABLED", "Webhooks", None),
)


@dataclass(slots=True)
class AgentSetupSessionResult:
    """Outcome from running an agent-scoped `hermes setup` session."""

    exit_code: int
    hermes_home: Path
    setup_status: str
    gateway_setup_status: str


def _load_env_values(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def derive_gateway_setup_status(hermes_home: Path) -> str:
    """Return whether the agent-scoped Hermes home has a usable gateway config."""

    env_values = _load_env_values(hermes_home / ".env")
    for primary_key, _label, home_key in _GATEWAY_ENV_SPECS:
        primary_value = env_values.get(primary_key, "").strip()
        if not primary_value or primary_value.lower() in {"0", "false", "no", "off"}:
            continue
        if home_key is None:
            return "complete"
        if env_values.get(home_key, "").strip():
            return "complete"
        return "token-only"
    return "incomplete"


def run_agent_setup_session(
    *,
    agent_id: str,
    agent_name: str,
    setup_target: str | None = None,
) -> AgentSetupSessionResult:
    """Run `hermes setup` in an agent-scoped Hermes home and return the outcome."""

    hermes_bin = shutil.which("hermes")
    if hermes_bin is None:
        raise ValueError(
            f"Can't open Hermes setup for {agent_name!r} because the Hermes CLI was not found in PATH"
        )

    hermes_home = get_agent_hermes_home(agent_id)
    hermes_home.mkdir(parents=True, exist_ok=True)
    ensure_keryx_skill_installed(hermes_home)

    child_env = os.environ.copy()
    child_env["HERMES_HOME"] = str(hermes_home)
    child_env["MAIA_AGENT_ID"] = agent_id
    child_env["MAIA_AGENT_NAME"] = agent_name

    command = [hermes_bin, "setup"]
    if setup_target:
        command.append(setup_target)

    try:
        completed = subprocess.run(command, env=child_env, check=False)
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValueError(
            f"Can't open Hermes setup for {agent_name!r}: {detail}"
        ) from exc

    exit_code = completed.returncode if completed.returncode >= 0 else 128 + abs(completed.returncode)
    ensure_keryx_skill_installed(hermes_home)
    gateway_setup_status = (
        derive_gateway_setup_status(hermes_home) if exit_code == 0 else "incomplete"
    )
    return AgentSetupSessionResult(
        exit_code=exit_code,
        hermes_home=hermes_home,
        setup_status="complete" if exit_code == 0 else "incomplete",
        gateway_setup_status=gateway_setup_status,
    )
