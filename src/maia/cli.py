"""Command-line interface for Maia."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
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
    "export",
    "import",
    "tune",
    "purge",
)
LIFECYCLE_STATUS_BY_COMMAND = {
    "start": AgentStatus.RUNNING,
    "stop": AgentStatus.STOPPED,
    "archive": AgentStatus.ARCHIVED,
    "restore": AgentStatus.STOPPED,
}
AGENT_ID_COMMANDS = frozenset(
    {"status", "tune", "purge", *LIFECYCLE_STATUS_BY_COMMAND}
)
RUNTIME_AGENT_COMMANDS = frozenset(
    {
        "new",
        "list",
        "status",
        "export",
        "import",
        "tune",
        "purge",
        *LIFECYCLE_STATUS_BY_COMMAND,
    }
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
        if command_name in {"export", "import"}:
            command_parser.add_argument("path", help="Registry JSON path")
        if command_name == "tune":
            persona_group = command_parser.add_mutually_exclusive_group(required=True)
            persona_group.add_argument(
                "--persona",
                help="Persona text to store for the agent",
            )
            persona_group.add_argument(
                "--persona-file",
                help="UTF-8 text file containing the persona to store for the agent",
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
        if args.agent_command == "import":
            return _handle_agent_import(args, storage, registry_path)

        registry = storage.load(registry_path)
        if args.agent_command == "new":
            return _handle_agent_new(args, storage, registry_path, registry)
        if args.agent_command == "list":
            return _handle_agent_list(registry)
        if args.agent_command == "status":
            return _handle_agent_status(args, registry)
        if args.agent_command == "export":
            return _handle_agent_export(args, storage, registry)
        if args.agent_command == "tune":
            return _handle_agent_tune(args, storage, registry_path, registry)
        if args.agent_command == "purge":
            return _handle_agent_purge(args, storage, registry_path, registry)
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


def _handle_agent_export(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry,
) -> int:
    storage.save(args.path, registry)
    print(f"exported registry path={args.path} agents={len(registry.list())}")
    return 0


def _handle_agent_import(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
) -> int:
    import_path = Path(args.path)
    if not import_path.exists():
        raise ValueError(f"Import file {args.path!r} not found")

    registry = storage.load(import_path)
    storage.save(registry_path, registry)
    print(f"imported registry path={args.path} agents={len(registry.list())}")
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
    updated = registry.set_persona(args.agent_id, _resolve_persona(args))
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


def _handle_agent_purge(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    record = registry.get(args.agent_id)
    if record.status is not AgentStatus.ARCHIVED:
        raise ValueError(
            f"Agent with id {args.agent_id!r} is not archived "
            f"(status={record.status.value})"
        )

    registry.remove(args.agent_id)
    storage.save(registry_path, registry)
    print(f"purged agent_id={args.agent_id}")
    return 0


def _format_record(record: AgentRecord) -> str:
    return f"agent_id={record.agent_id} name={record.name} status={record.status.value}"


def _resolve_persona(args: argparse.Namespace) -> str:
    if args.persona is not None:
        return args.persona

    persona_path = Path(args.persona_file)
    try:
        return persona_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Persona file {args.persona_file!r} not found") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Could not decode persona file {args.persona_file!r} as UTF-8"
        ) from exc
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise ValueError(
            f"Could not read persona file {args.persona_file!r}: {detail}"
        ) from exc
