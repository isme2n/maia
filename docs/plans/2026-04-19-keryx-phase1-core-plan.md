# Keryx Phase 1 Core Plan

> For Hermes/Codex execution, use the Maia harness loop on every task: worker Codex -> validation -> scoped reviewer Codex -> fix -> re-validate/re-review.

## Goal
Implement Phase 1 of the Keryx migration: canonical Keryx domain contracts, SQLite-backed persistence, roster-aware service layer, and a minimal HTTP server surface for agents/sessions/messages/handoffs.

## Why this phase exists
Phase 1 must establish Keryx as a real collaboration substrate before runtime cutover work begins. That means Phase 1 cannot stop at abstract ideas; it must provide concrete state models and callable server endpoints against the existing Maia SQLite state DB.

## Phase 1 boundary
Included:
- Keryx domain models and validation
- SQLite schema additions inside the existing Maia state DB
- Keryx persistence helpers
- Keryx service layer joining agent registry + runtime state into roster responses
- Minimal stdlib HTTP server exposing Phase 1 Keryx routes
- Tests for models, storage, service, and server behavior

Excluded from Phase 1:
- runtime worker cutover
- CLI/public surface migration
- `/call` deletion and old collaboration path removal
- RabbitMQ removal
- Keryx client inside runtime containers

## Design rules
1. Reuse the existing Maia SQLite state DB; do not add a second DB.
2. Keep Keryx models separate from old collaboration models.
3. Keep Keryx HTTP server thin; business logic lives in the service layer.
4. Do not introduce new third-party web dependencies.
5. Keep task scopes narrow because the repo already has unrelated in-flight changes.

## Task breakdown

### Task 127 - Keryx domain models
Create the new first-class Keryx resource contracts.

Files:
- `docs/tasks/127-keryx-domain-models.md`
- `src/maia/keryx_models.py`
- `tests/test_keryx_models.py`

Output:
- typed/validated records for roster summaries, sessions, messages, and handoffs
- serialization/deserialization parity tests

### Task 128 - Keryx SQLite schema and storage
Add persistent storage in the existing Maia SQLite state DB.

Files:
- `docs/tasks/128-keryx-sqlite-storage.md`
- `src/maia/sqlite_state.py`
- `src/maia/keryx_storage.py`
- `tests/test_sqlite_state.py`
- `tests/test_keryx_storage.py`

Output:
- `keryx_sessions`, `keryx_session_participants`, `keryx_messages`, `keryx_handoffs`
- CRUD-lite persistence helpers for Phase 1 resources

### Task 129 - Keryx service layer
Implement the stateful business layer that turns raw persistence into roster/session/message/handoff operations.

Files:
- `docs/tasks/129-keryx-service-layer.md`
- `src/maia/keryx_service.py`
- `tests/test_keryx_service.py`

Output:
- roster derived from canonical agent registry + runtime state
- create/list/get/update operations for sessions/handoffs/messages

### Task 130 - Keryx HTTP server
Expose the service through a minimal stdlib server so the runtime cutover has a real target.

Files:
- `docs/tasks/130-keryx-http-server.md`
- `src/maia/keryx_server.py`
- `tests/test_keryx_server.py`

Output:
- GET `/agents`
- GET/POST `/sessions`
- GET/PATCH `/sessions/{id}`
- GET/POST `/sessions/{id}/messages`
- GET/POST `/sessions/{id}/handoffs`
- GET/PATCH `/handoffs/{id}`

## Validation strategy
Per-task targeted validation only, then a final Phase 1 bundle run:
- `python3 -m pytest -q tests/test_keryx_models.py`
- `python3 -m pytest -q tests/test_sqlite_state.py tests/test_keryx_storage.py`
- `python3 -m pytest -q tests/test_keryx_service.py`
- `python3 -m pytest -q tests/test_keryx_server.py`
- final bundle: `python3 -m pytest -q tests/test_keryx_models.py tests/test_sqlite_state.py tests/test_keryx_storage.py tests/test_keryx_service.py tests/test_keryx_server.py`

## Review method
Because the repo contains unrelated uncommitted changes, use scoped review prompts that explicitly limit review to each task's allowed files and instruct Codex to ignore unrelated pre-existing changes elsewhere.

## Completion definition
Phase 1 is complete only when:
- all four task specs are implemented
- targeted tests and the final Phase 1 bundle pass
- each task has an approving scoped Codex review
- the result is ready for Phase 2 runtime cutover without inventing additional Phase 1 foundations
