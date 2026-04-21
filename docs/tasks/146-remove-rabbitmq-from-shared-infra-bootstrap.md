# Task 146 — remove RabbitMQ from shared infra bootstrap

## Goal
Align Maia's actual shared-infra bootstrap and doctor/setup contract with the current Keryx-over-HTTP collaboration architecture by removing RabbitMQ from the active bootstrap/readiness path.

## Non-goals
- Do not redesign Keryx thread/handoff/workspace behavior.
- Do not change agent identity, setup-gateway, or import/export semantics.
- Do not remove legacy broker modules/tests unless they are directly tied to active bootstrap/help/doctor surfaces.

## Allowed files
- `src/maia/infra_runtime.py`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `README.md`
- `docs/prd/maia-core-product.md`
- `ARCHITECTURE.md`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/tasks/146-remove-rabbitmq-from-shared-infra-bootstrap.md`

## Required behavior
1. `maia doctor` must no longer require RabbitMQ.
   - Shared infra checks should focus on Docker, Keryx HTTP API, and SQLite state DB.
   - No MAIA_BROKER_URL / external RabbitMQ branch in active doctor flow.
2. `maia setup` must no longer create/start RabbitMQ.
   - Shared infra bootstrap should create/start only what current active architecture needs.
3. Public wording must match the new truth.
   - doctor/setup/help/README/PRD/ARCHITECTURE must stop describing RabbitMQ as current shared infra.
4. Keep component naming operator-facing.
   - Docker
   - Keryx HTTP API
   - SQLite State DB
5. Preserve current Keryx HTTP bootstrap and runtime behavior.

## Acceptance criteria
- [ ] New/updated tests fail first and then pass.
- [ ] Doctor/setup no longer mention or require RabbitMQ.
- [ ] No active-path MAIA_BROKER_URL/RabbitMQ bootstrap logic remains in `infra_runtime.py`.
- [ ] README/help/PRD/ARCHITECTURE agree with the new shared-infra contract.

## Required validation commands
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'doctor or setup_bootstraps_shared_infra'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'doctor_help or setup_help or readme'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `PYTHONPATH=src python3 -m maia doctor --help`
- `PYTHONPATH=src python3 -m maia setup --help`

## Forbidden changes
- No unrelated refactors.
- Do not change unrelated runtime-worker code.
- Do not broaden into deleting every legacy broker module/test in this task unless needed for active bootstrap/help/doctor contract closure.
