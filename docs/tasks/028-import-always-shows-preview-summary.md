# Task 028 — import always shows preview summary

## Goal
Make `maia import <path>` print the same preview/risk block before applying the snapshot even when the current registry is empty.

## Why now
- Preview, risk classification, and truncation are now strong enough to be the standard import surface.
- Today, non-preview import only shows the preview/risk block when the current registry is non-empty.
- That makes first-time import into a fresh Maia state less transparent than overwrite import, even though operators still benefit from seeing what will be applied.

## Scope
- Always print the preview/risk/added/removed/changed block for `maia import <path>` and `maia import <path> --yes`.
- Keep overwrite warnings and confirmation only for destructive cases where the current registry is non-empty.
- Preserve existing `--preview` behavior as read-only.

## Non-goals
- No confirmation prompt for empty current registry.
- No change to overwrite warning text.
- No merge semantics.

## Output contract
For non-preview import when current registry is empty:
1. print preview line
2. print risk line
3. print added/removed/changed lines
4. apply import immediately
5. print imported line

For non-preview import when current registry is non-empty:
- keep existing destructive flow
- still print the same preview/risk block before warnings/confirmation

## Acceptance criteria
- Import into an empty current registry prints preview/risk block before `imported ...`.
- Empty-current import still does not ask for confirmation.
- Existing overwrite-confirm behavior remains unchanged.
- Existing `--preview` behavior remains unchanged.

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
