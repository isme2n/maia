# Task 033 — team-level metadata export/import/inspect

## Goal
Implement the first portable-state v2 slice by making team-level metadata portable through export/import/inspect.

## Scope
This slice makes the following team metadata portable:
- `team_name`
- `team_description`
- `team_tags`
- `default_agent_id`

## Approach
- Keep the team metadata in manifest fields for this first slice.
- Restore the imported team metadata into `~/.maia/team.json` on import.
- Show the team metadata in `maia inspect` output.
- Bump the written manifest `scope_version` to `2` and expand `portable_state_kinds` to include `team-metadata`.
- Preserve backward compatibility when loading older scope_version 1 manifests.

## Why this shape
- Lowest-risk first implementation from the v2 planning doc.
- No live runtime state is exported.
- No new agent schema changes are needed yet.
- Inspect gets immediate operator value.

## Files touched
- `src/maia/app_state.py`
- `src/maia/backup_manifest.py`
- `src/maia/bundle_archive.py`
- `src/maia/cli.py`
- `src/maia/team_metadata.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- Exported manifests include team metadata fields.
- Imports restore team metadata into the Maia home directory.
- Inspect prints team metadata when manifest metadata is available.
- New exports write `scope_version=2` and `portable_state_kinds=["registry", "team-metadata"]`.
- Older scope_version 1 manifests still load.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
