# Task 018 — Maia bundle format

## Goal
Add a Maia-native single-file bundle format so export/import can use a dedicated `.maia` artifact instead of only loose JSON files.

## Why now
- The product direction already settled on top-level `maia export` / `maia import`.
- A custom bundle extension makes the export artifact feel like a Maia object instead of an implementation detail.
- We already have the required inner files:
  - `manifest.json`
  - `registry.json`

## Scope
- Introduce `.maia` as the canonical export artifact.
- Make the default export path `~/.maia/exports/maia-state.maia`.
- Implement zip-backed bundle write/read helpers.
- Keep explicit raw JSON + manifest export/import support for debugging and backcompat.

## Non-goals
- No encryption/signing/checksum yet.
- No full multi-file payload beyond manifest + registry.
- No compression tuning or streaming import/export yet.

## Bundle contract v1
- File extension: `.maia`
- Container format: zip archive
- Required members:
  - exactly one `manifest.json`
  - exactly one `registry.json`
- No extra archive members in v1

## CLI behavior
- `maia export`
  - default output: `~/.maia/exports/maia-state.maia`
- `maia export team.maia`
  - writes a single-file Maia bundle archive
- `maia export snapshot.json`
  - still writes raw `snapshot.json` plus sibling `manifest.json`
- `maia import team.maia`
  - imports from the Maia bundle archive

## Files to modify
- `src/maia/app_state.py`
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Files to add
- `src/maia/bundle_archive.py`

## Acceptance criteria
- Default `maia export` produces a `.maia` file.
- Explicit `.maia` exports produce a readable Maia bundle archive.
- `maia import <bundle.maia>` restores from the bundle successfully.
- Invalid `.maia` files fail with a clear error.
- Explicit raw JSON export/import still works.

## Validation
- `python3 -m pytest -q tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`