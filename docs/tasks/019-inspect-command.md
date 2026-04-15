# Task 019 — inspect portable Maia snapshots

## Goal
Add a top-level `maia inspect <path>` command so an operator can examine a `.maia` bundle or other importable snapshot before running `maia import`.

## Why now
- `.maia` is now the canonical export artifact.
- Once there is a dedicated bundle file, the next operator need is safe preflight inspection.
- Import already validates the bundle contract, so inspect can reuse that strict parsing path and expose the important metadata.

## Scope
- Add a top-level `inspect` CLI command.
- Support the same input family as import:
  - `.maia` bundle
  - `manifest.json`
  - raw registry JSON
- Report:
  - source format
  - registry target inside the snapshot
  - agent count
  - manifest metadata when available
  - agent names
  - status counts

## Non-goals
- No JSON output mode yet.
- No bundle signature/checksum output yet.
- No diff against the current local Maia state yet.

## Output contract v1
First line:
- `inspected path=<path> format=<format> registry=<path-or-member> agents=<count>`

Additional lines when manifest metadata is available:
- `manifest kind=<kind> version=<version> scope_version=<scope_version> created_at=<timestamp>`
- `portable paths=<csv> state_kinds=<csv>`
- `runtime paths=<csv> state_kinds=<csv>`

Final line always:
- `agents names=<csv-or-> statuses=<csv-or->`

## Files to modify
- `src/maia/cli.py`
- `src/maia/bundle_archive.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- `python -m maia inspect team.maia` shows bundle metadata without mutating local state.
- `python -m maia inspect manifest.json` works.
- `python -m maia inspect registry.json` works, with manifest metadata when a matching sibling manifest exists.
- Missing or invalid inspect targets fail with clear errors.
- Existing import/export behavior remains unchanged.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
