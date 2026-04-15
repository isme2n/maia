# Task 021 — export metadata overrides

## Goal
Let operators override bundle metadata at export time so a `.maia` snapshot can carry a meaningful human label and description.

## Why now
- Bundle metadata now exists and is visible in `maia inspect`.
- The next practical step is allowing operators to name snapshots intentionally instead of relying only on auto-generated defaults.
- This improves migration, rollback, and archival workflows without changing the public export/import commands.

## Scope
- Add top-level export flags:
  - `--label`
  - `--description`
- Apply the overrides to both:
  - `.maia` bundle exports
  - raw registry + manifest exports
- Reject empty/whitespace-only metadata overrides.

## Non-goals
- No interactive prompt flow.
- No metadata editing after export.
- No new import behavior.

## CLI contract
Examples:
- `maia export team.maia --label prod-team --description "Nightly migration snapshot"`
- `maia export snapshot.json --label release-candidate --description "Pre-migration checkpoint"`

Rules:
- Missing flags keep the current defaults.
- Provided values are trimmed.
- Empty or whitespace-only values fail with a clear error.

## Files to modify
- `src/maia/cli.py`
- `src/maia/bundle_archive.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- Export flags override `label` and `description` in emitted manifest metadata.
- Inspect displays the overridden values.
- Raw registry exports and `.maia` bundle exports behave consistently.
- Empty metadata overrides fail with explicit validation errors.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
