# Task 020 — bundle metadata polish

## Goal
Add operator-friendly bundle metadata to the Maia backup manifest so `maia inspect` shows more than raw structural fields.

## Why now
- `.maia` is now the canonical export artifact.
- `maia inspect` already exists, so better manifest metadata immediately improves operator UX.
- We want a stable place to hang future restore-oriented metadata without changing the public commands.

## Scope
- Extend manifest payloads written by export with:
  - `label`
  - `description`
  - `created_by`
  - `maia_version`
- Surface those fields in `maia inspect`.
- Keep import compatible with older manifests that do not yet contain those fields.

## Non-goals
- No interactive metadata editing flags yet.
- No free-form user-supplied descriptions yet.
- No signing/checksum/provider metadata yet.

## Metadata contract v1
Defaults written by export:
- `label`
  - derived from the export artifact stem
  - examples:
    - `team.maia` -> `team`
    - `registry.json` -> `registry`
- `description`
  - `Portable Maia export with <N> agent(s)`
- `created_by`
  - `maia-cli`
- `maia_version`
  - current package version

Inspect output additions:
- `bundle label=<label> created_by=<created_by> maia_version=<maia_version>`
- `description <description>`

## Files to modify
- `src/maia/backup_manifest.py`
- `src/maia/bundle_archive.py`
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- `.maia` exports include the new metadata fields in `manifest.json`.
- raw registry + manifest exports include the same metadata fields.
- `maia inspect` shows the metadata for any manifest-backed snapshot.
- import remains compatible with manifests that omit the new metadata fields.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
