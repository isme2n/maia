# Task 031 — import/export operator examples

## Goal
Add short operator-facing examples for common Maia import/export workflows so users can copy/paste the right command without reconstructing the safety flow from prose.

## Why now
- Import/export behavior is now feature-complete enough to demonstrate clearly.
- Help text and README explain the flags, but examples make the workflow faster to discover and easier to trust.
- This is the natural final polish layer after preview, risk, truncation, verbose preview, and help improvements.

## Scope
- Add a compact “Examples” section to README covering:
  - export default bundle
  - preview-only safety check
  - verbose preview for large imports
  - non-interactive overwrite with `--yes`
  - inspect before import
- Add CLI epilog examples to `maia import --help` and `maia export --help`.
- Keep runtime behavior unchanged.

## Non-goals
- No new commands.
- No shell completion changes.
- No tutorial-length documentation.

## Acceptance criteria
- `maia import --help` includes short usage examples.
- `maia export --help` includes short usage examples.
- README includes operator-friendly copy/paste examples for common flows.
- Runtime behavior remains unchanged.

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `README.md`

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
