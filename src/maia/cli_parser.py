"""Argument parser construction for Maia CLI."""

from __future__ import annotations

import argparse

from maia.agent_model import AgentStatus

TOP_LEVEL_TRANSFER_COMMANDS = ("export", "import", "inspect")
TOP_LEVEL_INFO_COMMANDS = ("doctor",)
TOP_LEVEL_COLLAB_COMMANDS = ("send", "inbox", "thread", "reply")
AGENT_COMMANDS = (
    "new",
    "start",
    "stop",
    "archive",
    "restore",
    "status",
    "list",
    "tune",
    "purge",
)
TEAM_COMMANDS = ("show", "update")
LIFECYCLE_STATUS_BY_COMMAND = {
    "start": AgentStatus.RUNNING,
    "stop": AgentStatus.STOPPED,
    "archive": AgentStatus.ARCHIVED,
    "restore": AgentStatus.STOPPED,
}
AGENT_ID_COMMANDS = frozenset({"status", "tune", "purge", *LIFECYCLE_STATUS_BY_COMMAND})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maia",
        description="Maia control plane CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(parser=parser)

    top_level = parser.add_subparsers(dest="resource")

    for command_name in TOP_LEVEL_TRANSFER_COMMANDS:
        transfer_help = {
            "export": "Export Maia portable state",
            "import": "Import Maia portable state safely",
            "inspect": "Inspect an importable Maia snapshot",
        }[command_name]
        command_parser = top_level.add_parser(
            command_name,
            help=transfer_help,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command_parser.set_defaults(parser=command_parser)
        if command_name == "export":
            command_parser.epilog = (
                "Examples:\n"
                "  maia export\n"
                "  maia export backups/team.maia\n"
                "  maia export backups/team.maia --label prod --description 'Nightly snapshot'"
            )
            command_parser.add_argument(
                "path",
                nargs="?",
                help="Write a Maia bundle (.maia) or raw registry snapshot path",
            )
            command_parser.add_argument(
                "--label",
                help="Override the bundle label stored in manifest metadata",
            )
            command_parser.add_argument(
                "--description",
                help="Override the bundle description stored in manifest metadata",
            )
        if command_name in {"import", "inspect"}:
            if command_name == "import":
                command_parser.epilog = (
                    "Examples:\n"
                    "  maia import backups/team.maia --preview\n"
                    "  maia import backups/team.maia --preview --verbose-preview\n"
                    "  maia import backups/team.maia\n"
                    "  maia import backups/team.maia --yes"
                )
            if command_name == "inspect":
                command_parser.epilog = (
                    "Examples:\n"
                    "  maia inspect backups/team.maia\n"
                    "  maia inspect backups/manifest.json"
                )
            command_parser.add_argument(
                "path",
                help="Read a .maia bundle, manifest.json, or raw registry snapshot path",
            )
        if command_name == "import":
            command_parser.add_argument(
                "--preview",
                action="store_true",
                help="Show the import preview and risk summary without changing local Maia state",
            )
            command_parser.add_argument(
                "--verbose-preview",
                action="store_true",
                help="Show full added/removed/changed preview lists without truncation",
            )
            command_parser.add_argument(
                "--yes",
                action="store_true",
                help="Skip overwrite confirmation for destructive imports",
            )

    for command_name in TOP_LEVEL_INFO_COMMANDS:
        help_text = {
            "doctor": "Check local Phase 4 runtime prerequisites",
        }[command_name]
        command_parser = top_level.add_parser(
            command_name,
            help=help_text,
            description=help_text,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command_parser.set_defaults(parser=command_parser)
        if command_name == "doctor":
            command_parser.epilog = (
                "Examples:\n"
                "  maia doctor"
            )

    for command_name in TOP_LEVEL_COLLAB_COMMANDS:
        help_text = {
            "send": "Send a collaboration message",
            "inbox": "Show an agent inbox",
            "thread": "Show a collaboration thread",
            "reply": "Reply to an existing message",
        }[command_name]
        command_parser = top_level.add_parser(command_name, help=help_text)
        command_parser.set_defaults(parser=command_parser)
        if command_name == "send":
            command_parser.add_argument("from_agent", help="Sender agent id")
            command_parser.add_argument("to_agent", help="Recipient agent id")
            command_parser.add_argument("--body", required=True, help="Message body")
            route_group = command_parser.add_mutually_exclusive_group(required=True)
            route_group.add_argument("--topic", help="Topic for creating a new thread")
            route_group.add_argument("--thread-id", help="Existing thread id")
            command_parser.add_argument(
                "--kind",
                choices=("request", "question", "answer", "report", "handoff", "note"),
                default="request",
                help="Message kind",
            )
        if command_name == "inbox":
            command_parser.add_argument("agent_id", help="Agent id")
            command_parser.add_argument("--limit", type=int, default=20, help="Max messages to show")
        if command_name == "thread":
            command_parser.add_argument("thread_id", help="Thread id")
            command_parser.add_argument("--limit", type=int, default=50, help="Max messages to show")
        if command_name == "reply":
            command_parser.add_argument("message_id", help="Message id to reply to")
            command_parser.add_argument("--from-agent", required=True, help="Reply sender agent id")
            command_parser.add_argument("--body", required=True, help="Reply body")
            command_parser.add_argument(
                "--kind",
                choices=("answer", "report", "note"),
                default="answer",
                help="Reply message kind",
            )

    agent_parser = top_level.add_parser("agent", help="Manage agents")
    agent_parser.set_defaults(parser=agent_parser)

    agent_commands = agent_parser.add_subparsers(
        dest="agent_command",
        metavar="{" + ",".join(AGENT_COMMANDS) + "}",
    )
    for command_name in AGENT_COMMANDS:
        command_parser = agent_commands.add_parser(command_name, help=f"{command_name} agent")
        command_parser.set_defaults(parser=command_parser)
        if command_name == "new":
            command_parser.add_argument("name", help="Agent name")
        if command_name in AGENT_ID_COMMANDS:
            command_parser.add_argument("agent_id", help="Agent id")
        if command_name == "tune":
            persona_group = command_parser.add_mutually_exclusive_group()
            persona_group.add_argument(
                "--persona",
                help="Persona text to store for the agent",
            )
            persona_group.add_argument(
                "--persona-file",
                help="UTF-8 text file containing the persona to store for the agent",
            )
            role_group = command_parser.add_mutually_exclusive_group()
            role_group.add_argument("--role", help="Set the agent role")
            role_group.add_argument(
                "--clear-role",
                action="store_true",
                help="Clear the stored agent role",
            )
            model_group = command_parser.add_mutually_exclusive_group()
            model_group.add_argument("--model", help="Set the agent model id or alias")
            model_group.add_argument(
                "--clear-model",
                action="store_true",
                help="Clear the stored agent model id or alias",
            )
            tags_group = command_parser.add_mutually_exclusive_group()
            tags_group.add_argument(
                "--tags",
                help="Comma-separated agent tags to store (for example: research,reviewer)",
            )
            tags_group.add_argument(
                "--clear-tags",
                action="store_true",
                help="Clear all stored agent tags",
            )

    team_parser = top_level.add_parser("team", help="Manage team metadata")
    team_parser.set_defaults(parser=team_parser)

    team_commands = team_parser.add_subparsers(
        dest="team_command",
        metavar="{" + ",".join(TEAM_COMMANDS) + "}",
    )
    for command_name in TEAM_COMMANDS:
        command_parser = team_commands.add_parser(command_name, help=f"{command_name} team")
        command_parser.set_defaults(parser=command_parser)
        if command_name == "show":
            command_parser.epilog = "Examples:\n  maia team show"
        if command_name == "update":
            command_parser.epilog = (
                "Examples:\n"
                "  maia team update --name research-lab --tags research,ops\n"
                "  maia team update --description 'Nightly migration team' --default-agent abcd1234\n"
                "  maia team update --clear-default-agent --clear-tags"
            )
            name_group = command_parser.add_mutually_exclusive_group()
            name_group.add_argument("--name", help="Set the team display name")
            name_group.add_argument(
                "--clear-name",
                action="store_true",
                help="Clear the stored team name",
            )
            description_group = command_parser.add_mutually_exclusive_group()
            description_group.add_argument("--description", help="Set the team description")
            description_group.add_argument(
                "--clear-description",
                action="store_true",
                help="Clear the stored team description",
            )
            tags_group = command_parser.add_mutually_exclusive_group()
            tags_group.add_argument(
                "--tags",
                help="Comma-separated team tags to store (for example: research,ops)",
            )
            tags_group.add_argument(
                "--clear-tags",
                action="store_true",
                help="Clear all stored team tags",
            )
            default_agent_group = command_parser.add_mutually_exclusive_group()
            default_agent_group.add_argument(
                "--default-agent",
                help="Set the default agent id for the team",
            )
            default_agent_group.add_argument(
                "--clear-default-agent",
                action="store_true",
                help="Clear the stored default agent id",
            )

    return parser
