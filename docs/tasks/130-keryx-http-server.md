# Task 130 - Keryx HTTP server

## Goal
Expose Phase 1 Keryx service operations through a minimal stdlib HTTP server with JSON request/response handling.

## Non-goals
- authentication
- runtime worker cutover
- CLI command integration
- long-running daemon management
- old collaboration deletion

## Allowed files
- `docs/tasks/130-keryx-http-server.md`
- `src/maia/keryx_server.py`
- `tests/test_keryx_server.py`

## Acceptance criteria
- [x] Minimal HTTP server exists with JSON routes for `/agents`, `/sessions`, `/sessions/{id}`, `/sessions/{id}/messages`, `/sessions/{id}/handoffs`, and `/handoffs/{id}`.
- [x] GET/POST/PATCH routes return JSON and sensible HTTP status codes.
- [x] Server delegates business logic to `KeryxService` rather than embedding storage logic in handlers.
- [x] Tests cover successful route behavior and at least basic 404/400 handling.

## Required validation commands
- `python3 -m pytest -q tests/test_keryx_server.py`

## Forbidden changes
- CLI changes
- runtime worker changes
- broker removal
- editing storage/service contracts beyond what this task needs for server wiring
