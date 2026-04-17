# Phase 17 Agent Self-Discovery and Runtime Context Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia runtime agents should discover the current team roster and relevant collaboration context themselves, without requiring the operator to manually restate who exists or what handoff/thread state matters.

**Architecture:** Keep SQLite as the single-host source of truth and RabbitMQ as the live delivery plane. Inject a read-only SQLite DB path into runtime containers, add a Maia-owned context helper that performs constrained read-only queries, and have the runtime worker automatically compose roster/thread/handoff context into the Hermes prompt. Do not expose raw SQL or make broker queues the roster source of truth.

**Tech Stack:** Python stdlib (`sqlite3`, dataclasses), existing Maia SQLite state, Docker runtime adapter, Hermes runtime worker, pytest.

---

## Executive recommendation

### Best-practice answer
For Maia as it exists today, the best design is:
1. SQLite remains the source of truth for roster/state.
2. RabbitMQ remains the live message delivery plane.
3. Runtime agents get a read-only Maia context layer, not arbitrary SQL access.
4. Worker prompts automatically include team/thread/handoff context derived from SQLite.

### Why not queue-only
Queue messages are good for new deliveries and change notifications, but poor as the primary source for:
- full roster snapshots
- current runtime/setup state
- current thread state after restarts
- recent handoff lookup by thread

### Why not raw SQL in prompts
Prompt-visible SQL or “query whatever you want” creates tight schema coupling, weak safety boundaries, and brittle prompt contracts. The better pattern is a Maia-owned helper that returns high-level structures.

### Why not PostgreSQL yet
For Maia’s current single-host control-plane stage, PostgreSQL adds operational weight without solving the immediate design problem better than read-only SQLite + a clean helper.

---

## Public contract to preserve
- Operators should not need to tell an agent who the other agents are on every request.
- Newly added agents should become discoverable through Maia’s state layer.
- Maia remains the control plane; running agents remain the conversation actors.
- Queue messages carry live work; SQLite answers “who exists and what is the current state?”

---

## Proposed runtime contract

### Runtime env additions
Add one new reserved env var to runtime containers:
- `MAIA_STATE_DB_PATH=/maia/control/state.db`

Keep existing vars:
- `HERMES_HOME=/maia/hermes`
- `MAIA_AGENT_ID=<id>`
- `MAIA_AGENT_NAME=<name>`
- `MAIA_BROKER_URL=<url>`

### Runtime mount addition
Mount Maia state DB read-only into the container, for example:
- host: `<maia_home>/state.db`
- container: `/maia/control/state.db:ro`

### Reserved-env ownership rule
Treat `MAIA_STATE_DB_PATH`, `MAIA_AGENT_ID`, and `MAIA_AGENT_NAME` as Maia-owned env keys. If a runtime spec tries to override them, Maia wins.

Keep the existing `MAIA_BROKER_URL` behavior from Task 115: an explicit runtime-spec broker URL may still override the default when an operator intentionally points an agent at a different broker.

---

## Context helper contract
Create a new internal module:
- `src/maia/agent_context.py`

Recommended public functions inside that module:
- `load_team_roster(state_db_path: str | Path) -> list[AgentRosterEntry]`
- `load_thread_context(state_db_path: str | Path, thread_id: str) -> ThreadContext | None`
- `load_recent_handoffs(state_db_path: str | Path, *, thread_id: str, limit: int = 3) -> list[HandoffContext]`
- `build_runtime_context(state_db_path: str | Path, *, agent_id: str, incoming_message: MessageRecord) -> RuntimeContext`
- `format_runtime_context_for_prompt(context: RuntimeContext) -> str`

Recommended dataclasses:
- `AgentRosterEntry`
  - `agent_id`
  - `name`
  - `role`
  - `call_sign`
  - `status`
  - `setup_status`
  - `runtime_status`
- `ThreadContext`
  - `thread_id`
  - `topic`
  - `participants`
  - `pending_on`
  - `recent_message_ids`
- `HandoffContext`
  - `handoff_id`
  - `from_agent`
  - `to_agent`
  - `kind`
  - `summary`
  - `location`
  - `created_at`
- `RuntimeContext`
  - `self_agent`
  - `team_roster`
  - `thread_context`
  - `recent_handoffs`

### SQLite reading rules
- Open the DB read-only using URI mode.
- Fail fast with a clear `ValueError` if the DB path is missing or unreadable.
- Decode stored JSON payloads using the existing serialized records, not ad-hoc custom schemas.
- Prefer loading from `payload` columns and then normalizing into dataclasses.

### Snapshot scope rule
First cut should include only what the worker needs for self-discovery:
- team roster summary
- active thread context
- recent handoffs for the thread
Do not add full cross-thread analytics, free-form history search, or workspace file reads in this task.

---

## Worker prompt contract
Update `src/maia/hermes_runtime_worker.py` so `build_prompt()` prepends a Maia context section before the incoming message body.

Recommended prompt shape:

```text
You are Maia agent Reviewer (agent_id=reviewer).

Current Maia context:
- Known team roster:
  - planner (agent_id=..., role=planner, runtime=running)
  - reviewer (agent_id=..., role=reviewer, runtime=running)
- Active thread:
  - thread_id=...
  - topic=...
  - participants=planner, reviewer
  - pending_on=reviewer
- Recent handoffs for this thread:
  - handoff_id=... type=file from=planner to=reviewer summary=... location=...

Reply as this agent to the incoming Maia thread message below.
Keep the answer direct and useful. Return only the reply body.
...
```

### Fallback behavior
If `MAIA_STATE_DB_PATH` is unset or unreadable:
- do not crash with a raw traceback
- raise a clear worker error such as:
  - `Maia runtime context is unavailable: state DB path is missing`
  - `Maia runtime context is unavailable: state DB at /maia/control/state.db is unreadable`

---

## Recommended implementation order

### Task 1: Add read-only SQLite context helper

**Objective:** Create a dedicated Maia-owned helper for roster/thread/handoff reads.

**Files:**
- Create: `src/maia/agent_context.py`
- Test: `tests/test_agent_context.py`
- Optional support: `src/maia/sqlite_state.py`

**Step 1: Write failing tests**
Add tests that prove:
- roster can be read from a seeded SQLite DB
- thread context can be reconstructed from collaboration tables
- recent handoffs are returned newest-first
- missing/unreadable DB paths raise clear `ValueError`s

**Step 2: Run tests to verify failure**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_agent_context.py`
Expected:
- failing import / missing helper failures

**Step 3: Implement minimal helper**
- Read JSON payloads from `agents`, `runtime_states`, `collaboration_threads`, and `collaboration_handoffs`
- Normalize into dataclasses
- Use `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` for reads

**Step 4: Run tests to verify pass**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_agent_context.py`
Expected:
- pass

**Step 5: Commit**
```bash
git add src/maia/agent_context.py tests/test_agent_context.py
git commit -m "feat: add read-only maia agent context helper"
```

### Task 2: Mount state DB read-only into runtime containers

**Objective:** Make the SQLite source of truth available inside runtime containers safely.

**Files:**
- Modify: `src/maia/docker_runtime_adapter.py`
- Modify: `src/maia/app_state.py` if a helper path function is useful
- Test: `tests/test_docker_runtime_adapter.py`

**Step 1: Write failing tests**
Add tests that assert `docker run` now includes:
- a read-only bind mount for `state.db`
- `MAIA_STATE_DB_PATH=/maia/control/state.db`
- reserved-env precedence over user-supplied overrides

**Step 2: Run tests to verify failure**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_docker_runtime_adapter.py`
Expected:
- missing mount/env assertions fail

**Step 3: Implement minimal adapter change**
- Bind-mount the state DB file to `/maia/control/state.db:ro`
- Inject `MAIA_STATE_DB_PATH=/maia/control/state.db`
- Preserve current broker/id/name injection behavior

**Step 4: Run tests to verify pass**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_docker_runtime_adapter.py`
Expected:
- pass

**Step 5: Commit**
```bash
git add src/maia/docker_runtime_adapter.py tests/test_docker_runtime_adapter.py
git commit -m "feat: inject read-only maia state db into runtimes"
```

### Task 3: Inject roster/thread/handoff context into worker prompts

**Objective:** Make the runtime worker use the context helper automatically before asking Hermes for a reply.

**Files:**
- Modify: `src/maia/hermes_runtime_worker.py`
- Test: `tests/test_hermes_runtime_worker.py`
- Reuse: `src/maia/agent_context.py`

**Step 1: Write failing tests**
Add tests that prove:
- built prompts include a roster section when `MAIA_STATE_DB_PATH` is set
- built prompts include thread topic/participants and recent handoff summaries
- worker failure when context DB is missing is clear/operator-facing
- newly added agent records appear in prompt context without changing the message body

**Step 2: Run tests to verify failure**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py`
Expected:
- prompt-content assertions fail

**Step 3: Implement minimal prompt enrichment**
- Extend `WorkerConfig` with `state_db_path`
- Load it from `MAIA_STATE_DB_PATH`
- Build a compact, deterministic Maia context section
- Keep output body contract unchanged: Hermes still returns only the reply body

**Step 4: Run tests to verify pass**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py`
Expected:
- pass

**Step 5: Commit**
```bash
git add src/maia/hermes_runtime_worker.py tests/test_hermes_runtime_worker.py
git commit -m "feat: inject maia roster context into worker prompts"
```

### Task 4: End-to-end regression and hardening

**Objective:** Lock the self-discovery contract with focused runtime tests.

**Files:**
- Modify: `tests/test_cli_runtime.py` (only if needed for runtime env/mount regression)
- Modify: `tests/test_sqlite_state.py`
- Modify: `tests/test_agent_context.py`
- Modify: `docs/tasks/118-agent-self-discovery-via-sqlite-context-layer.md`

**Step 1: Add integration-style regression tests**
Cover:
- freshly added third agent appears in roster context for a subsequent worker prompt
- missing DB mount/path produces a clear failure
- read-only DB path works without changing current broker reply semantics

**Step 2: Run targeted tests**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_agent_context.py tests/test_hermes_runtime_worker.py tests/test_docker_runtime_adapter.py tests/test_sqlite_state.py`
Expected:
- all pass

**Step 3: Broader runtime regression**
Run:
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_docker_runtime_adapter.py`
Expected:
- all pass

**Step 4: Close task doc checkboxes**
Update `docs/tasks/118-agent-self-discovery-via-sqlite-context-layer.md` once validation is green.

**Step 5: Commit**
```bash
git add docs/tasks/118-agent-self-discovery-via-sqlite-context-layer.md tests/test_sqlite_state.py tests/test_cli_runtime.py
git commit -m "test: lock maia agent self-discovery context flow"
```

---

## Rollout notes

### v1 scope
Implement SQLite snapshot-based self-discovery first.
Do not block this task on queue-event subscriptions.

### v1.1 optional upgrade
If freshness becomes a problem, add a broker-side control event stream later:
- `agent.created`
- `agent.updated`
- `agent.started`
- `agent.stopped`
- `handoff.added`
- `thread.updated`

But even then:
- queue = delta/event signal
- SQLite = authoritative snapshot

### Future migration safety
If Maia later moves to PostgreSQL or a control-plane API:
- keep `agent_context.py` as the stable contract
- swap its backend implementation
- leave worker prompt logic unchanged

---

## Pitfalls to avoid
- Do not expose raw SQL strings to the LLM/runtime prompt.
- Do not mount the whole Maia home writable into worker containers.
- Do not make the worker depend on queue history to reconstruct the roster.
- Do not over-expand the prompt with full message history across all threads.
- Do not let runtime spec env override Maia-owned identity/state env vars.

---

## Verification checklist
- [ ] `MAIA_STATE_DB_PATH` is injected automatically
- [ ] runtime containers receive the DB file read-only
- [ ] worker prompt includes roster/thread/handoff context
- [ ] newly added agents become visible without operator restatement
- [ ] missing/unreadable DB path fails clearly
- [ ] targeted tests pass

---

## Recommended next execution move
Implement Task 118 first, then run a fresh-home live probe where:
1. create planner/reviewer
2. start reviewer
3. add a third agent after reviewer is already running
4. send a new request to reviewer
5. verify reviewer’s reply shows awareness of the new roster state without the operator spelling it out in the message
