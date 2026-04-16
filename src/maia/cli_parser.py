"""Argument parser construction for Maia CLI."""

from __future__ import annotations

import argparse

from maia.agent_model import AgentStatus
from maia.handoff_model import HandoffKind

TOP_LEVEL_TRANSFER_COMMANDS = ("export", "import", "inspect")
TOP_LEVEL_INFO_COMMANDS = ("doctor", "setup")
TOP_LEVEL_COLLAB_COMMANDS = ("send", "inbox", "thread", "reply")
THREAD_COMMANDS = ("list", "show")
HANDOFF_COMMANDS = ("add", "list", "show")
WORKSPACE_COMMANDS = ("show",)
PART2_CONVERSATION_CONTRACT = (
    "Running agents talk to each other over the broker/message plane.",
    "`send`, `reply`, and `inbox` are useful for diagnostics and controlled operator checks, not the primary product identity.",
    "`thread`, `handoff`, and `workspace` are the public visibility surfaces for open collaboration state.",
)
AGENT_COMMANDS = (
    "new",
    "setup",
    "start",
    "stop",
    "archive",
    "restore",
    "status",
    "logs",
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
AGENT_ID_COMMANDS = frozenset({"setup", "status", "logs", "tune", "purge", *LIFECYCLE_STATUS_BY_COMMAND})
PART1_OPERATOR_FLOW = (
    "maia doctor",
    "maia setup",
    "maia agent new planner",
    "maia agent setup planner",
    "maia agent start planner",
    "maia agent status planner",
    "maia agent logs planner --tail-lines 20",
    "maia agent stop planner",
)
DOCTOR_EXAMPLES = ("maia doctor",)
SETUP_EXAMPLES = ("maia setup",)
AGENT_SETUP_EXAMPLES = ("maia agent setup planner",)
QUICKSTART_EXAMPLES = PART1_OPERATOR_FLOW
RUNTIME_PREREQ_EXAMPLES = ("maia doctor",)
RUNTIME_SUPPORT_BOUNDARY = (
    "Fake-docker tests verify Maia's runtime command flow, not whether Docker, the queue, or the DB work on this host.",
    "Run `maia doctor` before using `agent start|stop|status|logs` for real.",
    "Run `maia setup` to bootstrap shared infra before the first agent run.",
)
V1_RELEASE_CHECKLIST = (
    "Top-level help and README lead with `doctor -> setup -> agent new -> agent setup -> agent start`.",
    "`doctor` stays infra-only: Docker, queue, and DB.",
    "`agent new` stays identity-only in the public story.",
    "`agent setup` is the operator path to open `hermes setup` for one agent.",
)
KNOWN_LIMITATIONS = (
    "Runtime control (agent start|stop|status|logs) requires Docker CLI and a reachable Docker daemon.",
    "Shared infra depends on a reachable queue and DB state path.",
    "`maia setup` bootstraps the shared Maia network, RabbitMQ container, and SQLite state DB.",
    "`maia agent setup` opens an interactive `hermes setup` session only in the CLI; gateway/chat surfaces do not support it.",
    "Messaging and thread commands remain available but are not the primary Part 1 operator flow.",
)
GOLDEN_FLOW_SMOKE_CONTRACT = PART1_OPERATOR_FLOW
HOST_VALIDATION_CHECKLIST = PART1_OPERATOR_FLOW
RUNTIME_RECOVERY_CHECKLIST = (
    "If doctor fails, fix Docker, queue, or DB access first.",
    "If setup fails, finish shared infra bootstrap before retrying agent commands.",
    "If agent setup fails, rerun `maia agent setup <name>`.",
    "If start fails, rerun doctor and confirm shared infra is ready.",
)
HOST_VALIDATION_REPORT_TEMPLATE = (
    "doctor=ok|fail",
    "setup=ok|fail",
    "agent_setup=ok|fail",
    "live_runtime_smoke=ok|fail",
)
EXPORT_EXAMPLES = (
    "maia export",
    "maia export backups/team.maia",
    "maia export backups/team.maia --label prod --description 'Nightly snapshot'",
)
IMPORT_EXAMPLES = (
    "maia import backups/team.maia --preview",
    "maia import backups/team.maia --preview --verbose-preview",
    "maia import backups/team.maia",
    "maia import backups/team.maia --yes",
)
INSPECT_EXAMPLES = (
    "maia inspect backups/team.maia",
    "maia inspect backups/manifest.json",
)
THREAD_EXAMPLES = (
    "maia thread list --status open",
    "maia thread list --agent <reviewer_id>",
    "maia thread show <thread_id>",
    "maia handoff show <handoff_id>",
)
TEAM_SHOW_EXAMPLES = ("maia team show",)
TEAM_UPDATE_EXAMPLES = (
    "maia team update --name research-lab --tags research,ops",
    "maia team update --description 'Nightly migration team' --default-agent <agent_id>",
    "maia team update --clear-description --clear-tags --clear-default-agent",
)
AGENT_TUNE_EXAMPLES = (
    "maia agent tune <planner_id> --role planner --runtime-image ghcr.io/example/planner:latest --runtime-workspace /workspace/planner --runtime-command python --runtime-command=-m --runtime-command planner --runtime-env MAIA_ENV=test --runtime-env MAIA_ROLE=planner",
    "maia agent tune <reviewer_id> --role reviewer --runtime-image ghcr.io/example/reviewer:latest --runtime-workspace /workspace/reviewer --runtime-command python --runtime-command=-m --runtime-command reviewer --runtime-env MAIA_ENV=test --runtime-env MAIA_ROLE=reviewer",
    "maia agent tune <agent_id> --role researcher --model gpt-5 --tags runtime,focus",
    "maia agent tune <agent_id> --clear-role --clear-model --clear-tags",
)
WORKSPACE_EXAMPLES = (
    "maia workspace show <planner_id>",
    "maia agent status <planner_id>",
    "maia agent logs <planner_id> --tail-lines 20",
)
HANDOFF_EXAMPLES = (
    "maia handoff add --thread-id <thread_id> --from-agent <reviewer_id> --to-agent <planner_id> "
    "--type report --location reports/review.md --summary 'Review notes ready'",
    "maia handoff show <handoff_id>",
    "maia workspace show <planner_id>",
    "maia agent status <planner_id>",
    "maia agent logs <planner_id> --tail-lines 20",
    "maia handoff list --thread-id <thread_id>",
)


def _format_epilog(heading: str, lines: tuple[str, ...]) -> str:
    return "\n".join((heading, *(f"  {line}" for line in lines)))


def _format_epilog_sections(*sections: tuple[str, tuple[str, ...]]) -> str:
    return "\n\n".join(_format_epilog(heading, lines) for heading, lines in sections)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maia",
        description="Maia control plane CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(parser=parser)
    parser.epilog = _format_epilog_sections(
        ("Part 1 operator flow:", PART1_OPERATOR_FLOW),
        ("Known limitations:", KNOWN_LIMITATIONS),
        ("Part 2 conversation contract:", PART2_CONVERSATION_CONTRACT),
    )

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
            command_parser.epilog = _format_epilog("Examples:", EXPORT_EXAMPLES)
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
                command_parser.epilog = _format_epilog("Examples:", IMPORT_EXAMPLES)
            if command_name == "inspect":
                command_parser.epilog = _format_epilog("Examples:", INSPECT_EXAMPLES)
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
            "doctor": "Check shared infra readiness (Docker, queue, DB)",
            "setup": "Bootstrap shared Maia infra (Docker, queue, DB)",
        }[command_name]
        description_text = {
            "doctor": "Check shared infra readiness for Docker, queue, and DB access only.",
            "setup": "Bootstrap shared Maia infra only: Docker-backed services, queue, and DB state.",
        }[command_name]
        command_parser = top_level.add_parser(
            command_name,
            help=help_text,
            description=description_text,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command_parser.set_defaults(parser=command_parser)
        if command_name == "doctor":
            command_parser.epilog = _format_epilog("Examples:", DOCTOR_EXAMPLES)
        if command_name == "setup":
            command_parser.epilog = _format_epilog("Examples:", SETUP_EXAMPLES)

    for command_name in TOP_LEVEL_COLLAB_COMMANDS:
        help_text = {
            "send": "Send a collaboration message (diagnostic/operator check)",
            "inbox": "Inspect a live agent inbox (diagnostic/operator check)",
            "thread": "Inspect open collaboration state",
            "reply": "Reply to an existing collaboration message",
        }[command_name]
        parser_kwargs: dict[str, object] = {"help": help_text}
        if command_name == "send":
            parser_kwargs["description"] = (
                "Send a collaboration message as a diagnostic/operator check path, "
                "not as the primary Maia product story."
            )
            parser_kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
        if command_name == "inbox":
            parser_kwargs["description"] = (
                "Inspect a live agent inbox for diagnostics and controlled operator checks."
            )
            parser_kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
        if command_name == "thread":
            parser_kwargs["description"] = (
                "Inspect collaboration threads with recent handoff pointers "
                "and participant runtime summaries."
            )
            parser_kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
        if command_name == "reply":
            parser_kwargs["description"] = (
                "Reply to an existing collaboration message while keeping the public product story centered on running-agent conversation."
            )
            parser_kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
        command_parser = top_level.add_parser(command_name, **parser_kwargs)
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
            command_parser.epilog = _format_epilog("Examples:", THREAD_EXAMPLES)
            thread_commands = command_parser.add_subparsers(
                dest="thread_command",
                metavar="{" + ",".join(THREAD_COMMANDS) + "}",
            )
            list_parser = thread_commands.add_parser("list", help="List collaboration threads")
            list_parser.set_defaults(parser=list_parser)
            list_parser.add_argument(
                "--agent",
                help="Only show threads that include the given participant agent id",
            )
            list_parser.add_argument(
                "--status",
                choices=("open", "closed"),
                help="Only show threads with the given status",
            )
            show_parser = thread_commands.add_parser("show", help="Show a collaboration thread")
            show_parser.set_defaults(parser=show_parser)
            show_parser.add_argument("thread_id", help="Thread id")
            show_parser.add_argument("--limit", type=int, default=50, help="Max messages to show")
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
        command_help = {
            "new": "Create an agent identity",
            "setup": "Open hermes setup for an agent in the CLI",
            "start": "Start an agent runtime",
            "stop": "Stop a running agent runtime",
            "archive": "Archive an agent identity",
            "restore": "Restore an archived agent identity",
            "status": "Show agent runtime status",
            "logs": "Show agent runtime logs",
            "list": "List agent identities",
            "tune": "Update stored agent metadata",
            "purge": "Purge an agent identity and local state",
        }[command_name]
        command_description = {
            "new": "Create an agent identity record.",
            "setup": "Open hermes setup for an agent in the CLI without adding Maia-managed runtime configuration.",
            "start": "Start an agent runtime after shared infra, agent setup, and runtime config are ready.",
            "stop": "Stop a running agent runtime without changing the stored agent identity.",
            "status": "Show the operator-facing agent status plus setup and runtime state.",
            "logs": "Show recent runtime logs for an agent after setup is complete and the runtime has started.",
            "list": "List stored agent identities with their operator-facing launch-readiness state.",
        }.get(command_name)
        command_parser = agent_commands.add_parser(
            command_name,
            help=command_help,
            description=command_description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command_parser.set_defaults(parser=command_parser)
        if command_name == "new":
            command_parser.add_argument("name", help="Agent name")
        if command_name in AGENT_ID_COMMANDS:
            if command_name in {"setup", "start", "stop", "status", "logs"}:
                command_parser.add_argument("agent_id", metavar="name", help="Agent name")
            else:
                command_parser.add_argument("agent_id", help="Agent id")
        if command_name == "setup":
            command_parser.epilog = _format_epilog("Examples:", AGENT_SETUP_EXAMPLES)
        if command_name == "logs":
            command_parser.add_argument(
                "--tail-lines",
                type=int,
                default=100,
                help="Number of recent runtime log lines to show",
            )
        if command_name == "tune":
            command_parser.epilog = _format_epilog("Examples:", AGENT_TUNE_EXAMPLES)
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
            runtime_group = command_parser.add_mutually_exclusive_group()
            runtime_group.add_argument(
                "--clear-runtime",
                action="store_true",
                help="Clear the stored runtime spec",
            )
            command_parser.add_argument(
                "--runtime-image",
                help="Set the runtime image for the agent",
            )
            command_parser.add_argument(
                "--runtime-workspace",
                help="Set the runtime workspace path for the agent",
            )
            command_parser.add_argument(
                "--runtime-command",
                action="append",
                default=None,
                help="Append one runtime command argv item; repeat for multiple items (use --runtime-command=-m for dash-prefixed args)",
            )
            command_parser.add_argument(
                "--runtime-env",
                action="append",
                default=None,
                help="Append one runtime env entry as KEY=VALUE; repeat for multiple entries",
            )

    team_parser = top_level.add_parser("team", help="Manage team metadata")
    team_parser.set_defaults(parser=team_parser)

    team_commands = team_parser.add_subparsers(
        dest="team_command",
        metavar="{" + ",".join(TEAM_COMMANDS) + "}",
    )
    for command_name in TEAM_COMMANDS:
        command_parser = team_commands.add_parser(
            command_name,
            help=f"{command_name} team",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command_parser.set_defaults(parser=command_parser)
        if command_name == "show":
            command_parser.epilog = _format_epilog("Examples:", TEAM_SHOW_EXAMPLES)
        if command_name == "update":
            command_parser.epilog = _format_epilog("Examples:", TEAM_UPDATE_EXAMPLES)
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

    workspace_parser = top_level.add_parser(
        "workspace",
        help="Show stored agent workspace context",
        description=(
            "Show operator-visible workspace context for a handoff participant "
            "from the stored agent runtime spec."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    workspace_parser.set_defaults(parser=workspace_parser)
    workspace_parser.epilog = _format_epilog("Examples:", WORKSPACE_EXAMPLES)
    workspace_commands = workspace_parser.add_subparsers(
        dest="workspace_command",
        metavar="{" + ",".join(WORKSPACE_COMMANDS) + "}",
    )
    show_parser = workspace_commands.add_parser("show", help="Show agent workspace context")
    show_parser.set_defaults(parser=show_parser)
    show_parser.add_argument("agent_id", help="Agent id")

    handoff_parser = top_level.add_parser(
        "handoff",
        help="Manage thread-linked handoff pointers",
        description=(
            "Record and inspect thread-linked handoff pointers stored in "
            "collaboration state, then follow them into workspace/runtime checks."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    handoff_parser.set_defaults(parser=handoff_parser)
    handoff_parser.epilog = _format_epilog("Examples:", HANDOFF_EXAMPLES)

    handoff_commands = handoff_parser.add_subparsers(
        dest="handoff_command",
        metavar="{" + ",".join(HANDOFF_COMMANDS) + "}",
    )
    for command_name in HANDOFF_COMMANDS:
        command_parser = handoff_commands.add_parser(command_name, help=f"{command_name} handoff")
        command_parser.set_defaults(parser=command_parser)
        if command_name == "add":
            command_parser.add_argument("--thread-id", required=True, help="Existing thread id")
            command_parser.add_argument("--from-agent", required=True, help="Sender agent id")
            command_parser.add_argument("--to-agent", required=True, help="Recipient agent id")
            command_parser.add_argument(
                "--type",
                required=True,
                choices=tuple(kind.value for kind in HandoffKind),
                help="Handoff pointer type",
            )
            command_parser.add_argument(
                "--location",
                required=True,
                help="Handoff pointer location (path, url, or repo ref)",
            )
            command_parser.add_argument(
                "--summary",
                required=True,
                help="Short handoff summary",
            )
        if command_name == "list":
            command_parser.add_argument(
                "--thread-id",
                help="Only show handoffs for the given thread id",
            )
        if command_name == "show":
            command_parser.add_argument("handoff_id", help="Handoff id")

    return parser
