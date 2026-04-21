# Task 140 — Contract Freeze surface alignment (README/CLI help/tests/code)

## Goal
Lock Maia collaboration contract wording and behavior so active surfaces are aligned:
- Maia = control plane, Keryx = collaboration plane
- user collaboration entry is `/keryx <instruction>`
- `/call` and `/agent-call` are not active contract
- `delivery_mode` command semantics are explicit and consistent

## Non-goals
- Runtime reliability internals (soak, zombie, self-heal)
- Full gateway re-architecture
- Broad historical docs cleanup not referenced by active product/help surfaces

## Primary surfaces in scope
- `README.md`
- `src/maia/cli_parser.py` (top-level and subcommand help contract)
- `tests/test_cli.py` (public contract assertions)
- active task/plan docs that are explicitly used as product contract references

## Required outputs
1) Contract matrix document (source-of-truth table)
   - command/term
   - status (`active`, `removed`, `legacy-history`)
   - canonical wording
   - where asserted (doc/help/test)
2) Remove/replace any active wording that contradicts Keryx-first contract.
3) Add/adjust tests to pin the final public contract.
4) Provide a short drift check command set for future regressions.

## Acceptance criteria
- No active README/CLI-help/tests wording presents `/call` or `/agent-call` as current collaboration entrypoints.
- `/keryx <instruction>` is consistently documented as explicit user collaboration instruction surface.
- `delivery_mode` wording appears consistently where message-delivery contract is explained.
- Targeted contract tests pass.

## Suggested validation
- `python3 -m pytest -q tests/test_cli.py`
- `python3 -m maia --help`
- `python3 -m maia thread --help`

## Notes
- Keep changes tightly scoped and reviewable.
- If this task reveals runtime contract mismatch that cannot be solved with wording/tests only, spin follow-up task instead of widening scope.
