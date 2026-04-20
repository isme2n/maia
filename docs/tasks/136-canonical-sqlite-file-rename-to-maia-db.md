# Task 136 - Canonical SQLite file rename to maia.db

## Goal
Rename the canonical Maia SQLite file from the generic state filename to a Maia-oriented filename (`maia.db`) without changing the product architecture: Maia still owns the canonical DB, and Keryx remains the collaboration plane using tables inside that DB.

## Non-goals
- changing Keryx collaboration model or API contracts
- introducing a second DB
- renaming Keryx tables
- reopening the completed Phase 1–4 migration contract

## Allowed files
- `docs/tasks/136-canonical-sqlite-file-rename-to-maia-db.md`
- `src/maia/app_state.py`
- `src/maia/cli.py`
- `src/maia/infra_runtime.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/keryx_service.py`
- `src/maia/keryx_storage.py`
- `src/maia/sqlite_state.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_docker_runtime_adapter.py`
- `tests/test_keryx_service.py`
- `tests/test_keryx_storage.py`
- `tests/test_sqlite_state.py`
- `README.md`
- `docs/prd/maia-core-product.md`

## Acceptance criteria
- [x] the canonical default DB path is `~/.maia/maia.db`.
- [x] user-facing/help/docs wording uses `maia.db` where the canonical DB file is named explicitly.
- [x] runtime/bootstrap paths still resolve one canonical Maia-owned DB.
- [x] no code/docs imply a separate Keryx DB was introduced.
- [x] targeted validation passes.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py tests/test_keryx_service.py tests/test_keryx_storage.py tests/test_sqlite_state.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`

## Forbidden changes
- renaming the DB to a Keryx-oriented name such as `keryx.db`
- splitting control-plane and collaboration-plane state into multiple canonical DB files
- broad cleanup outside the allowed files
