# Task 132 - Maia-managed Keryx shared-infra bootstrap

## Goal
Make Maia shared infra own one runtime-reachable Keryx endpoint so later runtime tasks consume a real managed collaboration service instead of ad hoc temporary servers.

## Non-goals
- worker collaboration logic cutover
- public CLI/help/docs Keryx wording migration
- deleting broker/call-era code

## Allowed files
- `docs/tasks/132-maia-managed-keryx-shared-infra-bootstrap.md`
- `src/maia/infra_runtime.py`
- `src/maia/cli.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/runtime_adapter.py`
- `tests/test_cli_runtime.py`
- `tests/test_docker_runtime_adapter.py`

## Acceptance criteria
- [x] shared infra bootstrap creates or verifies one Maia-managed Keryx endpoint for the local state DB.
- [x] `maia doctor` / `maia setup` surface Keryx readiness as part of shared infra, not as an agent-local concern.
- [x] runtime containers receive a runtime-reachable `KERYX_BASE_URL`.
- [x] temporary retention of broker/state env vars, if still needed, is explicitly compatibility-only and not framed as collaboration truth.
- [x] targeted tests cover endpoint/env wiring and readiness reporting.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia doctor --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia setup --help`

## Forbidden changes
- changing Keryx Phase 1 model/storage/service/server contracts unless strictly required for bootstrap
- introducing a second canonical DB
- making Keryx server lifecycle an operator-manual hidden prerequisite
