# Task 034 — team metadata CLI surface

## Goal
Make team-level metadata operator-manageable from the Maia CLI instead of only through import/export side effects.

## Scope
Add public CLI commands:
- `maia team show`
- `maia team update ...`

Supported editable fields:
- `team_name`
- `team_description`
- `team_tags`
- `default_agent_id`

## Approach
- Add a top-level `team` resource alongside `agent`, `export`, `import`, and `inspect`.
- Keep direct `main([...])` placeholder behavior intact for contract tests, while runtime `python -m maia ...` uses the real handlers.
- Store updates in `~/.maia/team.json` using the existing `TeamMetadata` helpers.
- Reuse the inspect-safe display encoding for command output:
  - empty string -> `∅`
  - lists -> comma-separated or `-`
- Validate `--default-agent` against the current registry so team metadata cannot point at a non-existent agent.
- Keep this slice scoped to team metadata only; do not touch agent persona/SOUL handling.

## CLI shape
### Show
- `maia team show`
- Prints the current team metadata in one machine-readable line.

### Update
- Setters:
  - `--name <text>`
  - `--description <text>`
  - `--tags <comma,separated,list>`
  - `--default-agent <agent_id>`
- Clearers:
  - `--clear-name`
  - `--clear-description`
  - `--clear-tags`
  - `--clear-default-agent`

## Validation rules
- At least one change flag is required for `team update`.
- Text setters reject empty/whitespace-only values.
- Tag lists must contain only non-empty values.
- Duplicate tags collapse to first-seen unique order.
- `--default-agent` must reference an existing agent id.

## Files touched
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- `python -m maia team show` returns the current team metadata, defaulting to empty values when `team.json` does not exist.
- `python -m maia team update ...` persists the requested fields into `~/.maia/team.json`.
- Operators can clear optional team metadata fields explicitly.
- Invalid updates fail cleanly with actionable errors.
- README and CLI help expose the new team commands.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
