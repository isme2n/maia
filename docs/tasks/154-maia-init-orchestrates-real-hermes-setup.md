# Task 154 — Maia init orchestrates real Hermes setup

## Goal
- Make `maia init` orchestrate the real agent-scoped Hermes setup flow through passthrough/attach behavior rather than duplicating or sniffing Hermes setup semantics.

## Non-goals
- Reimplement Hermes setup questions in Maia
- Parse Hermes interactive text as product logic
- Full gateway orchestration in this task
- Final conversation-ready runtime start in this task

## Allowed files
- `src/maia/cli.py`
- `src/maia/agent_setup_session.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/tasks/154-maia-init-orchestrates-real-hermes-setup.md`

## Acceptance criteria
- [x] `maia init` can create/resolve the first agent identity and launch real agent-scoped Hermes setup.
- [x] Maia records only durable setup/readiness outcome, not interpreted wizard semantics.
- [x] No code path in this task depends on sniffing Hermes prompt content.
- [x] Focused tests prove passthrough-style setup orchestration and failure handling.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- No gateway-specific orchestration yet
- No runtime start completion yet
- No Docker runtime adapter changes unless strictly required and listed later in a follow-up task

## Notes
- Maia owns orchestration and readiness tracking.
- Hermes owns setup UX.

## Closeout evidence
- Validation: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- Validation result: `152 passed`
- Reviewer verdict: `approve`
- Review-confirmed contract: `maia init` now bootstraps infra if needed, creates/resolves an onboarding agent, launches real agent-scoped Hermes setup via passthrough, and records only durable setup/gateway readiness outcomes for later phases instead of interpreting Hermes wizard text.
