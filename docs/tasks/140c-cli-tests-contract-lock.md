# Task 140C — CLI tests contract lock updates

## Goal
Pin Phase 1 collaboration contract in tests so regressions fail quickly.

## Non-goals
- Runtime logic changes
- Broad test cleanup unrelated to collaboration contract

## Allowed files
- `docs/tasks/140c-cli-tests-contract-lock.md`
- `tests/test_cli.py`

## Required changes
1) Update README/help contract assertions to include:
   - `/keryx <instruction>` as explicit user collaboration instruction surface
   - `delivery_mode` wording and values (`agent_only`, `user_direct`)
2) Add explicit assertions that active contract does not present:
   - `/call`
   - `/agent-call`
3) Keep existing Part 1 and visibility contract checks unless they conflict with locked contract.

## Acceptance criteria
- `tests/test_cli.py` contains explicit positive and negative assertions for the locked contract.
- test output remains green with updated wording.

## Validation
- `python3 -m pytest -q tests/test_cli.py`
