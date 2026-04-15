# Task 024 — destructive import confirmation flow

## Goal
Make Maia imports safe by default when local state already exists: show the diff, warn that the import is destructive, and require confirmation before applying it.

## Why now
- `--preview` already exists and proves the diff logic is useful.
- The remaining safety gap is that a normal import can still overwrite existing state without an explicit last-step confirmation.
- We want the default import path to cover not only similar states, but fully different Maia states as well.

## Scope
- Extend top-level `maia import` with:
  - interactive overwrite confirmation when current registry is non-empty
  - `--yes` escape hatch for automation/non-interactive use
- Reuse the existing preview diff summary before apply.
- Keep `--preview` read-only.

## Non-goals
- No merge import behavior.
- No multi-step TUI prompt.
- No force level beyond `--yes`.

## Safety contract
Cases:
1. `maia import <path> --preview`
   - show diff only
   - never mutate state
2. `maia import <path>` with empty current registry
   - import directly
3. `maia import <path>` with non-empty current registry
   - show diff
   - print overwrite warnings
   - ask for confirmation
   - default no/cancel
4. `maia import <path> --yes`
   - show diff + warning
   - skip interactive confirmation
   - apply import

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- Import preview remains non-mutating.
- Normal import asks for confirmation when local state exists.
- Declining confirmation leaves local state unchanged.
- `--yes` applies the import without prompting.
- Existing import source validation behavior remains unchanged.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
