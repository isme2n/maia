# Task 129 - Keryx service layer

## Goal
Implement a Keryx service layer that exposes roster/session/message/handoff operations on top of canonical Maia state.

## Non-goals
- HTTP transport details
- runtime cutover
- CLI/public command migration
- broker removal

## Allowed files
- `docs/tasks/129-keryx-service-layer.md`
- `src/maia/keryx_service.py`
- `tests/test_keryx_service.py`

## Acceptance criteria
- [x] Service can list roster entries by combining canonical agent registry and runtime state.
- [x] Service can create/list/get/update sessions.
- [x] Service can list/create messages under a session.
- [x] Service can list/create/get/update handoffs under a session.
- [x] Missing resources raise clear service-level errors.
- [x] Tests cover roster derivation and resource operations.

## Required validation commands
- `python3 -m pytest -q tests/test_keryx_service.py`

## Forbidden changes
- HTTP server code
- runtime worker changes
- CLI changes
- direct DB access from tests outside the Keryx storage/service contract
