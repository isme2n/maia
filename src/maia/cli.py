"""Command-line interface for Maia."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
import sys
import uuid
from urllib.parse import quote

from maia.agent_model import AgentRecord, AgentSetupStatus, AgentStatus, SpeakingStyle
import maia.agent_setup_session as agent_setup_session
from maia.runtime_spec import RuntimeSpec
from maia.app_state import (
    get_agent_hermes_home,
    get_default_export_path,
    get_state_db_path,
    get_team_metadata_path,
)
from maia.backup_manifest import BackupManifest, load_backup_manifest, write_backup_manifest
from maia.bundle_archive import (
    inspect_bundle_archive,
    is_bundle_archive_path,
    write_bundle_archive,
)
from maia.cli_bootstrap import (
    handle_doctor,
    handle_setup,
)
from maia.cli_init import (
    InitDependencies,
    derive_init_next_step,
    derive_init_runtime_status,
    ensure_init_infra_ready,
    format_init_output_lines,
    handle_init,
    init_runtime_start_capable,
    init_infra_ready,
    select_init_agent,
)
from maia.cli_parser import (
    AGENT_ID_COMMANDS,
    LIFECYCLE_STATUS_BY_COMMAND,
    TOP_LEVEL_COLLAB_COMMANDS,
    build_parser,
)
from maia.docker_runtime_adapter import DockerRuntimeAdapter
from maia import infra_runtime
from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)
from maia.keryx_skill import ensure_agent_keryx_skill_installed
from maia.keryx_service import KeryxService
from maia.runtime_adapter import RuntimeLogsRequest, RuntimeStatusRequest, RuntimeStopRequest, RuntimeStartRequest, RuntimeState, RuntimeStatus
from maia.runtime_state_storage import RuntimeStateStorage
from maia.sqlite_state import SQLiteState
from maia.storage import JsonRegistryStorage
from maia.team_metadata import TeamMetadata, load_team_metadata, save_team_metadata

_ACTIVE_RUNTIME_STATUSES = frozenset(
    {
        RuntimeStatus.STARTING,
        RuntimeStatus.RUNNING,
        RuntimeStatus.STOPPING,
    }
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(argv_list)
    if _get_runtime_command_name(args) is None:
        args.parser.print_help()
        return 0
    return _handle_runtime_command(args)


def _handle_runtime_command(args: argparse.Namespace) -> int:
    storage = JsonRegistryStorage()
    state_path = get_state_db_path()
    team_metadata_path = get_team_metadata_path()
    resource = getattr(args, "resource", None)

    try:
        command_name = _get_runtime_command_name(args)
        if resource == "init":
            return _handle_init(storage, state_path, team_metadata_path)
        if resource == "doctor":
            return handle_doctor(verbose=getattr(args, "verbose", False))
        if resource == "setup":
            return handle_setup()
        if resource == "import":
            return _handle_transfer_import(args, storage, state_path)
        if resource == "export":
            registry = storage.load(state_path)
            return _handle_transfer_export(args, storage, registry)
        if resource == "inspect":
            return _handle_transfer_inspect(args, storage)
        if resource == "team" and command_name == "show":
            return _handle_team_show(team_metadata_path)
        if resource == "team" and command_name == "update":
            registry = storage.load(state_path)
            return _handle_team_update(args, registry, team_metadata_path)
        if resource == "workspace" and command_name == "show":
            registry = storage.load(state_path)
            return _handle_workspace_show(args, registry)
        if resource == "handoff":
            registry = storage.load(state_path)
            keryx_service = KeryxService(state_path)
            if command_name == "add":
                return _handle_handoff_add(args, registry, keryx_service)
            if command_name == "list":
                return _handle_handoff_list(args, keryx_service)
            if command_name == "show":
                return _handle_handoff_show(args, keryx_service, registry)
        if resource in TOP_LEVEL_COLLAB_COMMANDS:
            keryx_service = KeryxService(state_path)
            if command_name == "thread":
                return _handle_thread(args, keryx_service)

        registry = storage.load(state_path)
        if resource == "agent" and command_name in AGENT_ID_COMMANDS:
            args.agent_lookup = args.agent_id
            args.agent_id = _resolve_agent_reference(registry, args.agent_id)
        runtime_adapter = _build_runtime_adapter()
        if command_name == "new":
            return _handle_agent_new(args, storage, state_path, registry)
        if command_name == "setup":
            return _handle_agent_setup(args, storage, state_path, registry)
        if command_name == "setup-gateway":
            return _handle_agent_setup_gateway(args, storage, state_path, registry)
        if command_name == "list":
            return _handle_agent_list(registry)
        if command_name == "status":
            return _handle_agent_status(args, storage, state_path, registry, runtime_adapter)
        if command_name == "logs":
            return _handle_agent_logs(args, storage, state_path, registry, runtime_adapter)
        if command_name == "start":
            return _handle_agent_start(args, storage, state_path, registry, runtime_adapter)
        if command_name == "stop":
            return _handle_agent_stop(args, storage, state_path, registry, runtime_adapter)
        if command_name == "tune":
            return _handle_agent_tune(args, storage, state_path, registry)
        if command_name == "purge":
            return _handle_agent_purge(args, storage, state_path, registry)
        if command_name == "purge-all":
            return _handle_agent_purge_all(args, storage, state_path, registry)
        if command_name in {"archive", "restore"}:
            return _handle_agent_lifecycle(args, storage, state_path, registry)
        if command_name == "archive-all":
            return _handle_agent_archive_all(storage, state_path, registry)
    except (LookupError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    raise ValueError(f"Unsupported command: {command_name}")




def _handle_init(
    storage: JsonRegistryStorage,
    state_path: Path | str,
    team_metadata_path: Path | str,
) -> int:
    return handle_init(
        storage,
        state_path,
        team_metadata_path,
        deps=InitDependencies(
            ensure_init_infra_ready=ensure_init_infra_ready,
            init_infra_ready=init_infra_ready,
            load_team_metadata=load_team_metadata,
            select_init_agent=select_init_agent,
            create_agent_interactively=_create_agent_interactively,
            format_created_agent_line=_format_created_agent_line,
            load_runtime_setup_state=lambda agent_id: RuntimeStateStorage().load(get_state_db_path()).get(agent_id),
            derive_setup_state=_derive_setup_state,
            run_agent_setup_passthrough=_run_agent_setup_passthrough,
            orchestrate_init_gateway_setup_if_needed=_orchestrate_init_gateway_setup_if_needed,
            init_runtime_start_capable=init_runtime_start_capable,
            build_runtime_adapter=_build_runtime_adapter,
            orchestrate_init_runtime_start_if_needed=_orchestrate_init_runtime_start_if_needed,
            resolve_runtime_state_for_init=_resolve_runtime_state_for_init,
            sync_registry_status_from_runtime_state=_sync_registry_status_from_runtime_state,
            derive_gateway_setup_state=_derive_gateway_setup_state,
            is_gateway_start_ready=_is_gateway_start_ready,
            is_default_destination_ready=_is_default_destination_ready,
            derive_init_runtime_status=derive_init_runtime_status,
            derive_init_next_step=derive_init_next_step,
            format_init_output_lines=format_init_output_lines,
            format_preview_value=_format_preview_value,
        ),
    )


def _orchestrate_init_gateway_setup_if_needed(record: AgentRecord) -> int | None:
    runtime_state = RuntimeStateStorage().load(get_state_db_path()).get(record.agent_id)
    runtime_state = _refresh_gateway_setup_state_from_hermes_home(
        record,
        runtime_state,
        allow_downgrade=True,
    )
    if _derive_setup_state(runtime_state) != "complete":
        return None
    if _is_default_destination_ready(_derive_gateway_setup_state(runtime_state)):
        return None
    gateway_exit_code, _gateway_result, gateway_error = _run_agent_setup_passthrough(
        record,
        setup_target="gateway",
    )
    if gateway_error is not None:
        print(
            f"Gateway setup failed for {record.name!r}. "
            f"Rerun maia agent setup-gateway {record.name} after fixing the Hermes setup issue. {gateway_error}",
            file=sys.stderr,
        )
    elif gateway_exit_code != 0:
        print(
            f"Gateway setup failed for {record.name!r}. "
            f"Rerun maia agent setup-gateway {record.name} after fixing the Hermes setup issue",
            file=sys.stderr,
        )
    return gateway_exit_code if gateway_exit_code != 0 else None


def _orchestrate_init_runtime_start_if_needed(
    record: AgentRecord,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> tuple[bool, str | None]:
    runtime_state = _resolve_runtime_state_for_init(
        record,
        runtime_adapter,
        infra_ready=True,
    )
    if _derive_setup_state(runtime_state) != "complete":
        return False, None
    if not _is_gateway_start_ready(_derive_gateway_setup_state(runtime_state)):
        return False, None
    if runtime_state is not None and runtime_state.runtime_status in _ACTIVE_RUNTIME_STATUSES:
        return False, None
    try:
        _start_agent_runtime(
            record,
            storage,
            registry_path,
            registry,
            runtime_adapter,
            stored_runtime_state=runtime_state,
        )
    except ValueError as exc:
        return True, str(exc)
    return True, None


def _resolve_runtime_state_for_init(
    record: AgentRecord,
    runtime_adapter: DockerRuntimeAdapter,
    *,
    infra_ready: bool,
) -> RuntimeState | None:
    runtime_state = RuntimeStateStorage().load(get_state_db_path()).get(record.agent_id)
    runtime_state = _refresh_gateway_setup_state_from_hermes_home(
        record,
        runtime_state,
        allow_downgrade=True,
    )
    if runtime_state is None or not infra_ready:
        return runtime_state
    if runtime_state.runtime_handle is None:
        if runtime_state.runtime_status is RuntimeStatus.RUNNING:
            return RuntimeState(
                agent_id=runtime_state.agent_id,
                runtime_status=RuntimeStatus.STOPPED,
                runtime_handle=None,
                setup_status=runtime_state.setup_status,
                gateway_setup_status=runtime_state.gateway_setup_status,
            )
        return runtime_state
    try:
        observed = runtime_adapter.status(RuntimeStatusRequest(agent_id=record.agent_id)).runtime
    except (LookupError, ValueError):
        return RuntimeState(
            agent_id=record.agent_id,
            runtime_status=RuntimeStatus.STOPPED,
            runtime_handle=runtime_state.runtime_handle,
            setup_status=runtime_state.setup_status,
            gateway_setup_status=runtime_state.gateway_setup_status,
        )
    return RuntimeState(
        agent_id=observed.agent_id,
        runtime_status=observed.runtime_status,
        runtime_handle=observed.runtime_handle,
        setup_status=(observed.setup_status or runtime_state.setup_status),
        gateway_setup_status=(observed.gateway_setup_status or runtime_state.gateway_setup_status),
    )


def _handle_agent_setup(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    _ = (storage, registry_path)
    record = registry.get(args.agent_id)
    requested_name = getattr(args, "agent_lookup", record.name)
    exit_code, result, error = _run_agent_setup_passthrough(record)
    if error is not None:
        print(
            f"Agent setup failed for {requested_name!r}. "
            f"Rerun maia agent setup {requested_name} after fixing the Hermes setup issue. {error}",
            file=sys.stderr,
        )
        return exit_code
    assert result is not None
    if exit_code == 0:
        print(
            f"Agent setup completed for {requested_name!r}. "
            f"Hermes home is ready at {result.hermes_home}. "
            f"Next: run maia agent start {requested_name}"
        )
        return 0
    print(
        f"Agent setup failed for {requested_name!r}. "
        f"Rerun maia agent setup {requested_name} after fixing the Hermes setup issue",
        file=sys.stderr,
    )
    return exit_code


def _handle_agent_setup_gateway(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    _ = (storage, registry_path)
    record = registry.get(args.agent_id)
    requested_name = getattr(args, "agent_lookup", record.name)
    exit_code, result, error = _run_agent_setup_passthrough(record, setup_target="gateway")
    if error is not None:
        print(
            f"Gateway setup failed for {requested_name!r}. "
            f"Rerun maia agent setup-gateway {requested_name} after fixing the Hermes setup issue. {error}",
            file=sys.stderr,
        )
        return exit_code
    assert result is not None
    if exit_code == 0:
        print(
            f"Gateway setup completed for {requested_name!r}. "
            f"Hermes home is ready at {result.hermes_home}. "
            f"Next: run maia agent start {requested_name}"
        )
        return 0
    print(
        f"Gateway setup failed for {requested_name!r}. "
        f"Rerun maia agent setup-gateway {requested_name} after fixing the Hermes setup issue",
        file=sys.stderr,
    )
    return exit_code


def _run_agent_setup_passthrough(
    record: AgentRecord,
    *,
    setup_target: str | None = None,
) -> tuple[int, agent_setup_session.AgentSetupSessionResult | None, str | None]:
    try:
        if setup_target is None:
            result = agent_setup_session.run_agent_setup_session(
                agent_id=record.agent_id,
                agent_name=record.name,
            )
        else:
            result = agent_setup_session.run_agent_setup_session(
                agent_id=record.agent_id,
                agent_name=record.name,
                setup_target=setup_target,
            )
    except ValueError as exc:
        if setup_target is None:
            _record_runtime_setup_state(
                record.agent_id,
                setup_status="incomplete",
                gateway_setup_status="incomplete",
            )
        else:
            _record_runtime_setup_state(record.agent_id, gateway_setup_status="incomplete")
        return 1, None, str(exc)

    if result.exit_code == 0 and setup_target is None:
        _sync_agent_hermes_soul(
            record,
            hermes_home=result.hermes_home,
            create_home=True,
        )
    if setup_target is None:
        _record_runtime_setup_state(
            record.agent_id,
            setup_status=result.setup_status,
            gateway_setup_status=result.gateway_setup_status,
        )
    else:
        _record_runtime_setup_state(
            record.agent_id,
            gateway_setup_status=result.gateway_setup_status,
        )
    return result.exit_code, result, None


def _record_runtime_setup_state(
    agent_id: str,
    *,
    setup_status: str | None = None,
    gateway_setup_status: str | None = None,
) -> None:
    state_storage = RuntimeStateStorage()
    state_path = get_state_db_path()
    states = state_storage.load(state_path)
    existing = states.get(agent_id)
    states[agent_id] = RuntimeState(
        agent_id=agent_id,
        runtime_status=(RuntimeStatus.STOPPED if existing is None else existing.runtime_status),
        runtime_handle=None if existing is None else existing.runtime_handle,
        setup_status=(
            setup_status
            if setup_status is not None
            else None if existing is None else existing.setup_status
        ),
        gateway_setup_status=(
            gateway_setup_status
            if gateway_setup_status is not None
            else None if existing is None else existing.gateway_setup_status
        ),
    )
    state_storage.save(state_path, states)




def _build_runtime_adapter() -> DockerRuntimeAdapter:
    return DockerRuntimeAdapter(
        state_storage=RuntimeStateStorage(),
        state_path=get_state_db_path(),
    )


def _prompt_required_text(label: str, *, field_name: str) -> str:
    while True:
        print(f"{label}:")
        try:
            value = input()
        except EOFError as exc:
            raise ValueError(f"{field_name} is required") from exc
        normalized = _normalize_optional_cli_text(value, field_name=field_name)
        if normalized:
            return normalized
        print(f"{field_name} is required", file=sys.stderr)


def _create_agent_interactively(
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> AgentRecord:
    name = _prompt_required_text("Agent name", field_name="agent name")
    if any(record.name == name for record in registry.list()):
        raise ValueError(f"Agent with name {name!r} already exists")
    call_sign = _prompt_required_text(
        "What should this agent call you?",
        field_name="agent call-sign",
    )
    speaking_style, speaking_style_details = _prompt_speaking_style()
    print("Persona examples:")
    print("- calm technical assistant")
    print("- fast research partner")
    print("- warm planning helper")
    persona = _prompt_required_text(
        "Persona",
        field_name="agent persona",
    )

    record = AgentRecord(
        agent_id=uuid.uuid4().hex[:8],
        name=name,
        call_sign=call_sign,
        status=AgentStatus.STOPPED,
        speaking_style=speaking_style,
        speaking_style_details=speaking_style_details,
        persona=persona,
        role="",
        model="",
        tags=[],
        runtime_spec=infra_runtime.default_agent_runtime_spec(name),
    )
    registry.add(record)
    storage.save(registry_path, registry)
    ensure_agent_keryx_skill_installed(record.agent_id)
    return record


def _format_created_agent_line(record: AgentRecord) -> str:
    created_parts = [
        f"created agent_id={record.agent_id}",
        f"name={_format_preview_value(record.name)}",
        f"call_sign={_format_preview_value(record.call_sign)}",
        f"speaking_style={_speaking_style_display(record.speaking_style)}",
    ]
    if record.speaking_style is SpeakingStyle.CUSTOM and record.speaking_style_details:
        created_parts.append(
            f"speaking_style_details={_format_preview_value(record.speaking_style_details)}"
        )
    created_parts.append(f"status={record.status.value}")
    return " ".join(created_parts)


def _handle_agent_new(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    record = _create_agent_interactively(storage, registry_path, registry)
    print(_format_created_agent_line(record))
    print(f"Next: run maia agent setup {record.name}")
    print(f"Tip: You can tune this agent later with maia agent tune {record.name}")
    return 0


def _handle_agent_list(registry) -> int:
    runtime_states = RuntimeStateStorage().load(get_state_db_path())
    for record in registry.list():
        print(_format_record(record, runtime_state=runtime_states.get(record.agent_id)))
    return 0


def _handle_thread(args, keryx_service: KeryxService) -> int:
    if args.thread_command == "list":
        return _handle_thread_list(args, keryx_service)
    if args.thread_command == "show":
        return _handle_thread_show(args, keryx_service)
    raise ValueError(f"Unsupported thread command: {args.thread_command!r}")


def _handle_thread_list(args, keryx_service: KeryxService) -> int:
    runtime_states = _load_thread_runtime_states()
    threads = sorted(
        keryx_service.list_threads(),
        key=lambda thread: (thread.updated_at, thread.thread_id),
        reverse=True,
    )
    if args.agent is not None:
        threads = [thread for thread in threads if args.agent in thread.participants]
    if args.status is not None:
        threads = [
            thread
            for thread in threads
            if _thread_visibility_status(thread) == args.status
        ]
    messages_by_thread = {
        thread.thread_id: keryx_service.list_thread_messages(thread.thread_id)
        for thread in threads
    }
    handoffs_by_thread = {
        thread.thread_id: keryx_service.list_thread_handoffs(thread.thread_id)
        for thread in threads
    }
    for thread in threads:
        overview = _format_thread_overview_fields(
            thread,
            messages_by_thread.get(thread.thread_id, []),
            handoffs_by_thread.get(thread.thread_id, []),
            runtime_states,
        )
        print(f"thread {overview}")
    return 0


def _handle_thread_show(args, keryx_service: KeryxService) -> int:
    limit = _validate_positive_limit(args.limit, field_name="Thread limit")
    thread = keryx_service.get_thread(args.thread_id)
    thread_messages = keryx_service.list_thread_messages(thread.thread_id)
    thread_handoffs = keryx_service.list_thread_handoffs(thread.thread_id)
    runtime_states = _load_thread_runtime_states()
    print(
        f"thread {_format_thread_overview_fields(thread, thread_messages, thread_handoffs, runtime_states)} "
        f"created_by={thread.created_by} created_at={thread.created_at} "
        f"{_format_recent_handoff_fields(_select_recent_handoff(thread_handoffs))}"
    )
    for message in thread_messages[:limit]:
        print(_format_message_line(message))
    return 0


def _handle_handoff_add(
    args,
    registry,
    keryx_service: KeryxService,
) -> int:
    thread = keryx_service.get_thread(args.thread_id)
    registry.get(args.from_agent)
    registry.get(args.to_agent)
    _require_thread_participant(
        thread,
        args.from_agent,
        error="Handoff sender must be a participant in the thread",
    )
    _require_thread_participant(
        thread,
        args.to_agent,
        error="Handoff recipient must be a participant in the thread",
    )

    timestamp = _timestamp_now()
    handoff = KeryxHandoffRecord(
        handoff_id=_new_id(),
        session_id=thread.thread_id,
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        kind=args.type,
        status=KeryxHandoffStatus.OPEN,
        location=args.location,
        summary=args.summary,
        created_at=timestamp,
        updated_at=timestamp,
    )
    keryx_service.create_thread_handoff(thread.thread_id, handoff)
    print(f"added {_format_handoff_line(handoff)}")
    return 0


def _handle_handoff_list(args, keryx_service: KeryxService) -> int:
    if args.thread_id is not None:
        handoffs = keryx_service.list_thread_handoffs(args.thread_id)
    else:
        handoffs = keryx_service.list_handoffs()

    for handoff in handoffs:
        print(_format_handoff_line(handoff))
    return 0


def _handle_handoff_show(args, keryx_service: KeryxService, registry) -> int:
    handoff = keryx_service.get_handoff(args.handoff_id)
    print(_format_handoff_line(handoff))
    print(
        _format_handoff_workspace_context_line(
            handoff.from_agent,
            registry,
            handoff_role="source",
        )
    )
    print(
        _format_handoff_workspace_context_line(
            handoff.to_agent,
            registry,
            handoff_role="target",
        )
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


def _message_sort_key(message: KeryxMessageRecord) -> str:
    return message.created_at


def _sorted_thread_messages(messages: Sequence[KeryxMessageRecord]) -> list[KeryxMessageRecord]:
    return sorted(messages, key=_message_sort_key)


def _handoff_sort_key(handoff: KeryxHandoffRecord) -> tuple[str, str]:
    return (handoff.created_at, handoff.handoff_id)


def _select_recent_handoff(
    thread_handoffs: Sequence[KeryxHandoffRecord],
) -> KeryxHandoffRecord | None:
    if not thread_handoffs:
        return None
    return max(thread_handoffs, key=_handoff_sort_key)


def _derive_thread_pending_on(thread_messages: Sequence[KeryxMessageRecord]) -> str:
    sorted_messages = _sorted_thread_messages(thread_messages)
    if not sorted_messages:
        return "-"
    return sorted_messages[-1].to_agent


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
        return RuntimeStateStorage().load(get_state_db_path())
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
    thread: KeryxSessionRecord,
    thread_messages: Sequence[KeryxMessageRecord],
    thread_handoffs: Sequence[KeryxHandoffRecord],
    runtime_states: dict[str, RuntimeState],
) -> str:
    recent_handoff = _select_recent_handoff(thread_handoffs)
    delegation_fields = _format_delegation_status_fields(
        thread,
        thread_messages,
        thread_handoffs,
    )
    return (
        f"thread_id={thread.thread_id} "
        f"topic={_format_preview_value(thread.topic)} "
        f"participants={_format_encoded_list_or_dash(thread.participants)} "
        f"participant_runtime={_format_thread_participant_runtime(thread.participants, runtime_states)} "
        f"status={_thread_visibility_status(thread)} updated_at={thread.updated_at} "
        f"pending_on={_format_preview_value(_derive_thread_pending_on(thread_messages))} "
        f"{delegation_fields} "
        f"handoffs={len(thread_handoffs)} messages={len(thread_messages)} "
        f"recent_handoff_id={recent_handoff.handoff_id if recent_handoff is not None else '-'} "
        f"recent_handoff_to={recent_handoff.to_agent if recent_handoff is not None else '-'} "
        f"recent_handoff_type={recent_handoff.kind if recent_handoff is not None else '-'} "
        f"recent_handoff_summary={_format_preview_value(recent_handoff.summary) if recent_handoff is not None else '-'}"
    )


def _thread_visibility_status(thread: KeryxSessionRecord) -> str:
    raw_status = thread.status.value if hasattr(thread.status, "value") else thread.status
    return "closed" if raw_status == KeryxSessionStatus.CLOSED.value else "open"


def _format_delegation_status_fields(
    thread: KeryxSessionRecord,
    thread_messages: Sequence[KeryxMessageRecord],
    thread_handoffs: Sequence[KeryxHandoffRecord],
) -> str:
    delegated_to = _derive_delegated_to(thread, thread_messages, thread_handoffs)
    delegation_status = _derive_delegation_status(thread, thread_messages, thread_handoffs)
    latest_internal_update = _derive_latest_internal_update(
        thread,
        thread_messages,
        thread_handoffs,
    )
    return (
        f"delegated_to={_format_preview_value(delegated_to)} "
        f"delegation_status={delegation_status} "
        f"current_thread_id={thread.thread_id} "
        f"latest_internal_update={_format_preview_value(latest_internal_update)}"
    )


def _derive_delegated_to(
    thread: KeryxSessionRecord,
    thread_messages: Sequence[KeryxMessageRecord],
    thread_handoffs: Sequence[KeryxHandoffRecord],
) -> str:
    anchor_agent = thread.created_by
    latest_event = _select_latest_internal_event(thread_messages, thread_handoffs)
    if latest_event is None:
        return "-"
    _event_kind, payload = latest_event
    return _derive_delegated_counterparty(anchor_agent, payload.from_agent, payload.to_agent)


def _derive_delegated_counterparty(anchor_agent: str, from_agent: str, to_agent: str) -> str:
    if from_agent == anchor_agent and to_agent != anchor_agent:
        return to_agent
    if to_agent == anchor_agent and from_agent != anchor_agent:
        return from_agent
    if from_agent != anchor_agent:
        return from_agent
    if to_agent != anchor_agent:
        return to_agent
    return "-"


def _derive_delegation_status(
    thread: KeryxSessionRecord,
    thread_messages: Sequence[KeryxMessageRecord],
    thread_handoffs: Sequence[KeryxHandoffRecord],
) -> str:
    anchor_agent = thread.created_by
    latest_event = _select_latest_internal_event(thread_messages, thread_handoffs)
    if latest_event is None:
        return "-"
    event_kind, payload = latest_event
    if event_kind == "handoff":
        return "handoff_ready" if payload.to_agent == anchor_agent else "answered"
    if payload.kind == "request":
        return "pending"
    if payload.kind == "question" and payload.to_agent == anchor_agent:
        return "needs_user_input"
    if payload.kind in {"answer", "report"}:
        return "answered"
    if payload.kind == "handoff":
        return "handoff_ready" if payload.to_agent == anchor_agent else "answered"
    return "-"


def _derive_latest_internal_update(
    thread: KeryxSessionRecord,
    thread_messages: Sequence[KeryxMessageRecord],
    thread_handoffs: Sequence[KeryxHandoffRecord],
) -> str:
    latest_event = _select_latest_internal_event(thread_messages, thread_handoffs)
    if latest_event is None:
        return "-"
    event_kind, payload = latest_event
    if event_kind == "handoff":
        summary = payload.summary if payload.summary else payload.location
        return f"{payload.from_agent} {payload.kind}: {_summarize_internal_update_text(summary)}"
    return f"{payload.from_agent} {payload.kind}: {_summarize_internal_update_text(payload.body)}"


def _summarize_internal_update_text(value: str, *, max_length: int = 48) -> str:
    if len(value) <= max_length:
        return value
    truncated = value[: max_length - 1].rstrip()
    return f"{truncated}…"


def _select_latest_internal_event(
    thread_messages: Sequence[KeryxMessageRecord],
    thread_handoffs: Sequence[KeryxHandoffRecord],
) -> tuple[str, KeryxMessageRecord | KeryxHandoffRecord] | None:
    latest_message = _sorted_thread_messages(thread_messages)[-1] if thread_messages else None
    latest_handoff = _select_recent_handoff(thread_handoffs)
    if latest_message is None and latest_handoff is None:
        return None
    if latest_handoff is None:
        return ("message", latest_message)
    if latest_message is None:
        return ("handoff", latest_handoff)
    if latest_handoff.created_at >= latest_message.created_at:
        return ("handoff", latest_handoff)
    return ("message", latest_message)


def _require_thread_participant(thread: KeryxSessionRecord, agent_id: str, *, error: str) -> None:
    if agent_id not in thread.participants:
        raise ValueError(error)


def _format_message_line(message: KeryxMessageRecord) -> str:
    reply_to = (
        _format_preview_value(message.reply_to_message_id)
        if message.reply_to_message_id is not None
        else "-"
    )
    return (
        f"message_id={message.message_id} thread_id={message.thread_id} "
        f"from_agent={message.from_agent} to_agent={message.to_agent} "
        f"kind={message.kind} body={_format_preview_value(message.body)} "
        f"created_at={message.created_at} reply_to_message_id={reply_to}"
    )


def _format_handoff_line(handoff: KeryxHandoffRecord) -> str:
    return (
        f"handoff_id={handoff.handoff_id} thread_id={handoff.thread_id} "
        f"from_agent={handoff.from_agent} to_agent={handoff.to_agent} "
        f"type={handoff.kind} location={_format_preview_value(handoff.location)} "
        f"summary={_format_preview_value(handoff.summary)} created_at={handoff.created_at}"
    )


def _format_recent_handoff_fields(handoff: KeryxHandoffRecord | None) -> str:
    if handoff is None:
        return (
            "recent_handoff_id=- recent_handoff_from=- recent_handoff_to=- "
            "recent_handoff_type=- recent_handoff_location=- "
            "recent_handoff_summary=- recent_handoff_created_at=-"
        )
    return (
        f"recent_handoff_id={handoff.handoff_id} "
        f"recent_handoff_from={handoff.from_agent} "
        f"recent_handoff_to={handoff.to_agent} "
        f"recent_handoff_type={handoff.kind} "
        f"recent_handoff_location={_format_preview_value(handoff.location)} "
        f"recent_handoff_summary={_format_preview_value(handoff.summary)} "
        f"recent_handoff_created_at={handoff.created_at}"
    )


def _format_handoff_workspace_context_line(
    agent_id: str,
    registry,
    *,
    handoff_role: str,
) -> str:
    parts = [
        "workspace",
        f"handoff_role={handoff_role}",
        f"agent_id={agent_id}",
    ]
    try:
        record = registry.get(agent_id)
    except LookupError:
        parts.extend(_format_workspace_context_fields(None))
        return " ".join(parts)
    parts.extend(_format_workspace_context_fields(record))
    return " ".join(parts)


def _format_workspace_context_fields(record: AgentRecord | None) -> list[str]:
    if record is None:
        return [
            "workspace_status=agent-missing",
            "workspace_basis=runtime_spec.workspace",
            "workspace=-",
            "runtime_image=-",
            "runtime_command=-",
            "runtime_env_keys=-",
        ]

    runtime_spec = record.runtime_spec
    if runtime_spec is None:
        return [
            "workspace_status=runtime-spec-missing",
            "workspace_basis=runtime_spec.workspace",
            "workspace=-",
            "runtime_image=-",
            "runtime_command=-",
            "runtime_env_keys=-",
        ]

    return [
        (
            "workspace_status=configured"
            if runtime_spec.workspace
            else "workspace_status=runtime-workspace-missing"
        ),
        "workspace_basis=runtime_spec.workspace",
        (
            f"workspace={_format_preview_value(runtime_spec.workspace)}"
            if runtime_spec.workspace
            else "workspace=-"
        ),
        f"runtime_image={_format_preview_value(runtime_spec.image)}",
        f"runtime_command={_format_encoded_list_or_dash(runtime_spec.command)}",
        f"runtime_env_keys={_format_encoded_list_or_dash(sorted(runtime_spec.env))}",
    ]


def _workspace_context_unavailable_error(agent_id: str, detail: str) -> ValueError:
    message = {
        "runtime spec is not configured": (
            f"Can't show the workspace for agent {agent_id!r} yet because runtime setup is missing"
        ),
        "runtime workspace is not configured": (
            f"Can't show the workspace for agent {agent_id!r} yet because the workspace path is missing"
        ),
    }.get(detail, f"Can't show the workspace for agent {agent_id!r}: {detail}")
    return ValueError(message)


def _agent_runtime_unavailable_error(agent_id: str, detail: str) -> ValueError:
    if detail.startswith("agent gateway setup is not complete"):
        return ValueError(
            f"Can't run agent {agent_id!r} yet because gateway setup is incomplete. "
            f"Run maia agent setup-gateway {detail.rsplit(' ', 1)[-1]}"
        )
    message = {
        "shared infra setup is not complete": (
            f"Can't run agent {agent_id!r} yet because shared infra setup is not complete"
        ),
        "agent setup is not complete": (
            f"Can't run agent {agent_id!r} yet because agent setup is incomplete"
        ),
        "agent gateway setup is not complete": (
            f"Can't run agent {agent_id!r} yet because gateway setup is incomplete"
        ),
        "runtime spec is not configured": (
            f"Can't run agent {agent_id!r} yet because runtime setup is missing"
        ),
        "runtime workspace is not configured": (
            f"Can't run agent {agent_id!r} yet because the workspace path is missing"
        ),
        "local runtime state is missing": (
            f"Maia can't find its saved runtime record for agent {agent_id!r}. "
            "Check Docker manually, then start the agent again if needed"
        ),
    }.get(detail, f"Can't use runtime commands for agent {agent_id!r}: {detail}")
    return ValueError(message)


def _agent_already_running_error(agent_id: str) -> ValueError:
    return ValueError(
        f"Agent {agent_id!r} is already running. Check its status or stop it first"
    )


def _agent_runtime_already_active_error(agent_id: str) -> ValueError:
    return ValueError(
        f"Agent {agent_id!r} already has a running container. Stop it first if you want to start again"
    )


def _agent_runtime_not_running_error(agent_id: str) -> ValueError:
    return ValueError(f"Agent {agent_id!r} is not running right now")


def _agent_logs_unavailable_error(agent_id: str, detail: str) -> ValueError:
    if detail == "agent setup is not complete":
        return ValueError(
            f"Can't show logs for agent {agent_id!r} yet because agent setup is not complete"
        )
    return _agent_runtime_unavailable_error(agent_id, detail)


def _stale_runtime_state_cleared_error(agent_id: str) -> ValueError:
    return ValueError(
        f"Maia found an old saved runtime record for agent {agent_id!r}, but the container is gone. "
        "The saved record was cleared. Start the agent again if you still need it"
    )


def _resolve_configured_runtime_spec(
    record: AgentRecord,
    *,
    error_factory: Callable[[str, str], ValueError],
) -> RuntimeSpec:
    runtime_spec = record.runtime_spec
    if runtime_spec is None:
        raise error_factory(record.agent_id, "runtime spec is not configured")
    if not runtime_spec.workspace:
        raise error_factory(record.agent_id, "runtime workspace is not configured")
    return runtime_spec


def _load_runtime_state_for_agent(record: AgentRecord) -> RuntimeState | None:
    runtime_state = RuntimeStateStorage().load(get_state_db_path()).get(record.agent_id)
    runtime_state = _refresh_gateway_setup_state_from_hermes_home(record, runtime_state)
    if runtime_state is None and record.status is AgentStatus.RUNNING:
        raise _agent_runtime_unavailable_error(record.agent_id, "local runtime state is missing")
    return runtime_state


def _refresh_gateway_setup_state_from_hermes_home(
    record: AgentRecord,
    runtime_state: RuntimeState | None,
    *,
    allow_downgrade: bool = False,
) -> RuntimeState | None:
    if runtime_state is None:
        return runtime_state
    if runtime_state.setup_status != "complete":
        return runtime_state
    if not allow_downgrade and _is_default_destination_ready(runtime_state.gateway_setup_status):
        return runtime_state
    derived_status = agent_setup_session.derive_gateway_setup_status(
        get_agent_hermes_home(record.agent_id)
    )
    if derived_status == runtime_state.gateway_setup_status:
        return runtime_state
    if (
        not allow_downgrade
        and _gateway_setup_status_rank(derived_status) <= _gateway_setup_status_rank(
            runtime_state.gateway_setup_status
        )
    ):
        return runtime_state
    updated_state = RuntimeState(
        agent_id=runtime_state.agent_id,
        runtime_status=runtime_state.runtime_status,
        runtime_handle=runtime_state.runtime_handle,
        setup_status=runtime_state.setup_status,
        gateway_setup_status=derived_status,
    )
    _record_runtime_setup_state(
        record.agent_id,
        setup_status=updated_state.setup_status,
        gateway_setup_status=updated_state.gateway_setup_status,
    )
    return updated_state


def _require_shared_infra_ready(agent_id: str) -> None:
    bootstrap = SQLiteState(get_state_db_path()).get_infra_status("bootstrap")
    if bootstrap is None or bootstrap["status"] != "ready":
        raise _agent_runtime_unavailable_error(agent_id, "shared infra setup is not complete")


def _require_agent_setup_complete(
    record: AgentRecord,
    runtime_state: RuntimeState | None,
    *,
    error_factory: Callable[[str, str], ValueError] = _agent_runtime_unavailable_error,
) -> RuntimeState:
    if runtime_state is None or runtime_state.setup_status != "complete":
        raise error_factory(record.agent_id, "agent setup is not complete")
    return runtime_state


def _require_agent_gateway_setup_complete(
    record: AgentRecord,
    runtime_state: RuntimeState | None,
    *,
    error_factory: Callable[[str, str], ValueError] = _agent_runtime_unavailable_error,
) -> RuntimeState:
    if runtime_state is None or not _is_gateway_start_ready(runtime_state.gateway_setup_status):
        raise error_factory(
            record.agent_id,
            f"agent gateway setup is not complete; run maia agent setup-gateway {record.name}",
        )
    return runtime_state


def _sync_registry_status_from_runtime_state(
    record: AgentRecord,
    runtime_state: RuntimeState,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> AgentRecord:
    expected_status = (
        AgentStatus.RUNNING
        if runtime_state.runtime_status in _ACTIVE_RUNTIME_STATUSES
        else AgentStatus.STOPPED
    )
    if record.status is expected_status:
        return record
    updated = registry.set_status(record.agent_id, expected_status)
    storage.save(registry_path, registry)
    return updated


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
            source_registry_path=get_state_db_path(),
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
        source_registry_path=get_state_db_path(),
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
    print("warning import apply will reset runtime/setup state for all local agents before replacing the snapshot")
    if preview["current_agents"] > 0 or preview["team_details"] != "-":
        print("warning import will overwrite the current Maia registry with the snapshot state")
        print("warning removed agents and changed fields will be replaced by snapshot values")
        if not args.yes:
            if not _confirm_import_overwrite():
                print("cancelled import")
                return 1
    storage.save(registry_path, incoming_registry)
    RuntimeStateStorage().save(get_state_db_path(), {})
    if effective_incoming_team_metadata != current_team_metadata:
        save_team_metadata(get_team_metadata_path(), effective_incoming_team_metadata)
    print(
        f"imported source={_format_preview_value(str(source_path))} "
        f"registry={_format_preview_value(str(import_path))} "
        f"agents={len(incoming_registry.list())}"
    )
    return 0


def _print_import_preview(preview: dict[str, object], source_path: Path, import_path: Path) -> None:
    print("warning import preview: applying this snapshot will reset runtime/setup state for all local agents")
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


def _handle_workspace_show(args: argparse.Namespace, registry) -> int:
    record = registry.get(args.agent_id)
    _resolve_configured_runtime_spec(
        record,
        error_factory=_workspace_context_unavailable_error,
    )
    print(
        "workspace "
        f"agent_id={record.agent_id} "
        + " ".join(_format_workspace_context_fields(record))
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


def _speaking_style_display(value: str | SpeakingStyle) -> str:
    style = value if isinstance(value, SpeakingStyle) else SpeakingStyle(value)
    return style.value.capitalize()


def _resolve_speaking_style(value: str) -> SpeakingStyle:
    normalized = _normalize_optional_cli_text(value, field_name="agent speaking style").lower()
    aliases = {
        "1": SpeakingStyle.RESPECTFUL,
        "respectful": SpeakingStyle.RESPECTFUL,
        "respect": SpeakingStyle.RESPECTFUL,
        "2": SpeakingStyle.CASUAL,
        "casual": SpeakingStyle.CASUAL,
        "friendly": SpeakingStyle.CASUAL,
        "3": SpeakingStyle.CUSTOM,
        "custom": SpeakingStyle.CUSTOM,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError("Agent speaking style must be Respectful, Casual, or Custom") from exc


def _prompt_speaking_style() -> tuple[SpeakingStyle, str]:
    print("Speaking style:")
    print("Respectful / Casual / Custom [default: Respectful]")
    try:
        raw_value = input()
    except EOFError:
        raw_value = ""
    if not raw_value.strip():
        return SpeakingStyle.RESPECTFUL, ""
    style = _resolve_speaking_style(raw_value)
    if style is not SpeakingStyle.CUSTOM:
        return style, ""
    details = _prompt_required_text(
        "Custom speaking style",
        field_name="custom speaking style",
    )
    return style, details


def _normalize_speaking_style_details(raw_value: str | None, *, style: SpeakingStyle) -> str:
    if style is not SpeakingStyle.CUSTOM:
        if raw_value is not None:
            raise ValueError("--speaking-style-details requires --speaking-style Custom")
        return ""
    if raw_value is None:
        raise ValueError("Custom speaking style requires --speaking-style-details")
    return _normalize_optional_cli_text(
        raw_value,
        field_name="agent speaking style details",
    )


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
    if resource == "handoff":
        return getattr(args, "handoff_command", None)
    if resource == "team":
        return getattr(args, "team_command", None)
    if resource == "workspace":
        return getattr(args, "workspace_command", None)
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
    stored_runtime_state = _load_runtime_state_for_agent(record)
    try:
        runtime_state = _resolve_runtime_state_for_status(record, runtime_adapter)
    except ValueError as exc:
        if _is_stale_runtime_error(exc):
            _clear_stale_runtime_state(args.agent_id, storage, registry_path, registry)
            raise _stale_runtime_state_cleared_error(args.agent_id) from exc
        raise
    record = _sync_registry_status_from_runtime_state(record, runtime_state, storage, registry_path, registry)
    print(_format_agent_status(record, runtime_state, stored_runtime_state=runtime_state))
    return 0


def _handle_agent_start(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> int:
    record = registry.get(args.agent_id)
    updated, runtime = _start_agent_runtime(
        record,
        storage,
        registry_path,
        registry,
        runtime_adapter,
    )
    print(
        f"updated agent_id={updated.agent_id} status={updated.status.value} "
        f"runtime_status={runtime.runtime_status.value} "
        f"runtime_handle={_format_preview_value(runtime.runtime_handle)}"
    )
    return 0


def _start_agent_runtime(
    record: AgentRecord,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
    *,
    stored_runtime_state: RuntimeState | None = None,
) -> tuple[AgentRecord, RuntimeState]:
    if stored_runtime_state is None:
        stored_runtime_state = _load_runtime_state_for_agent(record)
    if stored_runtime_state is not None and stored_runtime_state.runtime_status not in _ACTIVE_RUNTIME_STATUSES:
        record = _sync_registry_status_from_runtime_state(
            record,
            stored_runtime_state,
            storage,
            registry_path,
            registry,
        )
    if record.status is AgentStatus.RUNNING:
        raise _agent_already_running_error(record.agent_id)
    _resolve_configured_runtime_spec(
        record,
        error_factory=_agent_runtime_unavailable_error,
    )
    _require_shared_infra_ready(record.agent_id)
    _require_agent_setup_complete(record, stored_runtime_state)
    _require_agent_gateway_setup_complete(record, stored_runtime_state)
    ensure_agent_keryx_skill_installed(record.agent_id)
    if stored_runtime_state is not None and stored_runtime_state.runtime_status in _ACTIVE_RUNTIME_STATUSES:
        raise _agent_runtime_already_active_error(record.agent_id)
    start_result = runtime_adapter.start(RuntimeStartRequest(agent=record))
    _record_runtime_setup_state(
        record.agent_id,
        setup_status=(None if stored_runtime_state is None else stored_runtime_state.setup_status),
        gateway_setup_status=(None if stored_runtime_state is None else stored_runtime_state.gateway_setup_status),
    )
    registry.set_has_started(record.agent_id, True)
    updated = registry.set_status(record.agent_id, AgentStatus.RUNNING)
    storage.save(registry_path, registry)
    return updated, start_result.runtime


def _handle_agent_stop(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
    runtime_adapter: DockerRuntimeAdapter,
) -> int:
    record = registry.get(args.agent_id)
    stored_runtime_state = _load_runtime_state_for_agent(record)
    if stored_runtime_state is None or stored_runtime_state.runtime_status not in _ACTIVE_RUNTIME_STATUSES:
        raise _agent_runtime_not_running_error(args.agent_id)
    try:
        stop_result = runtime_adapter.stop(RuntimeStopRequest(agent_id=args.agent_id))
    except ValueError as exc:
        if _is_stale_runtime_error(exc):
            _clear_stale_runtime_state(args.agent_id, storage, registry_path, registry)
            raise _stale_runtime_state_cleared_error(args.agent_id) from exc
        raise
    _record_runtime_setup_state(
        args.agent_id,
        setup_status=(None if stored_runtime_state is None else stored_runtime_state.setup_status),
        gateway_setup_status=(None if stored_runtime_state is None else stored_runtime_state.gateway_setup_status),
    )
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
    record = registry.get(args.agent_id)
    stored_runtime_state = _load_runtime_state_for_agent(record)
    _require_agent_setup_complete(
        record,
        stored_runtime_state,
        error_factory=_agent_logs_unavailable_error,
    )
    if stored_runtime_state.runtime_status not in _ACTIVE_RUNTIME_STATUSES:
        raise _agent_runtime_not_running_error(args.agent_id)
    try:
        logs_result = runtime_adapter.logs(
            RuntimeLogsRequest(agent_id=args.agent_id, tail_lines=args.tail_lines)
        )
    except ValueError as exc:
        if _is_stale_runtime_error(exc):
            _clear_stale_runtime_state(args.agent_id, storage, registry_path, registry)
            raise _stale_runtime_state_cleared_error(args.agent_id) from exc
        raise
    _record_runtime_setup_state(
        args.agent_id,
        setup_status=(None if stored_runtime_state is None else stored_runtime_state.setup_status),
        gateway_setup_status=(None if stored_runtime_state is None else stored_runtime_state.gateway_setup_status),
    )
    record = _sync_registry_status_from_runtime_state(
        record,
        logs_result.runtime,
        storage,
        registry_path,
        registry,
    )
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
    stored_runtime_state = _load_runtime_state_for_agent(record)
    if stored_runtime_state is not None:
        if stored_runtime_state.runtime_handle is None:
            return stored_runtime_state
        observed = runtime_adapter.status(RuntimeStatusRequest(agent_id=record.agent_id)).runtime
        return RuntimeState(
            agent_id=observed.agent_id,
            runtime_status=observed.runtime_status,
            runtime_handle=observed.runtime_handle,
            setup_status=(observed.setup_status or stored_runtime_state.setup_status),
            gateway_setup_status=(
                observed.gateway_setup_status or stored_runtime_state.gateway_setup_status
            ),
        )
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
    state_storage = RuntimeStateStorage()
    states = state_storage.load(get_state_db_path())
    existing = states.get(agent_id)
    if existing is None:
        state_storage.remove(get_state_db_path(), agent_id)
    else:
        states[agent_id] = RuntimeState(
            agent_id=agent_id,
            runtime_status=RuntimeStatus.STOPPED,
            runtime_handle=None,
            setup_status=existing.setup_status,
            gateway_setup_status=existing.gateway_setup_status,
        )
        state_storage.save(get_state_db_path(), states)
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
    if "speaking_style" in updates:
        updated = registry.set_speaking_style(
            args.agent_id,
            speaking_style=str(updates["speaking_style"]),
            speaking_style_details=str(updates.get("speaking_style_details", "")),
        )
    profile_updates = {
        key: updates[key]
        for key in ("role", "model", "tags")
        if key in updates
    }
    if profile_updates:
        updated = registry.set_profile_metadata(args.agent_id, **profile_updates)
    if "runtime_spec" in updates:
        updated = registry.set_runtime_spec(args.agent_id, updates["runtime_spec"])
    hermes_home = get_agent_hermes_home(args.agent_id)
    if hermes_home.exists():
        _sync_agent_hermes_soul(updated, hermes_home=hermes_home)
    storage.save(registry_path, registry)
    print(_format_agent_tune_result(updated, updates))
    return 0


def _handle_agent_lifecycle(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    record = registry.get(args.agent_id)
    if args.agent_command == "archive" and _agent_has_active_runtime(record.agent_id):
        raise ValueError(f"Can't archive agent {args.agent_id!r} while its runtime is active; stop it first")
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
    RuntimeStateStorage().remove(get_state_db_path(), args.agent_id)
    _remove_agent_hermes_home(args.agent_id)
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


def _handle_agent_archive_all(
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    records = registry.list()
    active_agent_ids = [record.agent_id for record in records if _agent_has_active_runtime(record.agent_id)]
    if active_agent_ids:
        raise ValueError(
            f"Can't archive all agents while runtimes are active: {','.join(active_agent_ids)}. Stop them first"
        )
    updated_count = 0
    for record in records:
        if record.status is AgentStatus.ARCHIVED:
            continue
        registry.set_status(record.agent_id, AgentStatus.ARCHIVED)
        updated_count += 1
    storage.save(registry_path, registry)
    print(f"updated agents={updated_count} status=archived")
    return 0


def _handle_agent_purge_all(
    args: argparse.Namespace,
    storage: JsonRegistryStorage,
    registry_path: str,
    registry,
) -> int:
    if not args.yes:
        raise ValueError("maia agent purge-all requires --yes")
    records = registry.list()
    non_archived = [record.agent_id for record in records if record.status is not AgentStatus.ARCHIVED]
    if non_archived:
        raise ValueError(
            f"Can't purge all agents unless every remaining agent is archived: {','.join(non_archived)}"
        )
    for record in records:
        RuntimeStateStorage().remove(get_state_db_path(), record.agent_id)
        _remove_agent_hermes_home(record.agent_id)
        registry.remove(record.agent_id)
    storage.save(registry_path, registry)
    team_metadata_path = get_team_metadata_path()
    team_metadata = load_team_metadata(team_metadata_path)
    if team_metadata.default_agent_id:
        save_team_metadata(
            team_metadata_path,
            TeamMetadata(
                team_name=team_metadata.team_name,
                team_description=team_metadata.team_description,
                team_tags=list(team_metadata.team_tags),
                default_agent_id="",
            ),
        )
    print(f"purged agents={len(records)}")
    return 0


def _agent_has_active_runtime(agent_id: str) -> bool:
    runtime_state = RuntimeStateStorage().load(get_state_db_path()).get(agent_id)
    return runtime_state is not None and runtime_state.runtime_status in _ACTIVE_RUNTIME_STATUSES


def _render_agent_hermes_soul(record: AgentRecord) -> str:
    lines = [
        f"You are {record.name}.",
        f'Call the user "{record.call_sign}".',
        f"Use a {record.speaking_style.value} speaking style.",
    ]
    if record.speaking_style is SpeakingStyle.CUSTOM and record.speaking_style_details:
        lines.append(f"Custom speaking style details: {record.speaking_style_details}")
    if record.persona:
        lines.append(f"Persona: {record.persona}")
    return "\n".join(lines) + "\n"


def _sync_agent_hermes_soul(
    record: AgentRecord,
    *,
    hermes_home: Path,
    create_home: bool = False,
) -> None:
    if not create_home and not hermes_home.exists():
        return
    hermes_home.mkdir(parents=True, exist_ok=True)
    (hermes_home / "SOUL.md").write_text(_render_agent_hermes_soul(record), encoding="utf-8")


def _remove_agent_hermes_home(agent_id: str) -> None:
    hermes_home = get_agent_hermes_home(agent_id)
    if not hermes_home.exists():
        return
    for path in sorted(hermes_home.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        else:
            path.rmdir()
    hermes_home.rmdir()


def _format_record(record: AgentRecord, *, runtime_state: RuntimeState | None = None) -> str:
    return (
        f"agent_id={record.agent_id} "
        f"name={_format_preview_value(record.name)} "
        f"call_sign={_format_preview_value(record.call_sign)} "
        f"status={_derive_operator_status(record, runtime_state=runtime_state)}"
    )


def _derive_operator_status(record: AgentRecord, runtime_state: RuntimeState | None = None) -> str:
    if record.status is AgentStatus.ARCHIVED:
        return AgentStatus.ARCHIVED.value
    if record.status is AgentStatus.RUNNING:
        return AgentStatus.RUNNING.value
    if (
        _derive_setup_state(runtime_state) == "complete"
        and _is_gateway_start_ready(_derive_gateway_setup_state(runtime_state))
    ):
        return AgentStatus.STOPPED.value if record.has_started else "ready"
    return AgentSetupStatus.NOT_CONFIGURED.value


def _resolve_agent_reference(registry, value: str) -> str:
    try:
        return registry.get(value).agent_id
    except LookupError:
        matching = [record for record in registry.list() if record.name == value]
        if len(matching) == 1:
            return matching[0].agent_id
        if len(matching) > 1:
            raise ValueError(
                f"Agent name {value!r} matches multiple agents. Use agent_id instead"
            )
        raise


def _format_agent_status(
    record: AgentRecord,
    runtime_state: RuntimeState,
    *,
    stored_runtime_state: RuntimeState | None = None,
) -> str:
    setup_state = _derive_setup_state(stored_runtime_state)
    return (
        f"agent_id={record.agent_id} "
        f"name={_format_preview_value(record.name)} "
        f"call_sign={_format_preview_value(record.call_sign)} "
        f"status={_derive_operator_status(record, runtime_state=stored_runtime_state)} "
        f"setup={setup_state} "
        f"runtime={runtime_state.runtime_status.value} "
        f"persona={_format_preview_value(record.persona)}"
    )


def _derive_setup_state(runtime_state: RuntimeState | None) -> str:
    if runtime_state is None or runtime_state.setup_status is None:
        return "not-started"
    return runtime_state.setup_status


def _derive_gateway_setup_state(runtime_state: RuntimeState | None) -> str:
    if runtime_state is None or runtime_state.gateway_setup_status is None:
        return "not-started"
    return runtime_state.gateway_setup_status


def _gateway_setup_status_rank(status: str | None) -> int:
    return {
        None: 0,
        "not-started": 0,
        "incomplete": 1,
        "token-only": 2,
        "complete": 3,
    }.get(status, 0)


def _is_gateway_start_ready(status: str | None) -> bool:
    return status in {"complete", "token-only"}


def _is_default_destination_ready(status: str | None) -> bool:
    return status == "complete"


def _format_agent_tune_result(record: AgentRecord, updates: dict[str, object]) -> str:
    parts = [f"updated agent_id={record.agent_id}"]
    if "persona" in updates:
        parts.append(f"persona={_format_preview_value(record.persona)}")
    if "speaking_style" in updates:
        parts.append(f"speaking_style={_speaking_style_display(record.speaking_style)}")
        if record.speaking_style is SpeakingStyle.CUSTOM and record.speaking_style_details:
            parts.append(
                f"speaking_style_details={_format_preview_value(record.speaking_style_details)}"
            )
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
    if args.speaking_style is not None:
        style = _resolve_speaking_style(args.speaking_style)
        updates["speaking_style"] = style.value
        updates["speaking_style_details"] = _normalize_speaking_style_details(
            args.speaking_style_details,
            style=style,
        )
    elif args.speaking_style_details is not None:
        raise ValueError("--speaking-style-details requires --speaking-style Custom")
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
