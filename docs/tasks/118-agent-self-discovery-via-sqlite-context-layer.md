# Task 118 — agent self-discovery via SQLite context layer

## Goal
- Let a running Maia agent discover who else exists, what role/status they have, and what thread/handoff context matters right now without relying on the operator to restate that information in every message.
- Keep SQLite as the single-host source of truth, but expose it to runtime workers through a small read-only context layer rather than raw ad-hoc SQL in prompts.

## Root problem
- Current runtime containers only receive `HERMES_HOME`, `MAIA_AGENT_ID`, `MAIA_AGENT_NAME`, and `MAIA_BROKER_URL`.
- Current worker prompt only includes per-message fields like `thread_id`, `from_agent`, `to_agent`, and `message_body`.
- Result: a running agent can reply to the current sender, but it cannot independently discover:
  - which other agents exist
  - who is currently running
  - what roles/call-signs exist in the team
  - what recent handoffs apply to the current thread
  - whether a newly added agent exists unless the operator explicitly says so

## Recommended design direction
- Do not switch Maia to PostgreSQL just for this.
- Do not make runtime prompts or LLM tools generate raw SQL against Maia tables.
- Keep SQLite as the source of truth for one-host Maia state.
- Mount the Maia state DB into runtime containers read-only and inject a path env var such as `MAIA_STATE_DB_PATH=/maia/control/state.db`.
- Add a dedicated Maia-side read-only context helper/module that loads:
  - team roster summary
  - current thread participant context
  - recent thread-relevant handoffs
  - runtime/setup state for known agents
- Have the worker automatically include this derived context in the Hermes prompt before asking for a reply.
- Treat queue/broker event streams as optional freshness signals later, not the primary source of roster truth.

## Why this is the best v1 path
- Preserves a lightweight single-host control-plane architecture.
- Supports dynamic agent addition without operator re-explaining the roster.
- Avoids tight prompt-level coupling to raw SQLite schema.
- Leaves room to swap SQLite for a server/API later without changing the worker-facing context contract.

## Non-goals
- Replace SQLite with PostgreSQL
- Add a new public Maia operator command just for agent self-discovery
- Turn RabbitMQ into the source of truth for roster/state snapshots
- Give LLM prompts direct arbitrary SQL capabilities
- Implement autonomous workspace/file sync or full handoff file ingestion

## Allowed files
- `src/maia/docker_runtime_adapter.py`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/sqlite_state.py`
- `src/maia/app_state.py`
- `src/maia/agent_model.py`
- `src/maia/runtime_adapter.py`
- `src/maia/message_model.py`
- `src/maia/agent_context.py` (new)
- `tests/test_docker_runtime_adapter.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_sqlite_state.py`
- `tests/test_agent_context.py` (new)
- `docs/tasks/118-agent-self-discovery-via-sqlite-context-layer.md`
- `docs/plans/phase17-agent-self-discovery-and-runtime-context.md`

## Acceptance criteria
- [x] Runtime containers receive a read-only Maia state DB path automatically
- [x] The worker can load a roster summary from SQLite without operator message help
- [x] The worker can load current thread participants and recent handoffs for the active thread
- [x] The worker prompt includes Maia-derived context before the incoming message body
- [x] Newly added agents become discoverable via the context layer without changing operator prompts
- [x] The context layer opens SQLite read-only and fails with a clear operator-facing error when the DB is missing/unreadable
- [x] Targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_agent_context.py tests/test_hermes_runtime_worker.py tests/test_docker_runtime_adapter.py tests/test_sqlite_state.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- Broad CLI/help/README product-story churn
- Requiring operators to send manual roster/context reminders in the happy path
- Queue-only roster discovery without a SQLite snapshot source of truth
- Prompt-level raw SQL generation or exposing arbitrary SQL to the model
- Broad multi-host/database migration work

## Design notes to preserve
- Use SQLite URI read-only mode (`mode=ro`) in the context helper when reading the mounted DB.
- Prefer mounting only the state DB read-only first; do not mount the entire Maia home writable into agent runtimes.
- The context helper should return stable, high-level Python structures/prompts, not raw table rows.
- First implementation should be snapshot-driven from SQLite. Queue/event freshness can come in a later task if needed.

## Closeout evidence
- Targeted validation passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py tests/test_agent_context.py tests/test_docker_runtime_adapter.py tests/test_sqlite_state.py tests/test_cli_runtime.py`
  - Result: `95 passed`
- Scoped review passed:
  - Verdict: `approve`
  - Scope: `src/maia/agent_context.py`, `src/maia/docker_runtime_adapter.py`, `src/maia/hermes_runtime_worker.py`, associated tests, and Task 118/Phase 17 docs
