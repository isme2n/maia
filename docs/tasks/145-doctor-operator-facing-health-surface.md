# Task 145 — doctor operator-facing health surface

## Goal
Make `maia doctor` follow operator-facing CLI health-check best practices: concrete component names, clear status labels, TTY-safe color, and actionable remediation wording grounded in Maia's actual current infra.

## Non-goals
- Do not remove RabbitMQ from runtime/bootstrap in this task.
- Do not redesign the full shared-infra architecture.
- Do not change agent/runtime semantics outside doctor/setup/help wording.

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/infra_runtime.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/145-doctor-operator-facing-health-surface.md`

## Required behavior
1. `maia doctor` must use concrete operator-facing component names.
   - `Queue` -> `RabbitMQ`
   - `Keryx` -> `Keryx HTTP API`
   - `Maia DB` -> `SQLite State DB`
2. When a check is blocked by an earlier failure, the summary should say `BLOCKED`, not `FAIL`.
3. TTY output may add color, but non-TTY output must remain plain text and test-stable.
4. Doctor/setup help text should use the same concrete component names.
5. The behavior must stay truthful to the current codebase state:
   - RabbitMQ is still part of shared infra today.
   - Keryx is the HTTP collaboration API.
   - SQLite is the local state DB.

## Acceptance criteria
- [x] New/updated tests fail first and then pass.
- [x] Doctor summary lines use concrete names and `BLOCKED` where appropriate.
- [x] Non-TTY doctor output stays plain text.
- [x] Doctor/setup help wording matches the new naming.

## Required validation commands
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'doctor or setup_bootstraps_shared_infra'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'doctor_help or setup_help'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Closeout evidence
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'doctor or setup_bootstraps_shared_infra'` → `8 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'doctor_help or setup_help'` → `3 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py` → `131 passed`

## Forbidden changes
- No unrelated refactors.
- No RabbitMQ removal in this task.
- No roadmap changes in this task.
