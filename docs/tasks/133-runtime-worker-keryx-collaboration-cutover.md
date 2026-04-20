# Task 133 - Runtime worker Keryx collaboration cutover

## Goal
Replace broker-era runtime collaboration behavior with Keryx-backed collaboration so running agents consume work, build context, and post replies through Keryx.

## Non-goals
- final public help/README/CLI wording cleanup
- broad deletion of every old collaboration surface in the same task
- non-collaboration removal of all state/env wiring

## Allowed files
- `docs/tasks/133-runtime-worker-keryx-collaboration-cutover.md`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/keryx_service.py`
- `src/maia/keryx_server.py`
- `src/maia/keryx_models.py`
- `src/maia/keryx_storage.py`
- `src/maia/app_state.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_keryx_service.py`
- `tests/test_keryx_server.py`

## Acceptance criteria
- [x] runtime worker no longer requires broker polling as the active collaboration consumption path.
- [x] worker obtains pending work through an explicit Keryx contract.
- [x] worker collaboration context comes from Keryx, not direct SQLite collaboration reads.
- [x] worker replies/update flow preserve explicit `session_id` continuity.
- [x] any minimal Keryx API extension needed for pending-work discovery is added and tested narrowly.
- [x] targeted runtime + Keryx tests pass.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py tests/test_keryx_service.py tests/test_keryx_server.py`

## Forbidden changes
- rewriting public CLI/help/docs in this task
- reintroducing queue-like Keryx abstractions instead of narrow session/handoff-driven discovery
- direct SQLite collaboration reads from the runtime after the cutover is complete

## Implementation notes
- Added a narrow `GET /agents/{agent_id}/pending-work` Keryx contract that derives runtime work from open session handoffs plus the latest session message addressed to that agent.
- Updated the runtime worker to poll Keryx directly, build prompt context from Keryx roster/session state, create reply messages in-session, and mark the processed handoff done.
