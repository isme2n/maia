# Task 128 - Keryx SQLite storage

## Goal
Persist Keryx Phase 1 resources in the canonical Maia SQLite state DB without introducing a second control-plane database.

## Non-goals
- service-layer business rules
- HTTP route handling
- runtime worker integration
- CLI changes
- deleting old collaboration tables

## Allowed files
- `docs/tasks/128-keryx-sqlite-storage.md`
- `src/maia/sqlite_state.py`
- `src/maia/keryx_storage.py`
- `tests/test_sqlite_state.py`
- `tests/test_keryx_storage.py`

## Acceptance criteria
- [x] `SQLiteState.initialize()` creates Keryx tables alongside existing Maia tables.
- [x] New Keryx storage helper persists sessions, participant membership, messages, and handoffs in SQLite.
- [x] Storage helper can list/get/update Phase 1 records needed by the service layer.
- [x] Existing tests for prior SQLite/control-plane behavior still pass after schema expansion.
- [x] New tests cover create/list/get/update behavior for Keryx storage.

## Required validation commands
- `python3 -m pytest -q tests/test_sqlite_state.py tests/test_keryx_storage.py`

## Forbidden changes
- CLI changes
- runtime worker changes
- HTTP server code
- removing old collaboration persistence in this task
