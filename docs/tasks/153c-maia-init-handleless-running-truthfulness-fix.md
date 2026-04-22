# Task 153C — Maia init handleless-running truthfulness fix

## Goal
- Fix the remaining Task 153 blocker where `maia init` can report `runtime_running=yes` and `conversation_ready=yes` from a persisted `RUNNING` runtime state that has no runtime handle.

## Reviewer blocker to address
- A `RuntimeState` with `runtime_status=RUNNING` but `runtime_handle=None` currently bypasses live verification and can be treated as a real running runtime.

## Non-goals
- Full init orchestration
- Gateway/runtime feature expansion
- README/help/package wording changes

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `docs/tasks/153c-maia-init-handleless-running-truthfulness-fix.md`

## Acceptance criteria
- [x] `maia init` does not treat handleless persisted `RUNNING` state as a verified running runtime.
- [x] In that state, `runtime_running` is false and `conversation_ready` is false.
- [x] Next-step output points to a truthful remediation (for example runtime start or runtime status path) rather than `conversation-ready-now`.
- [x] Focused regression coverage locks the handleless-running case.
- [x] Focused pytest passes.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- No edits outside allowed files
- No README/help/pyproject changes in this task
- No new orchestration beyond truthfulness fix

## Notes
- Keep this task narrowly scoped to the handleless-running truthfulness bug.

## Closeout evidence
- Validation: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- Validation result: `81 passed`
- Scoped reviewer verdict: `approve`
- Reviewer-confirmed behavior: handleless persisted `RUNNING` is downgraded to a non-running state for `maia init`, avoids live status probing without a handle, reports `runtime_running=no` and `conversation_ready=no`, and points to runtime start as the truthful next step.
