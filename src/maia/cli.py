"""Command-line interface for Maia."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import uuid
from urllib.parse import quote, urlparse

from maia.agent_model import AgentRecord, AgentStatus
from maia.runtime_spec import RuntimeSpec
from maia.app_state import (
    get_collaboration_path,
    get_default_export_path,
    get_registry_path,
    get_runtime_state_path,
    get_team_metadata_path,
)
from maia.backup_manifest import BackupManifest, load_backup_manifest, write_backup_manifest
from maia.bundle_archive import (
    inspect_bundle_archive,
    is_bundle_archive_path,
    write_bundle_archive,
)
from maia.broker import BrokerMessageEnvelope, MessageBroker
from maia.cli_parser import (
    LIFECYCLE_STATUS_BY_COMMAND,
    TOP_LEVEL_COLLAB_COMMANDS,
    build_parser,
)
from maia.collaboration_storage import CollaborationStorage
from maia.docker_runtime_adapter import DockerRuntimeAdapter
from maia.handoff_model import HandoffKind, HandoffRecord
from maia.message_model import MessageKind, MessageRecord, ThreadRecord
from maia.rabbitmq_broker import RabbitMQBroker
from maia.runtime_adapter import RuntimeLogsRequest, RuntimeStatusRequest, RuntimeStopRequest, RuntimeStartRequest, RuntimeState, RuntimeStatus
from maia.runtime_state_storage import RuntimeStateStorage
from maia.storage import JsonRegistryStorage
from maia.team_metadata import TeamMetadata, load_team_metadata, save_team_metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(_normalize_legacy_thread_argv(argv_list))
    if _get_runtime_command_name(args) is None:
        args.parser.print_help()
        return 0
    return _handle_runtime_command(args)


def _normalize_legacy_thread_argv(argv: list[str]) -> list[str]:
    if len(argv) < 2 or argv[0] != "thread":
        return argv
    if argv[1] in {"list", "show", "-h", "--help"} or argv[1].startswith("-"):
        return argv
    return ["thread", "show", *argv[1:]]


def _handle_runtime_command(args: argparse.Namespace) -> int:
    storage = JsonRegistryStorage()
    collaboration_storage = CollaborationStorage()
    registry_path = get_registry_path()
    collaboration_path = get_collaboration_path()
    team_metadata_path = get_team_metadata_path()
    resource = getattr(args, "resource", None)

    try:
        command_name = _get_runtime_command_name(args)
        if resource == "doctor":
            return _handle_doctor()
        if resource == "import":
            return _handle_transfer_import(args, storage, registry_path)
        if resource == "export":
            registry = storage.load(registry_path)
            return _handle_transfer_export(args, storage, registry)
        if resource == "inspect":
            return _handle_transfer_inspect(args, storage)
        if resource == "team" and command_name == "show":
            return _handle_team_show(team_metadata_path)
        if resource == "team" and command_name == "update":
            registry = storage.load(registry_path)
            return _handle_team_update(args, registry, team_metadata_path)
        if resource == "artifact":
            registry = storage.load(registry_path)
            collaboration = collaboration_storage.load(collaboration_path)
            if command_name == "add":
                return _handle_artifact_add(
                    args,
                    registry,
                    collaboration_storage,
                    collaboration_path,
                    collaboration,
                )
            if command_name == "list":
                return _handle_artifact_list(args, collaboration)
            if command_name == "show":
                return _handle_artifact_show(args, collaboration)
        if resource in TOP_LEVEL_COLLAB_COMMANDS:
            registry = storage.load(registry_path)
            collaboration = collaboration_storage.load(collaboration_path)
            message_broker = _build_message_broker()
            try:
                if command_name == "send":
                    return _handle_send(
                        args,
                        registry,
                        collaboration_storage,
                        collaboration_path,
                        collaboration,
                        message_broker,
                    )
                if command_name == "inbox":
                    return _handle_inbox(
                        args,
                        registry,
                        collaboration_storage,
                        collaboration_path,
                        collaboration,
                        message_broker,
                    )
                if command_name == "thread":
                    return _handle_thread(args, collaboration)
                if command_name == "reply":
                    return _handle_reply(
                        args,
                        registry,
                        collaboration_storage,
                        collaboration_path,
                        collaboration,
                        message_broker,
                    )
            finally:
                if message_broker is not None:
                    message_broker.close()

        registry = storage.load(registry_path)
        runtime_adapter = _build_runtime_adapter()
        if command_name == "new":
            return _handle_agent_new(args, storage, registry_path, registry)
        if command_name == "list":
            return _handle_agent_list(registry)
        if command_name == "status":
            return _handle_agent_status(args, storage, registry_path, registry, runtime_adapter)
        if command_name == "logs":
            return _handle_agent_logs(args, storage, registry_path, registry, runtime_adapter)
        if command_name == "start":
            return _handle_agent_start(args, storage, registry_path, registry, runtime_adapter)
        if command_name == "stop":
            return _handle_agent_stop(args, storage, registry_path, registry, runtime_adapter)
        if command_name == "tune":
            return _handle_agent_tune(args, storage, registry_path, registry)
        if command_name == "purge":
            return _handle_agent_purge(args, storage, registry_path, registry)
        if command_name in {"archive", "restore"}:
            return _handle_agent_lifecycle(args, storage, registry_path, registry)
    except (LookupError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    raise ValueError(f"Unsupported command: {command_name}")


def _handle_doctor() -> int:
    checks = _collect_doctor_checks()
    failed_checks = [check["name"] for check in checks if _is_doctor_failure(check)]
    for check in checks:
        print(
            f"doctor check={check['name']} status={check['status']} "
            f"detail={_format_preview_value(check['detail'])} "
            f"remediation={_format_preview_value(check['remediation'])}"
        )
    print(
        f"doctor kind=summary status={'ok' if not failed_checks else 'fail'} "
        f"failed={','.join(failed_checks) if failed_checks else '-'} "
        f"next_step={_format_preview_value(_doctor_next_step(failed_checks))}"
    )
    return 0 if not failed_checks else 1


def _is_doctor_failure(check: dict[str, str]) -> bool:
    if check["name"] == "broker_url" and check["status"] == "missing":
        return False
    return check["status"] != "ok"


def _doctor_next_step(failed_checks: list[str]) -> str:
    if not failed_checks:
        return "runtime prerequisites satisfied"
    if "docker_cli" in failed_checks:
        return "install docker then rerun maia doctor"
    if "docker_compose" in failed_checks:
        return "install docker compose plugin then rerun maia doctor"
    if "docker_daemon" in failed_checks:
        return "start docker daemon then rerun maia doctor"
    if "broker_url" in failed_checks:
        return "set MAIA_BROKER_URL then rerun maia doctor"
    if "broker_tcp" in failed_checks:
        return "start or expose the broker service then rerun maia doctor"
    return "fix reported doctor failures then rerun maia doctor"


def _collect_doctor_checks() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        checks.extend(
            [
                {
                    "name": "docker_cli",
                    "status": "missing",
                    "detail": "docker binary not found in PATH",
                    "remediation": "install docker cli or docker engine on this host",
                },
                {
                    "name": "docker_compose",
                    "status": "missing",
                    "detail": "docker compose unavailable because docker CLI is missing",
                    "remediation": "install docker first, then verify docker compose plugin",
                },
                {
                    "name": "docker_daemon",
                    "status": "missing",
                    "detail": "docker daemon unreachable because docker CLI is missing",
                    "remediation": "install docker engine and start the docker daemon",
                },
            ]
        )
    else:
        checks.extend(
            [
                _run_doctor_probe(
                    "docker_cli",
                    [docker_bin, "--version"],
                    success_detail=docker_bin,
                    success_remediation="no action needed",
                    failure_remediation="verify the docker binary is executable on PATH",
                ),
                _run_doctor_probe(
                    "docker_compose",
                    [docker_bin, "compose", "version"],
                    success_detail="docker compose available",
                    success_remediation="no action needed",
                    failure_remediation="install or enable the docker compose plugin",
                ),
                _run_doctor_probe(
                    "docker_daemon",
                    [docker_bin, "info"],
                    success_detail="docker daemon reachable",
                    success_remediation="no action needed",
                    failure_remediation="start the docker daemon or fix daemon access permissions",
                ),
            ]
        )

    checks.extend(_collect_broker_doctor_checks())
    return checks


def _collect_broker_doctor_checks() -> list[dict[str, str]]:
    broker_url = os.environ.get("MAIA_BROKER_URL", "").strip()
    if not broker_url:
        return [
            {
                "name": "broker_url",
                "status": "missing",
                "detail": "MAIA_BROKER_URL is not set",
                "remediation": "optional: set MAIA_BROKER_URL to enable broker readiness checks",
            }
        ]

    parsed = urlparse(broker_url)
    try:
        port = parsed.port
    except ValueError:
        return [
            {
                "name": "broker_url",
                "status": "fail",
                "detail": "MAIA_BROKER_URL must include a valid numeric port",
                "remediation": "set MAIA_BROKER_URL to a full amqp URL like amqp://user:pass@host:5672/vhost",
            }
        ]
    if not parsed.hostname:
        return [
            {
                "name": "broker_url",
                "status": "fail",
                "detail": "MAIA_BROKER_URL must include a hostname",
                "remediation": "set MAIA_BROKER_URL to a full amqp URL like amqp://user:pass@host:5672/vhost",
            }
        ]
    if port is None:
        port = 5671 if parsed.scheme == "amqps" else 5672

    redacted_broker_url = _redact_broker_url(broker_url)

    try:
        with socket.create_connection((parsed.hostname, port), timeout=2):
            pass
    except OSError as exc:
        detail = exc.strerror or str(exc)
        return [
            {
                "name": "broker_url",
                "status": "ok",
                "detail": redacted_broker_url,
                "remediation": "no action needed",
            },
            {
                "name": "broker_tcp",
                "status": "fail",
                "detail": detail,
                "remediation": "start the broker service or expose the configured host:port",
            },
        ]

    return [
        {
            "name": "broker_url",
            "status": "ok",
            "detail": redacted_broker_url,
            "remediation": "no action needed",
        },
        {
            "name": "broker_tcp",
            "status": "ok",
            "detail": f"tcp reachability confirmed for {parsed.hostname}:{port}",
            "remediation": "no action needed",
        },
    ]


def _run_doctor_probe(
    name: str,
    command: list[str],
    *,
    success_detail: str,
    success_remediation: str,
    failure_remediation: str,
) -> dict[str, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        detail = exc.strerror or str(exc)
        return {
            "name": name,
            "status": "missing",
            "detail": detail,
            "remediation": failure_remediation,
        }

    if result.returncode == 0:
        return {
            "name": name,
            "status": "ok",
            "detail": success_detail,
            "remediation": success_remediation,
        }

    detail = (result.stderr or result.stdout or "probe failed").strip()
    return {
        "name": name,
        "status": "fail",
        "detail": detail,
        "remediation": failure_remediation,
    }


def _build_message_broker() -> MessageBroker | None:
    broker_url = os.environ.get("MAIA_BROKER_URL", "").strip()
    if not broker_url:
        return None
    return RabbitMQBroker(broker_url=broker_url)


def _redact_broker_url(broker_url: str) -> str:
    parsed = urlparse(broker_url)
    if not parsed.scheme or not parsed.hostname:
        return broker_url
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username is not None:
        netloc = f"{parsed.username}:***@{netloc}"
    return parsed._replace(netloc=netloc).geturl()


def _build_runtime_adapter() -> DockerRuntimeAdapter:
    return DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=get_runtime_state_path(),
    )


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
        role="",
        model="",
        tags=[],
    )
    registry.add(record)
    storage.save(registry_path, registry)
    print(f"created agent_id={record.agent_id} name={_format_preview_value(record.name)} status={record.status.value}")
    return 0


def _handle_agent_list(registry) -> int:
    for record in registry.list():
        print(_format_record(record))
    return 0


def _handle_send(
    args,
    registry,
    collaboration_storage,
    collaboration_path: Path,
    collaboration,
    message_broker: MessageBroker | None,
) -> int:
    registry.get(args.from_agent)
    registry.get(args.to_agent)
    kind = MessageKind(args.kind)
    threads = list(collaboration.threads)
    messages = list(collaboration.messages)
    now = _timestamp_now()

    if args.thread_id is None:
        thread = ThreadRecord(
            thread_id=_new_id(),
            topic=args.topic,
            participants=[args.from_agent, args.to_agent],
            created_by=args.from_agent,
            status="open",
            created_at=now,
            updated_at=now,
        )
        threads.append(thread)
    else:
        thread = _require_thread(collaboration, args.thread_id)
        participants = list(thread.participants)
        if args.from_agent not in participants:
            participants.append(args.from_agent)
        if args.to_agent not in participants:
            participants.append(args.to_agent)
        thread = ThreadRecord(
            thread_id=thread.thread_id,
            topic=thread.topic,
            participants=participants,
            created_by=thread.created_by,
            status=thread.status,
            created_at=thread.created_at,
            updated_at=now,
        )
        _replace_thread(threads, thread)

    message = MessageRecord(
        message_id=_new_id(),
        thread_id=thread.thread_id,
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        kind=kind,
        body=args.body,
        created_at=now,
    )
    messages.append(message)
    if message_broker is not None:
        if isinstance(message_broker, RabbitMQBroker):
            message_broker.publish_with_metadata(message, thread_topic=thread.topic)
        else:
            message_broker.publish(message)
    collaboration_storage.save(
        collaboration_path,
        threads=threads,
        messages=messages,
    )
    print(
        f"sent thread_id={thread.thread_id} message_id={message.message_id} "
        f"from_agent={message.from_agent} to_agent={message.to_agent} kind={message.kind.value}"
    )
    return 0


def _handle_inbox(
    args,
    registry,
    collaboration_storage,
    collaboration_path: Path,
    collaboration,
    message_broker: MessageBroker | None,
) -> int:
    registry.get(args.agent_id)
    limit = _validate_positive_limit(args.limit, field_name="Inbox limit")
    if message_broker is not None:
        if isinstance(message_broker, RabbitMQBroker):
            pulled_messages = message_broker.pull_with_metadata(agent_id=args.agent_id, limit=limit)
            collaboration = _merge_broker_inbox_messages(
                collaboration_storage,
                collaboration_path,
                collaboration,
                pulled_messages,
            )
            if pulled_messages:
                print(
                    f"inbox agent_id={args.agent_id} messages={len(pulled_messages)} "
                    "source=broker ack=after-print"
                )
                for envelope, _metadata in pulled_messages:
                    print(_format_envelope_line(envelope))
                _ack_broker_messages(
                    message_broker,
                    [envelope for envelope, _metadata in pulled_messages],
                    agent_id=args.agent_id,
                )
                return 0
            print(
                f"inbox agent_id={args.agent_id} messages=0 "
                "source=broker ack=complete"
            )
            return 0
        pull_result = message_broker.pull(agent_id=args.agent_id, limit=limit)
        collaboration = _merge_broker_inbox_messages(
            collaboration_storage,
            collaboration_path,
            collaboration,
            [(envelope, {}) for envelope in pull_result.messages],
        )
        inbox_messages = [envelope.message for envelope in pull_result.messages]
        if inbox_messages:
            print(
                f"inbox agent_id={args.agent_id} messages={len(inbox_messages)} "
                "source=broker ack=after-print"
            )
            for envelope in pull_result.messages:
                print(_format_envelope_line(envelope))
            _ack_broker_messages(
                message_broker,
                pull_result.messages,
                agent_id=args.agent_id,
            )
            return 0
        print(
            f"inbox agent_id={args.agent_id} messages=0 "
            "source=broker ack=complete"
        )
        return 0
    inbox_messages = [
        message for message in collaboration.messages if message.to_agent == args.agent_id
    ]
    inbox_messages = list(reversed(inbox_messages))[:limit]
    print(f"inbox agent_id={args.agent_id} messages={len(inbox_messages)}")
    for message in inbox_messages:
        print(_format_message_line(message))
    return 0


def _handle_thread(args, collaboration) -> int:
    if args.thread_command == "list":
        return _handle_thread_list(args, collaboration)
    if args.thread_command == "show":
        return _handle_thread_show(args, collaboration)
    raise ValueError(f"Unsupported thread command: {args.thread_command!r}")


def _handle_thread_list(args, collaboration) -> int:
    messages_by_thread = _group_messages_by_thread(collaboration.messages)
    handoffs_by_thread = _group_handoffs_by_thread(collaboration.handoffs)
    runtime_states = _load_thread_runtime_states()
    threads = sorted(
        collaboration.threads,
        key=lambda thread: (thread.updated_at, thread.thread_id),
        reverse=True,
    )
    if args.agent is not None:
        threads = [thread for thread in threads if args.agent in thread.participants]
    if args.status is not None:
        threads = [thread for thread in threads if thread.status == args.status]
    for thread in threads:
        overview = _format_thread_overview_fields(
            thread,
            messages_by_thread.get(thread.thread_id, []),
            handoffs_by_thread.get(thread.thread_id, []),
            runtime_states,
        )
        print(f"thread {overview}")
    return 0


def _handle_thread_show(args, collaboration) -> int:
    limit = _validate_positive_limit(args.limit, field_name="Thread limit")
    thread = _require_thread(collaboration, args.thread_id)
    thread_messages = _sorted_thread_messages(
        message for message in collaboration.messages if message.thread_id == thread.thread_id
    )
    thread_handoffs = [
        handoff for handoff in collaboration.handoffs if handoff.thread_id == thread.thread_id
    ]
    runtime_states = _load_thread_runtime_states()
    print(
        f"thread {_format_thread_overview_fields(thread, thread_messages, thread_handoffs, runtime_states)} "
        f"created_by={thread.created_by} created_at={thread.created_at}"
    )
    for message in thread_messages[:limit]:
        print(_format_message_line(message))
    return 0


def _handle_artifact_add(
    args,
    registry,
    collaboration_storage,
    collaboration_path: Path,
    collaboration,
) -> int:
    thread = _require_thread(collaboration, args.thread_id)
    registry.get(args.from_agent)
    registry.get(args.to_agent)
    _require_thread_participant(
        thread,
        args.from_agent,
        error="Artifact sender must be a participant in the thread",
    )
    _require_thread_participant(
        thread,
        args.to_agent,
        error="Artifact recipient must be a participant in the thread",
    )

    artifact = HandoffRecord(
        handoff_id=_new_id(),
        thread_id=thread.thread_id,
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        kind=HandoffKind(args.type),
        location=args.location,
        summary=args.summary,
        created_at=_timestamp_now(),
    )
    collaboration_storage.save(
        collaboration_path,
        threads=list(collaboration.threads),
        messages=list(collaboration.messages),
        handoffs=[*collaboration.handoffs, artifact],
    )
    print(f"added {_format_handoff_line(artifact)}")
    return 0


def _handle_artifact_list(args, collaboration) -> int:
    if args.thread_id is not None:
        _require_thread(collaboration, args.thread_id)
        handoffs = [
            handoff for handoff in collaboration.handoffs if handoff.thread_id == args.thread_id
        ]
    else:
        handoffs = list(collaboration.handoffs)

    for handoff in handoffs:
        print(_format_handoff_line(handoff))
    return 0


def _handle_artifact_show(args, collaboration) -> int:
    print(_format_handoff_line(_require_handoff(collaboration, args.artifact_id)))
    return 0


def _handle_reply(
    args,
    registry,
    collaboration_storage,
    collaboration_path: Path,
    collaboration,
    message_broker: MessageBroker | None,
) -> int:
    registry.get(args.from_agent)
    source_message = _require_message(collaboration, args.message_id)
    registry.get(source_message.from_agent)
    thread = _require_thread(collaboration, source_message.thread_id)
    if args.from_agent != source_message.to_agent:
        raise ValueError(
            "Reply sender must match the original message recipient"
        )
    if args.from_agent not in thread.participants:
        raise ValueError("Reply sender must be a participant in the thread")

    now = _timestamp_now()
    threads = list(collaboration.threads)
    messages = list(collaboration.messages)
    thread = ThreadRecord(
        thread_id=thread.thread_id,
        topic=thread.topic,
        participants=list(thread.participants),
        created_by=thread.created_by,
        status=thread.status,
        created_at=thread.created_at,
        updated_at=now,
    )
    _replace_thread(threads, thread)
    message = MessageRecord(
        message_id=_new_id(),
        thread_id=thread.thread_id,
        from_agent=args.from_agent,
        to_agent=source_message.from_agent,
        kind=MessageKind(args.kind),
        body=args.body,
        created_at=now,
        reply_to_message_id=source_message.message_id,
    )
    messages.append(message)
    if message_broker is not None:
        if isinstance(message_broker, RabbitMQBroker):
            message_broker.publish_with_metadata(message, thread_topic=thread.topic)
        else:
            message_broker.publish(message)
    collaboration_storage.save(
        collaboration_path,
        threads=threads,
        messages=messages,
    )
    print(
        f"replied thread_id={thread.thread_id} message_id={message.message_id} "
        f"reply_to_message_id={source_message.message_id} from_agent={message.from_agent} "
        f"to_agent={message.to_agent} kind={message.kind.value}"
    )
    return 0


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _timestamp_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_positive_limit(value: int, *, field_name: str) -> int:
    if value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def _message_sort_key(message: MessageRecord) -> tuple[str, str]:
    return (message.created_at, message.message_id)


def _sorted_thread_messages(messages: Sequence[MessageRecord]) -> list[MessageRecord]:
    return sorted(messages, key=_message_sort_key)


def _group_messages_by_thread(messages: Sequence[MessageRecord]) -> dict[str, list[MessageRecord]]:
    grouped: dict[str, list[MessageRecord]] = {}
    for message in messages:
        grouped.setdefault(message.thread_id, []).append(message)
    return grouped


def _group_handoffs_by_thread(handoffs: Sequence[HandoffRecord]) -> dict[str, list[HandoffRecord]]:
    grouped: dict[str, list[HandoffRecord]] = {}
    for handoff in handoffs:
        grouped.setdefault(handoff.thread_id, []).append(handoff)
    return grouped


def _derive_thread_pending_on(thread_messages: Sequence[MessageRecord]) -> str:
    if not thread_messages:
        return "-"
    return max(thread_messages, key=_message_sort_key).to_agent


def _resolve_thread_participant_runtime_status(
    agent_id: str,
    runtime_states: dict[str, RuntimeState],
) -> str:
    runtime_state = runtime_states.get(agent_id)
    if runtime_state is None:
        return RuntimeStatus.STOPPED.value
    return runtime_state.runtime_status.value


def _load_thread_runtime_states() -> dict[str, RuntimeState]:
    try:
        return RuntimeStateStorage().load(get_runtime_state_path())
    except ValueError:
        return {}


def _format_thread_participant_runtime(
    participants: Sequence[str],
    runtime_states: dict[str, RuntimeState],
) -> str:
    return _format_encoded_list_or_dash(
        [
            f"{quote(participant, safe='')}:{_resolve_thread_participant_runtime_status(participant, runtime_states)}"
            for participant in participants
        ]
    )


def _format_thread_overview_fields(
    thread: ThreadRecord,
    thread_messages: Sequence[MessageRecord],
    thread_handoffs: Sequence[HandoffRecord],
    runtime_states: dict[str, RuntimeState],
) -> str:
    return (
        f"thread_id={thread.thread_id} "
        f"topic={_format_preview_value(thread.topic)} "
        f"participants={_format_encoded_list_or_dash(thread.participants)} "
        f"participant_runtime={_format_thread_participant_runtime(thread.participants, runtime_states)} "
        f"status={thread.status} updated_at={thread.updated_at} "
        f"pending_on={_format_preview_value(_derive_thread_pending_on(thread_messages))} "
        f"artifacts={len(thread_handoffs)} messages={len(thread_messages)}"
    )


def _require_thread(collaboration, thread_id: str) -> ThreadRecord:
    for thread in collaboration.threads:
        if thread.thread_id == thread_id:
            return thread
    raise LookupError(f"Thread with id {thread_id!r} not found")


def _require_thread_participant(thread: ThreadRecord, agent_id: str, *, error: str) -> None:
    if agent_id not in thread.participants:
        raise ValueError(error)


def _require_message(collaboration, message_id: str) -> MessageRecord:
    for message in collaboration.messages:
        if message.message_id == message_id:
            return message
    raise LookupError(f"Message with id {message_id!r} not found")


def _require_handoff(collaboration, handoff_id: str) -> HandoffRecord:
    for handoff in collaboration.handoffs:
        if handoff.handoff_id == handoff_id:
            return handoff
    raise LookupError(f"Artifact with id {handoff_id!r} not found")


def _replace_thread(threads: list[ThreadRecord], updated: ThreadRecord) -> None:
    for index, thread in enumerate(threads):
        if thread.thread_id == updated.thread_id:
            threads[index] = updated
            return
    raise LookupError(f"Thread with id {updated.thread_id!r} not found")


def _merge_broker_inbox_messages(
    collaboration_storage,
    collaboration_path: Path,
    collaboration,
    envelopes: list[tuple[BrokerMessageEnvelope, dict[str, str]]],
):
    if not envelopes:
        return collaboration
    threads = list(collaboration.threads)
    messages = list(collaboration.messages)
    known_message_ids = {message.message_id for message in messages}
    changed = False
    for envelope, metadata in envelopes:
        message = envelope.message
        thread_topic = metadata.get("thread_topic", "")
        existing_thread = next(
            (thread for thread in threads if thread.thread_id == message.thread_id),
            None,
        )
        if existing_thread is None:
            threads.append(
                ThreadRecord(
                    thread_id=message.thread_id,
                    topic=thread_topic,
                    participants=[message.from_agent, message.to_agent],
                    created_by=message.from_agent,
                    status="open",
                    created_at=message.created_at,
                    updated_at=message.created_at,
                )
            )
            changed = True
        else:
            participants = list(existing_thread.participants)
            if message.from_agent not in participants:
                participants.append(message.from_agent)
            if message.to_agent not in participants:
                participants.append(message.to_agent)
            next_topic = existing_thread.topic or thread_topic
            if (
                participants != existing_thread.participants
                or message.created_at > existing_thread.updated_at
                or next_topic != existing_thread.topic
            ):
                _replace_thread(
                    threads,
                    ThreadRecord(
                        thread_id=existing_thread.thread_id,
                        topic=next_topic,
                        participants=participants,
                        created_by=existing_thread.created_by,
                        status=existing_thread.status,
                        created_at=existing_thread.created_at,
                        updated_at=max(existing_thread.updated_at, message.created_at),
                    ),
                )
                changed = True
        if message.message_id not in known_message_ids:
            messages.append(message)
            known_message_ids.add(message.message_id)
            changed = True
    if changed:
        collaboration_storage.save(
            collaboration_path,
            threads=threads,
            messages=messages,
        )
        return collaboration_storage.load(collaboration_path)
    return collaboration


def _format_envelope_line(envelope: BrokerMessageEnvelope) -> str:
    return (
        _format_message_line(envelope.message)
        + f" receipt_handle={envelope.receipt_handle}"
        + f" delivery_attempt={envelope.delivery_attempt}"
    )


def _ack_broker_messages(
    message_broker: MessageBroker,
    envelopes: list[BrokerMessageEnvelope],
    *,
    agent_id: str,
) -> None:
    for envelope in envelopes:
        try:
            message_broker.ack(envelope)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"Broker inbox ack failed for agent {agent_id!r}: {exc}"
            ) from exc


def _format_message_line(message: MessageRecord) -> str:
    reply_to = (
        _format_preview_value(message.reply_to_message_id)
        if message.reply_to_message_id is not None
        else "-"
    )
    return (
        f"message_id={message.message_id} thread_id={message.thread_id} "
        f"from_agent={message.from_agent} to_agent={message.to_agent} "
        f"kind={message.kind.value} body={_format_preview_value(message.body)} "
        f"created_at={message.created_at} reply_to_message_id={reply_to}"
    )


def _format_handoff_line(handoff: HandoffRecord) -> str:
    return (
        f"artifact_id={handoff.handoff_id} thread_id={handoff.thread_id} "
        f"from_agent={handoff.from_agent} to_agent={handoff.to_agent} "
        f"type={handoff.kind.value} location={_format_preview_value(handoff.location)} "
        f"summary={_format_preview_value(handoff.summary)} created_at={handoff.created_at}"
    )


def _handle_transfer_export(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry,
) -> int:
    export_path = Path(args.path) if args.path is not None else get_default_export_path()
    label = _normalize_export_metadata_value(args.label, field_name="label")
    description = _normalize_export_metadata_value(
        args.description,
        field_name="description",
    )
    team_metadata = _sanitize_team_metadata_for_registry(
        load_team_metadata(get_team_metadata_path()),
        registry,
    )
    if export_path.exists() and export_path.is_dir():
        raise ValueError(f"Export path {str(export_path)!r} is a directory")
    if is_bundle_archive_path(export_path):
        write_bundle_archive(
            export_path,
            storage,
            registry,
            label=label,
            description=description,
            source_registry_path=get_registry_path(),
            team_metadata=team_metadata,
        )
        print(
            f"exported path={_format_preview_value(str(export_path))} "
            f"format=maia-bundle agents={len(registry.list())}"
        )
        return 0
    if export_path.name == "manifest.json":
        raise ValueError(
            f"Export path {str(export_path)!r} is reserved for the backup manifest"
        )
    storage.save(export_path, registry, portable=True)
    manifest_path = write_backup_manifest(
        export_path,
        agent_count=len(registry.list()),
        label=label or export_path.stem,
        description=description,
        source_registry_path=get_registry_path(),
        team_metadata=team_metadata,
    )
    print(
        f"exported registry path={_format_preview_value(str(export_path))} "
        f"manifest={_format_preview_value(str(manifest_path))} agents={len(registry.list())}"
    )
    return 0


def _handle_transfer_import(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
) -> int:
    current_registry = storage.load(registry_path)
    current_team_metadata = load_team_metadata(get_team_metadata_path())
    incoming_registry, incoming_team_metadata, source_path, import_path = _load_registry_for_transfer(
        args.path, storage
    )
    effective_incoming_team_metadata = (
        _sanitize_team_metadata_for_registry(current_team_metadata, incoming_registry)
        if incoming_team_metadata is None
        else incoming_team_metadata
    )
    preview = _build_import_preview(
        current_registry,
        incoming_registry,
        current_team_metadata=current_team_metadata,
        incoming_team_metadata=effective_incoming_team_metadata,
        verbose=args.verbose_preview,
    )
    if args.preview:
        _print_import_preview(preview, source_path, import_path)
        return 0

    _print_import_preview(preview, source_path, import_path)
    if preview["current_agents"] > 0 or preview["team_details"] != "-":
        print("warning import will overwrite the current Maia registry with the snapshot state")
        print("warning removed agents and changed fields will be replaced by snapshot values")
        if not args.yes:
            if not _confirm_import_overwrite():
                print("cancelled import")
                return 1
    storage.save(registry_path, incoming_registry)
    RuntimeStateStorage().prune(
        get_runtime_state_path(),
        {record.agent_id for record in incoming_registry.list()},
    )
    if effective_incoming_team_metadata != current_team_metadata:
        save_team_metadata(get_team_metadata_path(), effective_incoming_team_metadata)
    print(
        f"imported source={_format_preview_value(str(source_path))} "
        f"registry={_format_preview_value(str(import_path))} "
        f"agents={len(incoming_registry.list())}"
    )
    return 0


def _print_import_preview(preview: dict[str, object], source_path: Path, import_path: Path) -> None:
    print(
        "preview "
        f"source={_format_preview_value(str(source_path))} "
        f"registry={_format_preview_value(str(import_path))} "
        f"current_agents={preview['current_agents']} "
        f"incoming_agents={preview['incoming_agents']} "
        f"added={preview['added_count']} "
        f"removed={preview['removed_count']} "
        f"changed={preview['changed_count']} "
        f"unchanged={preview['unchanged_count']}"
    )
    print(
        "risk "
        f"level={preview['risk_level']} "
        f"reasons={preview['risk_reasons']}"
    )
    print(
        "added "
        f"ids={preview['added_ids']} "
        f"names={preview['added_names']}"
    )
    print(
        "removed "
        f"ids={preview['removed_ids']} "
        f"names={preview['removed_names']}"
    )
    print(
        "changed "
        f"ids={preview['changed_ids']} "
        f"names={preview['changed_names']} "
        f"details={preview['change_details']}"
    )
    print(f"team details={preview['team_details']}")


def _handle_transfer_inspect(args: argparse.Namespace, storage: JsonRegistryStorage) -> int:
    inspection = _inspect_transfer_source(args.path, storage)
    print(
        "inspected "
        f"path={_format_preview_value(str(inspection['path']))} "
        f"format={inspection['format']} "
        f"registry={_format_preview_value(str(inspection['registry']))} "
        f"agents={inspection['agents']}"
    )
    if inspection["manifest"] is not None:
        manifest = inspection["manifest"]
        print(
            "manifest "
            f"kind={manifest.kind} "
            f"version={manifest.version} "
            f"scope_version={manifest.scope_version} "
            f"created_at={manifest.created_at}"
        )
        print(
            "bundle "
            f"label={_format_preview_value(manifest.label)} "
            f"created_by={_format_preview_value(manifest.created_by)} "
            f"maia_version={_format_preview_value(manifest.maia_version)}"
        )
        print(
            "provenance "
            f"source_host={_format_preview_value(manifest.source_host)} "
            f"source_platform={_format_preview_value(manifest.source_platform)} "
            f"source_registry={_format_preview_value(manifest.source_registry_path)}"
        )
        print(f"description value={_format_preview_value(manifest.description)}")
        print(
            "portable "
            f"paths={','.join(manifest.portable_paths)} "
            f"state_kinds={','.join(manifest.portable_state_kinds)}"
        )
        print(
            "runtime "
            f"paths={','.join(manifest.runtime_only_paths)} "
            f"state_kinds={','.join(manifest.runtime_only_state_kinds)}"
        )
        if manifest.scope_version >= 2:
            print(
                "team "
                f"name={_format_preview_value(manifest.team_name)} "
                f"description={_format_preview_value(manifest.team_description)} "
                f"tags={_format_encoded_list_or_dash(manifest.team_tags)} "
                f"default_agent_id={_format_preview_value(manifest.default_agent_id)}"
            )
    print(
        "agents "
        f"names={inspection['agent_names']} "
        f"statuses={inspection['status_counts']}"
    )
    print(f"profiles entries={inspection['agent_profiles']}")
    return 0


def _inspect_transfer_source(source: str, storage: JsonRegistryStorage) -> dict[str, object]:
    source_path = Path(source)
    if not source_path.exists():
        raise ValueError(f"Inspect file {source!r} not found")
    if source_path.is_dir():
        raise ValueError(f"Inspect file {source!r} is a directory")
    if is_bundle_archive_path(source_path):
        manifest, registry, bundle_path, registry_path = inspect_bundle_archive(source_path, storage)
        _validate_import_team_metadata(_team_metadata_from_manifest(manifest), registry)
        return _build_inspection_result(
            path=bundle_path,
            format_name="maia-bundle",
            manifest=manifest,
            registry=registry,
            registry_path=registry_path,
        )
    if source_path.name == "manifest.json":
        manifest = load_backup_manifest(source_path)
        registry_path = _resolve_import_registry_path(source_path)
        registry = storage.load(registry_path)
        _validate_import_team_metadata(_team_metadata_from_manifest(manifest), registry)
        return _build_inspection_result(
            path=source_path,
            format_name="manifest-json",
            manifest=manifest,
            registry=registry,
            registry_path=registry_path,
        )

    registry = storage.load(source_path)
    manifest = _maybe_load_adjacent_manifest(source_path)
    _validate_import_team_metadata(_team_metadata_from_manifest(manifest), registry)
    return _build_inspection_result(
        path=source_path,
        format_name="registry-json",
        manifest=manifest,
        registry=registry,
        registry_path=source_path,
    )


def _build_inspection_result(
    *,
    path: Path,
    format_name: str,
    manifest: BackupManifest | None,
    registry,
    registry_path: Path,
) -> dict[str, object]:
    records = registry.list()
    status_counts = Counter(record.status.value for record in records)
    return {
        "path": str(path),
        "format": format_name,
        "manifest": manifest,
        "registry": str(registry_path),
        "agents": len(records),
        "agent_names": _format_agent_names(records),
        "status_counts": _format_status_counts(status_counts),
        "agent_profiles": _format_agent_profiles(records),
    }


def _build_import_preview(
    current_registry,
    incoming_registry,
    *,
    current_team_metadata: TeamMetadata,
    incoming_team_metadata: TeamMetadata | None,
    verbose: bool = False,
) -> dict[str, object]:
    current_records = {record.agent_id: record for record in current_registry.list()}
    incoming_records = {record.agent_id: record for record in incoming_registry.list()}
    effective_incoming_team_metadata = (
        current_team_metadata if incoming_team_metadata is None else incoming_team_metadata
    )

    current_ids = set(current_records)
    incoming_ids = set(incoming_records)

    added_ids = sorted(incoming_ids - current_ids)
    removed_ids = sorted(current_ids - incoming_ids)
    shared_ids = sorted(current_ids & incoming_ids)

    changed_ids: list[str] = []
    unchanged_count = 0
    change_details: list[str] = []
    for agent_id in shared_ids:
        current_record = current_records[agent_id]
        incoming_record = incoming_records[agent_id]
        changes: list[str] = []
        if current_record.name != incoming_record.name:
            changes.append(
                f"name:{_format_preview_value(current_record.name)}->{_format_preview_value(incoming_record.name)}"
            )
        if current_record.status != incoming_record.status:
            changes.append(
                f"status:{current_record.status.value}->{incoming_record.status.value}"
            )
        if current_record.persona != incoming_record.persona:
            changes.append(
                f"persona:{_format_preview_value(current_record.persona)}->{_format_preview_value(incoming_record.persona)}"
            )
        if current_record.role != incoming_record.role:
            changes.append(
                f"role:{_format_preview_value(current_record.role)}->{_format_preview_value(incoming_record.role)}"
            )
        if current_record.model != incoming_record.model:
            changes.append(
                f"model:{_format_preview_value(current_record.model)}->{_format_preview_value(incoming_record.model)}"
            )
        if current_record.tags != incoming_record.tags:
            changes.append(
                f"tags:{_format_encoded_list_or_dash(current_record.tags)}->{_format_encoded_list_or_dash(incoming_record.tags)}"
            )
        if changes:
            changed_ids.append(agent_id)
            change_details.append(f"{agent_id}:{'+'.join(changes)}")
        else:
            unchanged_count += 1

    team_changes: list[str] = []
    if current_team_metadata.team_name != effective_incoming_team_metadata.team_name:
        team_changes.append(
            f"name:{_format_preview_value(current_team_metadata.team_name)}->{_format_preview_value(effective_incoming_team_metadata.team_name)}"
        )
    if current_team_metadata.team_description != effective_incoming_team_metadata.team_description:
        team_changes.append(
            f"description:{_format_preview_value(current_team_metadata.team_description)}->{_format_preview_value(effective_incoming_team_metadata.team_description)}"
        )
    if current_team_metadata.team_tags != effective_incoming_team_metadata.team_tags:
        team_changes.append(
            f"tags:{_format_encoded_list_or_dash(current_team_metadata.team_tags)}->{_format_encoded_list_or_dash(effective_incoming_team_metadata.team_tags)}"
        )
    if current_team_metadata.default_agent_id != effective_incoming_team_metadata.default_agent_id:
        team_changes.append(
            f"default_agent_id:{_format_preview_value(current_team_metadata.default_agent_id)}->{_format_preview_value(effective_incoming_team_metadata.default_agent_id)}"
        )

    risk_level, risk_reasons = _classify_import_risk(
        current_agents=len(current_records),
        incoming_agents=len(incoming_records),
        added_count=len(added_ids),
        removed_count=len(removed_ids),
        changed_count=len(changed_ids),
        shared_count=len(shared_ids),
        team_changed=bool(team_changes),
    )

    list_formatter = _format_list_or_dash if verbose else _format_preview_list

    return {
        "current_agents": len(current_records),
        "incoming_agents": len(incoming_records),
        "added_count": len(added_ids),
        "removed_count": len(removed_ids),
        "changed_count": len(changed_ids),
        "unchanged_count": unchanged_count,
        "added_ids": list_formatter(added_ids),
        "removed_ids": list_formatter(removed_ids),
        "changed_ids": list_formatter(changed_ids),
        "added_names": list_formatter([
            _format_preview_value(incoming_records[agent_id].name) for agent_id in added_ids
        ]),
        "removed_names": list_formatter([
            _format_preview_value(current_records[agent_id].name) for agent_id in removed_ids
        ]),
        "changed_names": list_formatter([
            _format_preview_value(incoming_records[agent_id].name) for agent_id in changed_ids
        ]),
        "change_details": list_formatter(change_details),
        "team_details": list_formatter(team_changes),
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
    }


def _classify_import_risk(
    *,
    current_agents: int,
    incoming_agents: int,
    added_count: int,
    removed_count: int,
    changed_count: int,
    shared_count: int,
    team_changed: bool,
) -> tuple[str, str]:
    if added_count == 0 and removed_count == 0 and changed_count == 0 and not team_changed:
        return "safe", "identical"

    reasons: list[str] = []
    if current_agents == 0:
        reasons.append("current_empty")
    if added_count > 0:
        reasons.append("added_agents")
    if removed_count > 0:
        reasons.append("removed_agents")
    if changed_count > 0:
        reasons.append("changed_agents")
    if team_changed:
        reasons.append("changed_team_metadata")
    if current_agents > 0 and incoming_agents > 0 and shared_count == 0:
        reasons.append("no_shared_agent_ids")

    if current_agents == 0:
        return "low-change", _format_list_or_dash(reasons)
    if current_agents > 0 and incoming_agents > 0 and shared_count == 0:
        return "replacement-like", _format_list_or_dash(reasons)
    if removed_count > 0 or changed_count > 1 or added_count > 1:
        return "high-impact", _format_list_or_dash(reasons)
    return "low-change", _format_list_or_dash(reasons)


def _maybe_load_adjacent_manifest(registry_path: Path) -> BackupManifest | None:
    manifest_path = registry_path.parent / "manifest.json"
    if not manifest_path.exists() or manifest_path.is_dir():
        return None
    try:
        manifest = load_backup_manifest(manifest_path)
    except ValueError:
        return None
    return manifest if manifest.registry_file == registry_path.name else None


def _team_metadata_from_manifest(manifest: BackupManifest | None) -> TeamMetadata | None:
    if manifest is None or manifest.scope_version < 2:
        return None
    return TeamMetadata(
        team_name=manifest.team_name,
        team_description=manifest.team_description,
        team_tags=list(manifest.team_tags),
        default_agent_id=manifest.default_agent_id,
    )


def _handle_team_show(team_metadata_path: Path) -> int:
    metadata = load_team_metadata(team_metadata_path)
    print(_format_team_metadata(metadata))
    return 0


def _handle_team_update(args: argparse.Namespace, registry, team_metadata_path: Path) -> int:
    metadata = load_team_metadata(team_metadata_path)
    updated = _resolve_team_metadata_update(args, metadata, registry)
    save_team_metadata(team_metadata_path, updated)
    print(
        "updated "
        f"name={_format_preview_value(updated.team_name)} "
        f"description={_format_preview_value(updated.team_description)} "
        f"tags={_format_encoded_list_or_dash(updated.team_tags)} "
        f"default_agent_id={_format_preview_value(updated.default_agent_id)}"
    )
    return 0


def _resolve_team_metadata_update(args: argparse.Namespace, metadata: TeamMetadata, registry) -> TeamMetadata:
    updates_requested = False

    team_name = metadata.team_name
    if args.clear_name:
        team_name = ""
        updates_requested = True
    elif args.name is not None:
        team_name = _normalize_optional_cli_text(args.name, field_name="team name")
        updates_requested = True

    team_description = metadata.team_description
    if args.clear_description:
        team_description = ""
        updates_requested = True
    elif args.description is not None:
        team_description = _normalize_optional_cli_text(args.description, field_name="team description")
        updates_requested = True

    team_tags = list(metadata.team_tags)
    if args.clear_tags:
        team_tags = []
        updates_requested = True
    elif args.tags is not None:
        team_tags = _parse_team_tags(args.tags)
        updates_requested = True

    default_agent_id = metadata.default_agent_id
    if args.clear_default_agent:
        default_agent_id = ""
        updates_requested = True
    elif args.default_agent is not None:
        default_agent_id = _normalize_optional_cli_text(
            args.default_agent,
            field_name="default agent id",
        )
        registry.get(default_agent_id)
        updates_requested = True

    if not updates_requested:
        raise ValueError("Team update requires at least one change flag")

    return TeamMetadata(
        team_name=team_name,
        team_description=team_description,
        team_tags=team_tags,
        default_agent_id=default_agent_id,
    )


def _normalize_optional_cli_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name.capitalize()} must not be empty")
    return normalized


def _parse_tag_list(raw_tags: str, *, field_name: str) -> list[str]:
    tags = [item.strip() for item in raw_tags.split(",")]
    if any(not item for item in tags):
        raise ValueError(f"{field_name} must be a comma-separated list of non-empty values")
    return list(dict.fromkeys(tags))


def _parse_team_tags(raw_tags: str) -> list[str]:
    return _parse_tag_list(raw_tags, field_name="Team tags")


def _format_team_metadata(metadata: TeamMetadata) -> str:
    return (
        "team "
        f"name={_format_preview_value(metadata.team_name)} "
        f"description={_format_preview_value(metadata.team_description)} "
        f"tags={_format_encoded_list_or_dash(metadata.team_tags)} "
        f"default_agent_id={_format_preview_value(metadata.default_agent_id)}"
    )


def _format_agent_profiles(records: list[AgentRecord]) -> str:
    if not records:
        return "-"
    return ",".join(
        (
            f"{record.agent_id}:"
            f"role={_format_preview_value(record.role)}+"
            f"model={_format_preview_value(record.model)}+"
            f"tags={_format_encoded_list_or_dash(record.tags)}"
        )
        for record in records
    )


def _format_agent_names(records: list[AgentRecord]) -> str:
    return ",".join(_format_preview_value(record.name) for record in records) if records else "-"


def _format_list_or_dash(values: list[str]) -> str:
    return ",".join(values) if values else "-"


def _format_encoded_list_or_dash(values: list[str]) -> str:
    return ",".join(_format_preview_value(value) for value in values) if values else "-"


def _format_preview_list(values: list[str], *, limit: int = 5) -> str:
    if not values:
        return "-"
    if len(values) <= limit:
        return ",".join(values)
    visible = ",".join(values[:limit])
    return f"{visible},...(+{len(values) - limit})"


def _format_preview_value(value: str) -> str:
    if not value:
        return "∅"
    return value.replace("\n", "↵").replace("\r", "␍").replace(" ", "␠").replace(",", "⸴")


def _format_status_counts(status_counts: Counter[str]) -> str:
    if not status_counts:
        return "-"
    ordered_statuses = (
        AgentStatus.RUNNING.value,
        AgentStatus.STOPPED.value,
        AgentStatus.ARCHIVED.value,
    )
    return ",".join(
        f"{status}:{status_counts[status]}"
        for status in ordered_statuses
        if status_counts[status]
    )


def _confirm_import_overwrite() -> bool:
    print("confirm prompt=Proceed with overwrite import? [y/N]")
    try:
        response = input()
    except EOFError:
        return False
    return response.strip().lower() in {"y", "yes"}


def _normalize_export_metadata_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Export {field_name} must not be empty")
    return normalized


def _load_registry_for_transfer(
    source: str,
    storage: JsonRegistryStorage,
) -> tuple[object, TeamMetadata | None, Path, Path]:
    source_path = Path(source)
    if not source_path.exists():
        raise ValueError(f"Import file {source!r} not found")
    if source_path.is_dir():
        raise ValueError(f"Import file {source!r} is a directory")
    if is_bundle_archive_path(source_path):
        manifest, registry, bundle_path, registry_path = inspect_bundle_archive(source_path, storage)
        team_metadata = _team_metadata_from_manifest(manifest)
        _validate_import_team_metadata(team_metadata, registry)
        return registry, team_metadata, bundle_path, registry_path

    import_path = _resolve_import_registry_path(source_path)
    registry = storage.load(import_path)
    manifest = load_backup_manifest(source_path) if source_path.name == "manifest.json" else _maybe_load_adjacent_manifest(source_path)
    team_metadata = _team_metadata_from_manifest(manifest)
    _validate_import_team_metadata(team_metadata, registry)
    return registry, team_metadata, source_path, import_path


def _validate_import_team_metadata(team_metadata: TeamMetadata | None, registry) -> None:
    if team_metadata is None or not team_metadata.default_agent_id:
        return
    registry.get(team_metadata.default_agent_id)


def _sanitize_team_metadata_for_registry(metadata: TeamMetadata, registry) -> TeamMetadata:
    if not metadata.default_agent_id:
        return metadata
    try:
        registry.get(metadata.default_agent_id)
    except LookupError:
        return TeamMetadata(
            team_name=metadata.team_name,
            team_description=metadata.team_description,
            team_tags=list(metadata.team_tags),
            default_agent_id="",
        )
    return metadata


def _get_runtime_command_name(args: argparse.Namespace) -> str | None:
    resource = getattr(args, "resource", None)
    if resource == "agent":
        return getattr(args, "agent_command", None)
    if resource == "artifact":
        return getattr(args, "artifact_command", None)
    if resource == "team":
        return getattr(args, "team_command", None)
    if resource == "thread":
        return resource if getattr(args, "thread_command", None) is not None else None
    return resource


def _resolve_import_registry_path(source_path: Path) -> Path:
    if source_path.name != "manifest.json":
        return source_path

    manifest = load_backup_manifest(source_path)
    registry_path = source_path.parent / manifest.registry_file
    if not registry_path.exists():
        raise ValueError(
            f"Manifest {str(source_path)!r} references missing registry file "
            f"{manifest.registry_file!r}"
        )
    if registry_path.is_dir():
        raise ValueError(
            f"Manifest {str(source_path)!r} references registry path "
            f"{str(registry_path)!r} which is a directory"
        )
    return registry_path


def _handle_agent_status(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> int:
    record = registry.get(args.agent_id)
    try:
        runtime_state = _resolve_runtime_state_for_status(record, runtime_adapter)
    except ValueError as exc:
        if _is_stale_runtime_error(exc):
            _clear_stale_runtime_state(args.agent_id, storage, registry_path, registry)
            raise ValueError(
                f"Stale runtime state detected for agent {args.agent_id!r}; cleared local runtime state"
            ) from exc
        raise
    print(_format_agent_status(record, runtime_state))
    return 0


def _handle_agent_start(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> int:
    record = registry.get(args.agent_id)
    if record.status is AgentStatus.RUNNING:
        raise ValueError(f"Agent with id {args.agent_id!r} is already marked running")
    stored_runtime_state = RuntimeStateStorage().load(get_runtime_state_path()).get(args.agent_id)
    if stored_runtime_state is not None and stored_runtime_state.runtime_status in {
        RuntimeStatus.STARTING,
        RuntimeStatus.RUNNING,
        RuntimeStatus.STOPPING,
    }:
        raise ValueError(f"Agent runtime for id {args.agent_id!r} is already active")
    start_result = runtime_adapter.start(RuntimeStartRequest(agent=record))
    updated = registry.set_status(args.agent_id, AgentStatus.RUNNING)
    storage.save(registry_path, registry)
    print(
        f"updated agent_id={updated.agent_id} status={updated.status.value} "
        f"runtime_status={start_result.runtime.runtime_status.value} "
        f"runtime_handle={_format_preview_value(start_result.runtime.runtime_handle)}"
    )
    return 0


def _handle_agent_stop(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> int:
    registry.get(args.agent_id)
    stored_runtime_state = RuntimeStateStorage().load(get_runtime_state_path()).get(args.agent_id)
    if stored_runtime_state is None or stored_runtime_state.runtime_status not in {
        RuntimeStatus.STARTING,
        RuntimeStatus.RUNNING,
        RuntimeStatus.STOPPING,
    }:
        raise ValueError(f"Agent runtime for id {args.agent_id!r} is not running")
    try:
        stop_result = runtime_adapter.stop(RuntimeStopRequest(agent_id=args.agent_id))
    except ValueError as exc:
        if _is_stale_runtime_error(exc):
            _clear_stale_runtime_state(args.agent_id, storage, registry_path, registry)
            raise ValueError(
                f"Stale runtime state detected for agent {args.agent_id!r}; cleared local runtime state"
            ) from exc
        raise
    updated = registry.set_status(args.agent_id, AgentStatus.STOPPED)
    storage.save(registry_path, registry)
    print(
        f"updated agent_id={updated.agent_id} status={updated.status.value} "
        f"runtime_status={stop_result.runtime.runtime_status.value} "
        f"runtime_handle={_format_preview_value(stop_result.runtime.runtime_handle)}"
    )
    return 0


def _handle_agent_logs(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> int:
    registry.get(args.agent_id)
    stored_runtime_state = RuntimeStateStorage().load(get_runtime_state_path()).get(args.agent_id)
    if stored_runtime_state is None or stored_runtime_state.runtime_status not in {
        RuntimeStatus.STARTING,
        RuntimeStatus.RUNNING,
        RuntimeStatus.STOPPING,
    }:
        raise ValueError(f"Agent runtime for id {args.agent_id!r} is not running")
    try:
        logs_result = runtime_adapter.logs(
            RuntimeLogsRequest(agent_id=args.agent_id, tail_lines=args.tail_lines)
        )
    except ValueError as exc:
        if _is_stale_runtime_error(exc):
            _clear_stale_runtime_state(args.agent_id, storage, registry_path, registry)
            raise ValueError(
                f"Stale runtime state detected for agent {args.agent_id!r}; cleared local runtime state"
            ) from exc
        raise
    print(
        f"logs agent_id={args.agent_id} runtime_status={logs_result.runtime.runtime_status.value} "
        f"runtime_handle={_format_preview_value(logs_result.runtime.runtime_handle)} lines={len(logs_result.lines)}"
    )
    for line in logs_result.lines:
        print(f"line={_format_preview_value(line)}")
    return 0


def _resolve_runtime_state_for_status(
    record: AgentRecord,
    runtime_adapter: DockerRuntimeAdapter,
) -> RuntimeState:
    stored_states = RuntimeStateStorage().load(get_runtime_state_path())
    if record.agent_id in stored_states:
        return runtime_adapter.status(RuntimeStatusRequest(agent_id=record.agent_id)).runtime
    return RuntimeState(agent_id=record.agent_id, runtime_status=RuntimeStatus.STOPPED)


def _is_stale_runtime_error(exc: ValueError) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("missing container", "no such container"))


def _clear_stale_runtime_state(
    agent_id: str,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> None:
    RuntimeStateStorage().remove(get_runtime_state_path(), agent_id)
    record = registry.get(agent_id)
    if record.status is AgentStatus.RUNNING:
        registry.set_status(agent_id, AgentStatus.STOPPED)
        storage.save(registry_path, registry)


def _handle_agent_tune(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    updates = _resolve_agent_tune_updates(args)
    updated = registry.get(args.agent_id)
    if "persona" in updates:
        updated = registry.set_persona(args.agent_id, updates["persona"])
    profile_updates = {
        key: updates[key]
        for key in ("role", "model", "tags")
        if key in updates
    }
    if profile_updates:
        updated = registry.set_profile_metadata(args.agent_id, **profile_updates)
    if "runtime_spec" in updates:
        updated = registry.set_runtime_spec(args.agent_id, updates["runtime_spec"])
    storage.save(registry_path, registry)
    print(_format_agent_tune_result(updated, updates))
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
    RuntimeStateStorage().remove(get_runtime_state_path(), args.agent_id)
    team_metadata_path = get_team_metadata_path()
    team_metadata = load_team_metadata(team_metadata_path)
    if team_metadata.default_agent_id == args.agent_id:
        save_team_metadata(
            team_metadata_path,
            TeamMetadata(
                team_name=team_metadata.team_name,
                team_description=team_metadata.team_description,
                team_tags=list(team_metadata.team_tags),
                default_agent_id="",
            ),
        )
    print(f"purged agent_id={args.agent_id}")
    return 0


def _format_record(record: AgentRecord) -> str:
    return (
        f"agent_id={record.agent_id} "
        f"name={_format_preview_value(record.name)} "
        f"status={record.status.value}"
    )


def _format_agent_status(record: AgentRecord, runtime_state: RuntimeState) -> str:
    runtime_handle = (
        _format_preview_value(runtime_state.runtime_handle)
        if runtime_state.runtime_handle is not None
        else "-"
    )
    return (
        f"{_format_record(record)} "
        f"persona={_format_preview_value(record.persona)} "
        f"role={_format_preview_value(record.role)} "
        f"model={_format_preview_value(record.model)} "
        f"tags={_format_encoded_list_or_dash(record.tags)} "
        f"runtime_status={runtime_state.runtime_status.value} "
        f"runtime_handle={runtime_handle}"
    )


def _format_agent_tune_result(record: AgentRecord, updates: dict[str, object]) -> str:
    parts = [f"updated agent_id={record.agent_id}"]
    if "persona" in updates:
        parts.append(f"persona={_format_preview_value(record.persona)}")
    if "role" in updates:
        parts.append(f"role={_format_preview_value(record.role)}")
    if "model" in updates:
        parts.append(f"model={_format_preview_value(record.model)}")
    if "tags" in updates:
        parts.append(f"tags={_format_encoded_list_or_dash(record.tags)}")
    if "runtime_spec" in updates:
        if record.runtime_spec is None:
            parts.append("runtime=cleared")
        else:
            parts.append(f"runtime_image={_format_preview_value(record.runtime_spec.image)}")
            parts.append(f"runtime_workspace={_format_preview_value(record.runtime_spec.workspace)}")
            parts.append(
                f"runtime_command={_format_encoded_list_or_dash(record.runtime_spec.command)}"
            )
            runtime_env_keys = sorted(record.runtime_spec.env)
            parts.append(f"runtime_env={_format_encoded_list_or_dash(runtime_env_keys)}")
    return " ".join(parts)


def _resolve_agent_tune_updates(args: argparse.Namespace) -> dict[str, object]:
    updates: dict[str, object] = {}
    if args.persona is not None or args.persona_file is not None:
        updates["persona"] = _resolve_persona(args)
    if args.clear_role:
        updates["role"] = ""
    elif args.role is not None:
        updates["role"] = _normalize_optional_cli_text(args.role, field_name="agent role")
    if args.clear_model:
        updates["model"] = ""
    elif args.model is not None:
        updates["model"] = _normalize_optional_cli_text(args.model, field_name="agent model")
    if args.clear_tags:
        updates["tags"] = []
    elif args.tags is not None:
        updates["tags"] = _parse_tag_list(args.tags, field_name="Agent tags")
    if args.clear_runtime:
        if any(
            value is not None
            for value in (
                args.runtime_image,
                args.runtime_workspace,
                args.runtime_command,
                args.runtime_env,
            )
        ):
            raise ValueError("Agent tune runtime clear cannot be combined with runtime set flags")
        updates["runtime_spec"] = None
    elif any(
        value is not None
        for value in (
            args.runtime_image,
            args.runtime_workspace,
            args.runtime_command,
            args.runtime_env,
        )
    ):
        updates["runtime_spec"] = _resolve_runtime_spec(args)
    if not updates:
        raise ValueError("Agent tune requires at least one change flag")
    return updates


def _resolve_runtime_spec(args: argparse.Namespace) -> RuntimeSpec:
    if args.runtime_image is None:
        raise ValueError("Agent runtime spec requires --runtime-image")
    if args.runtime_workspace is None:
        raise ValueError("Agent runtime spec requires --runtime-workspace")
    if args.runtime_command is None:
        raise ValueError("Agent runtime spec requires at least one --runtime-command")
    if args.runtime_env is None:
        raise ValueError("Agent runtime spec requires at least one --runtime-env")
    image = _normalize_optional_cli_text(args.runtime_image, field_name="runtime image")
    workspace = _normalize_optional_cli_text(
        args.runtime_workspace,
        field_name="runtime workspace",
    )
    command = [
        _normalize_optional_cli_text(part, field_name="runtime command item")
        for part in args.runtime_command
    ]
    env = _parse_runtime_env(args.runtime_env)
    return RuntimeSpec(
        image=image,
        workspace=workspace,
        command=command,
        env=env,
    )


def _parse_runtime_env(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("Agent runtime env entries must use KEY=VALUE format")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Agent runtime env entries must use non-empty KEY=VALUE format")
        if key in env:
            raise ValueError(f"Duplicate agent runtime env key: {key!r}")
        env[key] = value
    return env


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
