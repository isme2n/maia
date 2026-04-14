"""Command-line interface for Maia."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
import sys
import uuid

from maia.agent_model import AgentRecord, AgentStatus
from maia.app_state import get_registry_path
from maia.storage import JsonRegistryStorage

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
LIFECYCLE_STATUS_BY_COMMAND = {
    "start": AgentStatus.RUNNING,
    "stop": AgentStatus.STOPPED,
    "archive": AgentStatus.ARCHIVED,
    "restore": AgentStatus.STOPPED,
}
AGENT_ID_COMMANDS = frozenset({"status", "tune", *LIFECYCLE_STATUS_BY_COMMAND})
RUNTIME_AGENT_COMMANDS = frozenset(
    {"new", "list", "status", "tune", *LIFECYCLE_STATUS_BY_COMMAND}
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
        if command_name in AGENT_ID_COMMANDS:
            command_parser.add_argument("agent_id", help="Agent id")
        if command_name == "tune":
            command_parser.add_argument(
                "--persona",
                required=True,
                help="Persona text to store for the agent",
            )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    # Preserve the direct ``main([...])`` placeholder contract from task 001
    # while wiring the actual module entrypoint to registry-backed commands.
    if _should_handle_runtime_command(argv, args):
        return _handle_runtime_command(args)

    handler = getattr(args, "handler", None)
    if handler is None:
        args.parser.print_help()
        return 0

    return handler(args)


def _handle_placeholder(args: argparse.Namespace) -> int:
    print(PLACEHOLDER_TEMPLATE.format(args.placeholder_target))
    return 0


def _should_handle_runtime_command(
    argv: Sequence[str] | None, args: argparse.Namespace
) -> bool:
    return (
        argv is None
        and getattr(args, "resource", None) == "agent"
        and getattr(args, "agent_command", None) in RUNTIME_AGENT_COMMANDS
    )


def _handle_runtime_command(args: argparse.Namespace) -> int:
    storage = JsonRegistryStorage()
    registry_path = get_registry_path()

    try:
        registry = storage.load(registry_path)
        if args.agent_command == "new":
            return _handle_agent_new(args, storage, registry_path, registry)
        if args.agent_command == "list":
            return _handle_agent_list(registry)
        if args.agent_command == "status":
            return _handle_agent_status(args, registry)
        if args.agent_command == "tune":
            return _handle_agent_tune(args, storage, registry_path, registry)
        if args.agent_command in LIFECYCLE_STATUS_BY_COMMAND:
            return _handle_agent_lifecycle(args, storage, registry_path, registry)
    except (LookupError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return _handle_placeholder(args)


def _handle_agent_new(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    if any(record.name == args.name for record in registry.list()):
        raise ValueError(f"Agent with name {args.name!r} already exists")

    record = AgentRecord(
        agent_id=uuid.uuid4().hex[:8],
        name=args.name,
        status=AgentStatus.STOPPED,
        persona="",
    )
    registry.add(record)
    storage.save(registry_path, registry)
    print(f"created agent_id={record.agent_id} name={record.name} status={record.status.value}")
    return 0


def _handle_agent_list(registry) -> int:
    for record in registry.list():
        print(_format_record(record))
    return 0


def _handle_agent_status(args: argparse.Namespace, registry) -> int:
    record = registry.get(args.agent_id)
    print(f"{_format_record(record)} persona={record.persona}")
    return 0


def _handle_agent_tune(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    record = registry.get(args.agent_id)
    updated = replace(record, persona=args.persona)
    registry._records[args.agent_id] = updated
    storage.save(registry_path, registry)
    print(f"updated agent_id={updated.agent_id} persona={updated.persona}")
    return 0


def _handle_agent_lifecycle(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    updated = registry.set_status(
        args.agent_id, LIFECYCLE_STATUS_BY_COMMAND[args.agent_command]
    )
    storage.save(registry_path, registry)
    print(f"updated agent_id={updated.agent_id} status={updated.status.value}")
    return 0


def _format_record(record: AgentRecord) -> str:
    return f"agent_id={record.agent_id} name={record.name} status={record.status.value}"
