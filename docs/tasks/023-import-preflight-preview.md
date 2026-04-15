# Task 023 — import preflight preview

## Goal
Add a safe import preflight preview so operators can see how a snapshot would change the current Maia registry before committing the import.

## Why now
- Bundles now carry enough metadata to identify what they are and where they came from.
- The next operator question is impact: what will actually change if this snapshot is imported?
- A read-only preview reduces accidental overwrites and makes rollback/migration workflows safer.

## Scope
- Add `--preview` to top-level `maia import`.
- Reuse the existing import source-loading path.
- Compare current registry vs incoming registry by `agent_id`.
- Report:
  - current agent count
  - incoming agent count
  - added / removed / changed / unchanged counts
  - added names/ids
  - removed names/ids
  - changed names/ids plus changed fields
- Do not mutate local state when preview mode is used.

## Non-goals
- No interactive confirmation prompt.
- No per-field diff pretty printer beyond summary details.
- No automatic import after preview.

## Diff rules v1
Agent identity is keyed by `agent_id`.
Field changes considered meaningful:
- `name`
- `status`
- `persona`

Output lines:
- `preview source=<path> registry=<path> current_agents=<n> incoming_agents=<n> added=<n> removed=<n> changed=<n> unchanged=<n>`
- `added ids=<csv-or-> names=<csv-or->`
- `removed ids=<csv-or-> names=<csv-or->`
- `changed ids=<csv-or-> names=<csv-or-> details=<csv-or->`

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- `maia import <path> --preview` prints a diff summary and exits successfully.
- Preview mode does not mutate the local registry.
- Standard import behavior remains unchanged when `--preview` is omitted.
- Missing/invalid import sources still fail with the same clear errors.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
