# Task 014 — backup manifest foundation

## Goal
Add a minimal portable backup manifest next to every exported registry snapshot so Maia has a stable bundle contract for future restore work.

## Why now
- Task 012 introduced registry export/import.
- Task 013 established the restore-ready state layout.
- The next smallest useful step is to define a portable bundle shape instead of treating the registry JSON as an unstructured loose file.

## Scope
- Add a backup manifest module for Maia portable exports.
- Write `manifest.json` next to every exported registry snapshot.
- Keep current registry JSON export behavior intact.
- Allow `maia agent import <path>` to accept either:
  - a raw registry JSON path, or
  - a `manifest.json` path that resolves the registry file in the same directory.

## Non-goals
- No full-team bundle beyond registry + manifest.
- No Docker / Compose / DB / queue restore.
- No merge import semantics.
- No checksum/signature/encryption yet.

## Bundle contract v1

Directory example:

```text
bundle/
  manifest.json
  registry.json
```

Manifest shape:

```json
{
  "kind": "maia-backup-manifest",
  "version": 1,
  "created_at": "2026-04-14T12:00:00Z",
  "registry_file": "registry.json",
  "portable_paths": ["registry.json"],
  "runtime_only_paths": ["runtime/"],
  "agents": 2
}
```

Notes:
- `registry_file` is a file name, resolved relative to the manifest directory.
- `runtime_only_paths` is declarative only for now. It documents what should not be treated as portable state.

## Files to modify
- `src/maia/app_state.py`
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Files to add
- `src/maia/backup_manifest.py`

## Acceptance criteria
- `python -m maia agent export` writes both registry JSON and `manifest.json`.
- Explicit export paths also produce a sibling `manifest.json`.
- `python -m maia agent import <manifest.json>` restores from the referenced registry file.
- Invalid manifests produce clear errors.
- Missing registry files referenced by manifests produce clear errors.
- Direct `main([...])` placeholder contract remains unchanged.

## Validation
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- Manual runtime flow:
  - `PYTHONPATH=src python3 -m maia agent new demo`
  - `PYTHONPATH=src python3 -m maia agent export`
  - inspect `~/.maia/exports/manifest.json`
  - `PYTHONPATH=src python3 -m maia agent import ~/.maia/exports/manifest.json`