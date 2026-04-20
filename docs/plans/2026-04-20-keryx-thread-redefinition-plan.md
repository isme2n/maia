# Keryx Thread Redefinition Implementation Plan

> For Hermes: use the Codex harness loop on each subtask (`scripts/codex-worker.sh` -> validation -> scoped reviewer Codex -> fix -> re-validate/re-review).

**Goal:** Finish Task 137 by deleting the active legacy thread path and making `thread` mean only the Keryx collaboration object across CLI, runtime context, tests, and docs.

**Architecture:** Keep Keryx storage/service internals free to retain `session_id` temporarily if needed, but introduce one clear Maia adapter boundary where public/operator surfaces expose only `thread`/`thread_id`. Remove all active reads of `collaboration_threads/messages/handoffs` from thread visibility and runtime context. After the cutover, legacy collaboration tables/models may remain only if they are no longer part of any active code path and are clearly non-canonical.

**Tech stack:** Python 3.11, argparse CLI, SQLite state DB, pytest, Codex worker/reviewer harness.

---

## Subtask sequence

### Subtask 137A — Keryx-backed thread visibility cutover
**Spec:** `docs/tasks/137a-keryx-thread-visibility-cutover.md`

Objective:
- Move `maia thread list/show` and related `handoff show` visibility from `CollaborationStorage` to Keryx-backed data.
- Make operator output use `thread`/`thread_id` even when backed by Keryx `session_id` internally.

Primary files:
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/keryx_models.py`
- `tests/test_cli.py`

Validation:
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- `PYTHONPATH=src python3 -m maia --help`
- `PYTHONPATH=src python3 -m maia thread --help`
- live repro in isolated HOME: `maia thread show sess01`, `maia handoff show handoff01`

### Subtask 137B — Runtime context thread contract cutover
**Spec:** `docs/tasks/137b-runtime-thread-context-cutover.md`

Objective:
- Remove active runtime context dependence on legacy collaboration tables/models.
- Ensure runtime prompt/context refers to the Keryx collaboration object as a `thread`, not a `session`, while leaving Hermes runtime session semantics untouched.

Primary files:
- `src/maia/agent_context.py`
- `src/maia/hermes_runtime_worker.py`
- `tests/test_hermes_runtime_worker.py`

Validation:
- `PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py`

### Subtask 137C — Legacy thread cleanup and contract closeout
**Spec:** `docs/tasks/137c-legacy-thread-cleanup-and-closeout.md`

Objective:
- Clean up leftover legacy thread dependencies that would keep two meanings of `thread` alive.
- Align docs/tests/state helpers/closeout notes so the Keryx thread contract is the only active story.

Primary files:
- `src/maia/collaboration_storage.py`
- `src/maia/message_model.py`
- `src/maia/handoff_model.py`
- `src/maia/sqlite_state.py`
- `tests/test_cli_runtime.py`
- `tests/test_sqlite_state.py`
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/2026-04-20-keryx-migration-closeout.md`
- `docs/tasks/137-keryx-thread-redefinition-after-legacy-purge.md`

Validation:
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_keryx_service.py tests/test_keryx_server.py tests/test_sqlite_state.py`
- `PYTHONPATH=src python3 -m maia --help`
- `PYTHONPATH=src python3 -m maia thread --help`

## Working rules
- Keep scope tight in this dirty repo; do not sweep unrelated untracked docs or prior Keryx files into the subtask review context.
- Reviewers must ignore unrelated pre-existing uncommitted changes outside each subtask’s allowed files.
- If a subtask reveals a contract ambiguity (for example public `thread_id` vs internal `session_id`), fix the contract explicitly in the spec/doc/test rather than leaving mixed wording.
- Update the parent Task 137 checkboxes only after all three subtasks are complete and final validation + reviewer approval pass.
