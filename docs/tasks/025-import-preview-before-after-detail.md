# Task 025 — import preview before/after detail

## Goal
Improve import preview output so changed agents show field-level before/after values instead of only listing changed field names.

## Why now
- The destructive import safety flow is now in place.
- Operators can already see that something changed, but not exactly how.
- Before/after detail makes preview useful even for highly different Maia states and reduces confirmation mistakes.

## Scope
- Extend changed preview details to include old -> new values.
- Cover the meaningful compared fields:
  - `name`
  - `status`
  - `persona`
- Keep the existing one-line summary structure.

## Non-goals
- No multiline per-agent diff view.
- No colorized output.
- No merge behavior.

## Output contract
Changed details stay on the existing `changed ... details=...` line.
Format per changed agent:
- `<agent_id>:name:<old>-><new>+status:<old>-><new>+persona:<old>-><new>`

Formatting rules:
- empty strings render as `∅`
- spaces render as `␠`
- commas render as `⸴`
- unchanged fields are omitted

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- Preview still reports the same counts.
- Changed detail now shows before/after values.
- Multi-field changes for a single agent show all changed fields.
- Existing preview/confirm/import behavior remains unchanged.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
