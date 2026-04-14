"""Command-line interface for Maia."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

PLACEHOLDER_TEMPLATE = "Not implemented yet: {}"
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="maia", description="Maia control plane CLI.")
    parser.set_defaults(parser=parser)

    top_level = parser.add_subparsers(dest="resource")

    agent_parser = top_level.add_parser("agent", help="Manage agents")
    agent_parser.set_defaults(parser=agent_parser)

    agent_commands = agent_parser.add_subparsers(dest="agent_command")
    for command_name in AGENT_COMMANDS:
        command_parser = agent_commands.add_parser(command_name, help=f"{command_name} agent placeholder")
        command_parser.set_defaults(
            handler=_handle_placeholder,
            placeholder_target=f"agent {command_name}",
        )
        if command_name == "new":
            command_parser.add_argument("name", help="Agent name")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    handler = getattr(args, "handler", None)
    if handler is None:
        args.parser.print_help()
        return 0

    return handler(args)


def _handle_placeholder(args: argparse.Namespace) -> int:
    print(PLACEHOLDER_TEMPLATE.format(args.placeholder_target))
    return 0
