# Task 030 — import/export CLI help polish

## Goal
Improve Maia CLI help text for `import` and `export` so operators can understand the safety workflow directly from `--help` output.

## Why now
- Import preview, risk classification, truncation, and verbose preview are now implemented.
- The remaining UX gap is discoverability: users should not need README context to understand how `--preview`, `--verbose-preview`, and `--yes` interact.
- Better `--help` text makes the CLI feel more self-explanatory and production-ready.

## Scope
- Improve `maia import --help` descriptions:
  - clarify that `--preview` is read-only
  - clarify that `--verbose-preview` disables truncation for preview lists
  - clarify that `--yes` skips confirmation for overwrite imports
- Improve top-level subcommand help labels for `import`, `export`, and `inspect`.
- Keep behavior unchanged.

## Non-goals
- No new flags.
- No output format changes.
- No shell completions.

## Acceptance criteria
- `maia --help` shows clearer top-level help for import/export/inspect.
- `maia import --help` clearly describes:
  - preview is read-only
  - verbose preview expands list output
  - yes skips overwrite confirmation
- Runtime behavior remains unchanged.

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `README.md`

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
