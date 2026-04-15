# Task 016 — final import/export command structure

## Goal
Promote Maia-wide state transfer to top-level `maia export` / `maia import` commands and remove the confusing dedicated restore-command wording.

## Why now
- The final product direction is:
  - `export` = save current Maia portable state
  - `import` = restore that portable state elsewhere or later
- `restore` should remain reserved for agent lifecycle (`archive -> restore`).
- The earlier dedicated restore command added ambiguity instead of reducing it.

## Scope
- Add top-level runtime commands:
  - `maia export [path]`
  - `maia import <path>`
- Keep current runtime behavior for bundle creation/resolution.
- Remove the earlier dedicated restore command from the public CLI surface.
- Keep hidden `agent export|import` aliases only for compatibility.

## Non-goals
- No change to agent lifecycle commands.
- No full Maia-state expansion beyond the current registry + manifest bundle.
- No schema migration engine.

## Command contract
- `maia export [path]`
  - exports current Maia portable state
  - default path: `~/.maia/exports/registry.json`
  - writes sibling `manifest.json`
- `maia import <path>`
  - imports a raw registry snapshot or a manifest-backed bundle
  - replaces current registry state
- `maia agent restore <id>`
  - remains lifecycle-only

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- Top-level help shows `export` and `import`.
- Agent help no longer exposes transfer commands publicly.
- `python -m maia export` and `python -m maia import` work end-to-end.
- Existing direct `main([...])` placeholder behavior is preserved for the new top-level commands.
- Hidden `agent export|import` aliases may remain for compatibility but are not part of the public surface.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- Manual runtime flow:
  - `PYTHONPATH=src python3 -m maia export`
  - `PYTHONPATH=src python3 -m maia import ~/.maia/exports/manifest.json`