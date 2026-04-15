# Task 022 — bundle provenance metadata

## Goal
Add provenance metadata to Maia backup manifests so operators can tell where a snapshot came from before importing it.

## Why now
- `.maia` bundles now have human-friendly metadata.
- The next useful operator question is provenance: which machine and which source registry produced this snapshot?
- This improves migration audits, rollback confidence, and general restore hygiene without changing the core export/import UX.

## Scope
- Extend manifest metadata with:
  - `source_host`
  - `source_platform`
  - `source_registry_path`
- Populate those fields during export.
- Surface them in `maia inspect`.
- Keep import compatible with older manifests that do not include the new fields.

## Non-goals
- No cryptographic signing or authenticity guarantees.
- No user-editable provenance flags.
- No environment fingerprinting beyond basic host/platform/source path.

## Metadata contract
Export writes:
- `source_host`
  - current hostname
- `source_platform`
  - current Python platform string
- `source_registry_path`
  - the registry path used as the export source

Inspect output addition:
- `provenance source_host=<host> source_platform=<platform> source_registry=<path>`

## Files to modify
- `src/maia/backup_manifest.py`
- `src/maia/bundle_archive.py`
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- Exported manifests include provenance metadata.
- Inspect shows provenance metadata for manifest-backed snapshots.
- Older manifests still import successfully with fallback defaults.
- Existing export/import behavior remains unchanged.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
