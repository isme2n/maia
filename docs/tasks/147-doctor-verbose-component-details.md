# Task 147 — doctor verbose component details

## Goal
Add a `--verbose` mode to `maia doctor` so the default output stays short, while verbose output shows concrete component details such as the Keryx implementation/runtime detail the operator asked for.

## Non-goals
- Do not redesign the entire doctor command.
- Do not change shared infra dependencies in this task.
- Do not broaden into setup/new wording changes.

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/infra_runtime.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/147-doctor-verbose-component-details.md`

## Required behavior
1. `maia doctor` default output stays concise.
2. `maia doctor --verbose` adds per-component detail lines under the summary.
3. Verbose detail must include concrete Keryx implementation info.
   - At minimum: `Keryx HTTP API`, endpoint, and that it runs as the current Python-based HTTP server/container path.
4. Verbose detail should include similarly concrete detail for:
   - Docker
   - SQLite State DB
5. Non-TTY output remains stable for tests.
6. Help text and README must mention the new verbose mode.

## Acceptance criteria
- [x] New/updated tests fail first and then pass.
- [x] Default doctor output remains short.
- [x] `maia doctor --verbose` shows component detail lines.
- [x] Help/README mention verbose detail mode.

## Required validation commands
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'doctor'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'doctor_help or verbose'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `PYTHONPATH=src python3 -m maia doctor --help`
- `PYTHONPATH=src python3 -m maia doctor --verbose`

## Closeout evidence
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'doctor'` → `10 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'doctor_help or verbose'` → `1 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py` → `132 passed`
- `PYTHONPATH=src python3 -m maia doctor --help` checked live
- `PYTHONPATH=src python3 -m maia doctor --verbose` checked live
- `KERYX_BASE_URL=http://custom-keryx:9999 PYTHONPATH=src python3 -m maia doctor --verbose` checked live
- Scoped reviewer verdict: `approve`

## Forbidden changes
- No unrelated refactors.
- No setup/new UX changes in this task.
