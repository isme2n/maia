# Task 140A — Contract matrix and drift-check baseline

## Goal
Create explicit Phase 1 contract lock artifacts so future changes can be checked against one source of truth.

## Non-goals
- Updating runtime behavior
- Editing README/help/test wording directly (handled by follow-up tasks)

## Allowed files
- `docs/tasks/140a-contract-matrix-and-drift-check.md`
- `docs/contracts/keryx-public-contract-matrix.md`
- `docs/contracts/contract-drift-checks.md`

## Required outputs
1) Contract matrix with fields:
   - command/term
   - status (`active`, `removed`, `legacy-history`)
   - canonical wording
   - assert locations (README/help/tests/code)
2) Drift-check command doc containing:
   - text grep/check commands for `/keryx`, `/call`, `/agent-call`, `delivery_mode`
   - help command checks (`python3 -m maia --help`, `python3 -m maia thread --help`)
   - test command checks (`pytest` targets)

## Acceptance criteria
- Matrix explicitly marks `/keryx` as active instruction contract.
- Matrix marks `/call` and `/agent-call` as removed from active contract.
- Matrix includes `delivery_mode` (`agent_only`/`user_direct`) contract row.
- Drift-check document is executable and concise.

## Validation
- `python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- Editing src code or tests in this task.
