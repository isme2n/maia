# Task 141C — CLI tests portable-state contract lock

## Goal
Pin Part 3 portable-state contract in tests so wording drift fails quickly.

## Roadmap position
- Execution task for Part 3.

## Non-goals
- Runtime logic changes
- Broad test refactors unrelated to portable-state contract

## Allowed files
- `docs/tasks/141c-cli-tests-portable-contract-lock.md`
- `tests/test_cli.py`

## Required changes
1) Update README/help contract assertions to include:
   - export default flow and explicit-path export flow
   - import safety flow (`--preview`, confirm, `--yes`)
2) Add assertions that primary public flow does not require `inspect`.
3) Keep existing Part 1/Part 2 contract checks unless conflicting.

## Acceptance criteria
- `tests/test_cli.py` contains explicit positive/negative assertions for Part 3 contract.
- test output remains green.

## Validation
- `python3 -m pytest -q tests/test_cli.py`
