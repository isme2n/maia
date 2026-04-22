# Task 153 — Maia init CLI surface and state model

## Goal
- Add the `maia init` command surface and define the truthful onboarding state model that distinguishes partial setup from true conversation-ready completion.

## Non-goals
- Full orchestration of Hermes setup or gateway setup
- Runtime startup logic
- Public packaging/doc sweep beyond what this CLI surface requires

## Allowed files
- `src/maia/cli_parser.py`
- `src/maia/cli.py`
- `tests/test_cli.py`
- `docs/tasks/153-maia-init-cli-surface-and-state-model.md`

## Acceptance criteria
- [x] `maia init` exists as a public top-level command.
- [x] Help text explains `init` as the canonical onboarding command.
- [x] CLI text/state output distinguishes at minimum: infra ready, agent identity ready, agent setup ready, gateway ready, default destination ready, runtime running, conversation ready.
- [x] If resume semantics are introduced, `maia init --resume` is documented/tested truthfully.
- [x] No code in this task pretends partial setup equals conversation-ready.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- No Hermes setup passthrough implementation in this task
- No gateway adapter logic changes
- No Docker runtime code changes
- No unrelated README/help cleanup outside the init surface

## Notes
- This task defines the command and state model only.
- The state model must support later truthful orchestration work.

## Closeout evidence
- Follow-up hardening tasks: `153B` approved, `153C` approved.
- Validation: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- Validation result: `81 passed`
- Live help checks:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia --help`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia init --help`
- Re-review verdict: `approve`
- Review-confirmed contract: `maia init` is top-level, non-ready states return non-zero, readiness output distinguishes infra/identity/setup/gateway/default destination/runtime/conversation, and handleless persisted `RUNNING` is not misreported as a real running runtime.
