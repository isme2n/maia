# Task 137 - Legacy thread purge and Keryx thread redefinition

## Goal
Purge the legacy Maia thread/collaboration model first, then reintroduce `thread` as the public and operator-facing name for the Keryx collaboration object. After this task, `thread` must mean only the Keryx collaboration unit, while Hermes keeps its own existing session concept unchanged.

## Non-goals
- changing Hermes runtime/session semantics
- introducing a third naming layer such as `chat` and `thread` at the same time
- keeping legacy thread storage/models around as compatibility aliases
- reopening `/call` or old collaboration compatibility
- redesigning Keryx core resources beyond the naming/visibility cutover needed here

## Allowed files
- `docs/tasks/137-keryx-thread-redefinition-after-legacy-purge.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/keryx_models.py`
- `src/maia/keryx_storage.py`
- `src/maia/keryx_service.py`
- `src/maia/keryx_server.py`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/agent_context.py`
- `src/maia/collaboration_storage.py`
- `src/maia/message_model.py`
- `src/maia/handoff_model.py`
- `src/maia/sqlite_state.py`
- `src/maia/app_state.py`
- `tests/test_agent_context.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_keryx_service.py`
- `tests/test_keryx_server.py`
- `tests/test_sqlite_state.py`
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/2026-04-20-keryx-migration-closeout.md`

## Required contract decisions
- `thread` is the Keryx collaboration object name on the Maia public surface.
- `thread_id` is the public/operator identifier for that Keryx collaboration object.
- Hermes keeps its own `session` wording untouched.
- Maia docs/help must never imply that a Keryx thread is the same thing as a Hermes session.
- If an internal Keryx API/storage field still uses `session_id`, it must be hidden behind a clear Maia adapter boundary or migrated consistently; mixed public wording is not allowed.

## Legacy purge targets
- CLI handlers that read/write `CollaborationStorage` / `ThreadRecord` / legacy `HandoffRecord` for `thread` commands
- `agent_context.py` thread-context loading that reads `collaboration_threads` / `collaboration_messages` / `collaboration_handoffs`
- legacy SQLite collaboration tables and payload helpers if they are no longer needed after Keryx thread cutover
- tests that prove thread behavior using `ThreadRecord`, `MessageRecord`, `HandoffRecord`, or `CollaborationStorage` fixtures instead of Keryx fixtures
- docs/help text that still describes thread as a leftover legacy visibility concept rather than the Keryx collaboration root

## Acceptance criteria
- [x] there is only one active meaning of `thread` in Maia: the Keryx collaboration object.
- [x] `maia thread list/show` reads real Keryx-backed data and can surface the live flow already proven via `keryx_sessions/messages/handoffs`.
- [x] no operator-visible wording suggests `thread` is legacy storage, a compatibility alias, or a Hermes session.
- [x] runtime/agent context loading no longer depends on legacy `collaboration_threads/messages/handoffs` tables for active collaboration flow.
- [x] tests for thread visibility use Keryx-backed fixtures/state rather than legacy thread records.
- [x] docs/help/PRD/closeout notes all describe the same contract: Hermes session stays local; Keryx thread is the shared collaboration object.
- [x] targeted validation passes.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_agent_context.py tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_keryx_service.py tests/test_keryx_server.py tests/test_sqlite_state.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia thread --help`
- `cd /home/asle/maia && HOME=/tmp/tmp.XMgdLzcroJ PYTHONPATH=src python3 -m maia thread show sess01`
- `cd /home/asle/maia && HOME=/tmp/tmp.XMgdLzcroJ PYTHONPATH=src python3 -m maia handoff show handoff01`

## Forbidden changes
- keeping legacy thread storage as an active fallback for `maia thread`
- using bare `session` on the Maia public surface for Keryx collaboration objects
- changing Hermes behavior or requiring Hermes session renames
- broad repo cleanup outside the allowed files
