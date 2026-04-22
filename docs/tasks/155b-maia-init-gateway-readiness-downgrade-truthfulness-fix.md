# Task 155B — Maia init gateway readiness downgrade truthfulness fix

## Goal
- Fix the Task 155 blocker where `maia init` can trust a stale persisted `gateway_setup_status=complete` even after the default destination/chat surface has been removed from the agent-scoped Hermes home.

## Reviewer blocker to address
- `maia init` currently refreshes gateway readiness only when the derived Hermes-home status is stronger than the stored status, and skips refresh entirely once stored status is `complete`.
- This can cause `default_destination_ready=yes` and even `conversation_ready=yes` to be reported after the default destination was removed from `.env`.

## Non-goals
- Final runtime start completion
- Adapter-specific gateway redesign
- Broad docs sweep

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/tasks/155b-maia-init-gateway-readiness-downgrade-truthfulness-fix.md`

## Acceptance criteria
- [x] `maia init` re-evaluates gateway/default-destination truthfulness from durable Hermes-home state even when stored gateway status was previously `complete`.
- [x] If the default destination is no longer resolvable, readiness is downgraded truthfully.
- [x] `default_destination_ready` and `conversation_ready` are not falsely reported as ready in the stale-complete case.
- [x] Focused regression coverage locks the downgrade case.
- [x] Required pytest passes.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- No final runtime-start completion logic
- No broad wording/doc changes outside task scope

## Notes
- Keep this narrowly scoped to truthful downgrade/refresh behavior for gateway/default-destination readiness.

## Closeout evidence
- Validation: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- Validation result: `156 passed`
- Reviewer verdict: `approve`
- Review-confirmed behavior: `maia init` now allows gateway-state downgrade refresh from durable Hermes-home state before readiness reporting, so stale persisted `complete` no longer falsely drives `default_destination_ready` or `conversation_ready`.
