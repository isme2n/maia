# Task 137B - Runtime thread context cutover

## Goal
Make Maia runtime context loading and worker prompt assembly describe the Keryx collaboration object as a `thread` and stop depending on legacy collaboration tables/models for active flow.

## Reviewer follow-up scope
- keep Keryx HTTP `/sessions/...` routes internal to `HttpKeryxClient`
- make the worker-facing Keryx contract use explicit thread adapter/view types
- ensure `process_once`, `build_prompt`, and focused tests do not operate on session-shaped Keryx records

## Non-goals
- changing Hermes own session/runtime semantics
- removing all legacy collaboration model files from disk in this subtask
- changing public README/PRD wording beyond code/test changes needed here

## Allowed files
- `docs/tasks/137b-runtime-thread-context-cutover.md`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/keryx_models.py`
- `src/maia/keryx_service.py`
- `tests/test_hermes_runtime_worker.py`

## Acceptance criteria
- [x] active runtime context loading no longer reads `collaboration_threads/messages/handoffs` as the current collaboration source.
- [x] worker prompt/context uses `thread` / `thread_id` wording for the Keryx collaboration object.
- [x] the worker-facing Keryx contract is thread-shaped via explicit adapter/view types, with any `/sessions` routing hidden behind the HTTP client boundary.
- [x] no code in this active runtime path implies a Keryx thread is a Hermes session.
- [x] targeted tests cover the new thread wording and pass.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py`

## Forbidden changes
- renaming Hermes session concepts
- broad CLI/docs cleanup outside the allowed files
- adding a second collaboration naming layer
