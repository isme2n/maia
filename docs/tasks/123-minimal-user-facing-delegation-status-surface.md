# Task 123 — minimal user-facing delegation status surface

## Goal
- active conversation agent가 내부 delegation 상태를 사용자에게 lightweight하게 보여주는 surface를 구현한다.
- dashboard-first가 아니라, 현재 대화 흐름 안에서 delegated_to / delegation_status / current_thread_id / latest_internal_update가 읽히는 것이 목표다.

## Roadmap position
- This task should only execute after the contract in Task 122 is stable.
- It is still part of the later direct-agent UX execution track, not a license for broad Part 4 work.

## Non-goals
- live runtime closeout
- giant operator dashboard
- autonomous routing layer
- dynamic agent addition expansion

## Allowed files
- `src/maia/cli.py`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/message_model.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_hermes_runtime_worker.py`
- `docs/tasks/123-minimal-user-facing-delegation-status-surface.md`
- `docs/plans/phase18-direct-agent-delegation-and-user-anchored-collaboration.md`

## Acceptance criteria
- [x] active conversation output can show delegated_to
- [x] active conversation output can show delegation_status
- [x] active conversation output can show current_thread_id
- [x] active conversation output can show latest_internal_update summary
- [x] the normal user flow does not require opening a separate dashboard or raw internal thread view
- [x] scoped review approves the minimal surface

## Closeout evidence
- Validation passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py`
  - Result: `145 passed`
- Scoped spec/quality review: `approve`
- Minimal surface outcome:
  - existing `send` / `reply` outputs now carry lightweight delegation fields without adding a new dashboard
  - existing `thread list` / `thread show` summaries now expose delegation metadata anchored to the active conversation thread
  - surfaced status meanings follow the Task 122 contract for `pending`, `needs_user_input`, `answered`, and `handoff_ready`
  - no delegation target is fabricated when there is no real internal event
  - latest_internal_update is bounded/truncated instead of dumping full internal message bodies

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py`

## Forbidden changes
- broad visibility/dashboard redesign
- leaking raw internal state into normal user-facing output
- changing delegation state semantics without updating Task 122/120

## Worker/reviewer notes
- Worker must keep the active conversation agent as the primary anchor.
- Reviewer should reject outputs that feel like operator debug dumps or raw internal thread dumps rather than lightweight user-facing status.
