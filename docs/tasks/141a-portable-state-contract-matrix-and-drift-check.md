# Task 141A — Portable-state contract matrix and drift-check baseline

## Goal
Create explicit Part 3 contract-lock artifacts for export/import/inspect safety surfaces.

## Non-goals
- Runtime behavior changes
- Editing README/help/test wording directly (handled by follow-up tasks)

## Allowed files
- `docs/tasks/141a-portable-state-contract-matrix-and-drift-check.md`
- `docs/contracts/portable-state-public-contract-matrix.md`
- `docs/contracts/portable-state-drift-checks.md`

## Required outputs
1) Contract matrix with fields:
   - command/term
   - status (`active`, `secondary`, `legacy-history`)
   - canonical wording
   - assert locations (README/help/tests/code)
2) Drift-check command doc containing:
   - text checks for `maia export`, `maia import`, `--preview`, `--yes`, `maia inspect`
   - help checks (`python3 -m maia --help`, `python3 -m maia import --help`, `python3 -m maia export --help`)
   - test checks (`pytest` targets)

## Acceptance criteria
- Matrix marks `export` and `import` as active Part 3 public surface.
- Matrix marks `inspect` as secondary/support surface.
- Matrix includes import safety contract (`preview` + confirm + `--yes`).
- Drift-check document is executable and concise.

## Validation
- `python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- Editing src code or tests in this task.
