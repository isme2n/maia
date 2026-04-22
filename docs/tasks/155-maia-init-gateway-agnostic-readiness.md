# Task 155 — Maia init gateway-agnostic readiness

## Goal
- Absorb gateway setup into the init flow in a platform-agnostic way so Maia requires at least one usable user-facing gateway plus a default delivery destination before claiming onboarding success.

## Non-goals
- Adapter-specific redesign for every platform
- Telegram-only product wording
- Final Docker runtime start in this task

## Allowed files
- `src/maia/cli.py`
- `src/maia/agent_setup_session.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/tasks/155-maia-init-gateway-agnostic-readiness.md`

## Acceptance criteria
- [x] Public wording is gateway/platform agnostic.
- [x] Init requires at least one usable gateway, not a Telegram-specific branch.
- [x] Init records whether a default destination/chat surface is resolvable.
- [x] Partial gateway setup does not produce a false success.
- [x] Focused tests lock the generic readiness contract.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- No final runtime-start completion logic in this task
- No broad docs sweep outside task scope

## Notes
- Recovery subcommands may remain, but the happy path must not require users to memorize them.

## Closeout evidence
- Follow-up hardening task: `155B` approved.
- Validation: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- Validation result: `156 passed`
- Re-review verdict: `approve`
- Review-confirmed contract: public init wording remains gateway-agnostic, init distinguishes usable gateway readiness from default-destination readiness, partial gateway setup no longer yields false onboarding success, and the downgrade truthfulness fix prevents stale persisted `complete` from overstating readiness.
