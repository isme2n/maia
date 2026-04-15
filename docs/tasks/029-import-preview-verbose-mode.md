# Task 029 — import preview verbose mode

## Goal
Add an explicit verbose preview mode so operators can request full untruncated import preview lists when reviewing large Maia imports.

## Why now
- The default preview is now intentionally compact and truncates long lists after 5 entries.
- That is good for everyday operations, but sometimes an operator needs the complete added/removed/changed lists before approving a high-impact import.
- A verbose mode gives deeper visibility without making the default output noisy.

## Scope
- Add `--verbose-preview` to `maia import`.
- Support it with:
  - `maia import <path> --preview --verbose-preview`
  - `maia import <path> --verbose-preview`
  - `maia import <path> --yes --verbose-preview`
- When enabled, print the full added/removed/changed ids, names, and changed details without truncation.
- Keep the default compact behavior unchanged when the flag is absent.

## Non-goals
- No separate `preview` command.
- No pagination.
- No JSON output mode.
- No color formatting.

## Output contract
- Existing line structure remains unchanged:
  - `preview ...`
  - `risk ...`
  - `added ...`
  - `removed ...`
  - `changed ...`
- `--verbose-preview` only affects list truncation.
- Without `--verbose-preview`, large lists still use `...(+X)`.
- With `--verbose-preview`, large lists render in full.

## Acceptance criteria
- `maia import <path> --preview --verbose-preview` shows full lists.
- `maia import <path> --verbose-preview` shows full lists before apply.
- Default preview output remains truncated for long lists.
- Existing risk, confirmation, and overwrite flows remain unchanged.

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
