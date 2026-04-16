# Task 116 — Hermes runtime worker foundation

## Goal
- Add a minimal Maia-side runtime worker that can run inside a real Hermes container.
- The worker should poll the Maia broker, invoke the Hermes CLI for one-turn replies, publish replies back onto the broker, and ack only after a reply is published.
- Keep this as an internal runtime foundation, not a new public CLI surface.

## Non-goals
- Change public README/help narrative
- Add new Maia operator commands
- Implement handoff automation or workspace sync
- Solve provider credential bootstrapping beyond surfacing live blockers

## Allowed files
- `src/maia/docker_runtime_adapter.py`
- `src/maia/hermes_runtime_worker.py`
- `tests/test_docker_runtime_adapter.py`
- `tests/test_hermes_runtime_worker.py`
- `docs/tasks/116-hermes-runtime-worker-foundation.md`

## Acceptance criteria
- [x] Worker can process a delivered broker message into a reply message using a pluggable Hermes runner
- [x] Reply preserves thread continuity via `thread_id` and `reply_to_message_id`
- [x] Incoming message is acked only after publish succeeds
- [x] Hermes runner failure leaves the incoming message unacked for retry
- [x] Runtime containers receive `MAIA_AGENT_ID` and `MAIA_AGENT_NAME` automatically for the worker entrypoint
- [x] Targeted tests green
- [x] Live broker -> Hermes -> reply sanity check succeeded

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_hermes_runtime_worker.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- README/help churn
- broker contract/schema changes
- runtime adapter CLI UX changes
- speculative provider/setup UX work
