# Task 156 — Maia init conversation-ready start

## Goal
- Finish `maia init` by actually starting the first Docker-backed agent and verifying a truthful conversation-ready completion state.

## Non-goals
- Broad release-readiness docs cleanup
- New collaboration features beyond startup verification

## Allowed files
- `src/maia/cli.py`
- `src/maia/docker_runtime_adapter.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/156-maia-init-conversation-ready-start.md`

## Acceptance criteria
- [x] `maia init` success means the first agent runtime actually started.
- [x] Completion text distinguishes `running but incomplete` from true `conversation-ready` success.
- [x] Failure output gives a single concrete remediation path and, if applicable, a resume command.
- [x] Focused tests cover running/conversation-ready success and partial-failure cases.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py`
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- No broad packaging/docs overhaul beyond the final README wording needed by this task
- No unrelated gateway contract redesign

## Notes
- The product success condition is runnable now, ideally talk now.

## Closeout evidence
- Validation 1: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py`
- Validation 1 result: `72 passed`
- Validation 2: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- Validation 2 result: `158 passed`
- Reviewer verdict: `approve`
- Review-confirmed contract: `maia init` now returns success only when the selected agent runtime is actually running and `conversation_ready=yes`; failure states emit a single concrete remediation path and preserve truthful non-success when runtime is running but onboarding is still incomplete.
