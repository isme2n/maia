# Task 117 — bootstrap runtime defaults for live Part 2

## Goal
- Restore the public bootstrap contract `maia doctor -> maia setup -> maia agent new -> maia agent setup -> maia agent start` so it works without requiring an extra `agent tune` step in the happy path.
- Re-open Part 2 closeout against the real requirement: actual Hermes runtime containers must be startable from the public flow and able to participate in live broker-backed conversation.

## Root cause summary
- Current public docs/help/PRD lock a simple Part 1 flow where `agent new` is identity-only and `agent start` follows `agent setup`.
- Current implementation still requires `runtime_spec` to exist before `agent start`, and the only public way to create that spec is `agent tune --runtime-image --runtime-workspace --runtime-command --runtime-env ...`.
- The old runtime smoke contract (Phase 10 / Phase 13 and `_setup_v1_golden_flow()` in `tests/test_cli_runtime.py`) still encodes that older `agent tune -> start` flow.
- Result: the shipped public story and the actual start preconditions diverged, so Part 2 was declared complete while the advertised live bootstrap path is not actually runnable end-to-end.

## Non-goals
- Add a new public lifecycle verb
- Reintroduce a model/provider/team-default wizard into `maia setup`
- Expand broker semantics or collaboration schema beyond what is needed for the live bootstrap fix
- Add a web UI or daemon supervisor

## Recommended fix direction
- Choose code change over doc rollback.
- `maia setup` should establish a shared Maia runtime default for the canonical Hermes worker path.
- `maia agent new` should attach that default runtime launch intent automatically so `agent start` has a valid baseline runtime spec without requiring `agent tune` in the happy path.
- `maia agent tune` should remain as an override/edit surface, not a hidden prerequisite for first start.
- Live Part 2 closeout should only be re-closed after a representative host proves: setup, new, agent setup, start planner, start reviewer, broker-backed request/reply, thread visibility.

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/app_state.py`
- `src/maia/infra_runtime.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/agent_model.py`
- `src/maia/hermes_runtime_worker.py`
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md`
- `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`
- `docs/plans/maia-product-roadmap-5-parts.md`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_docker_runtime_adapter.py`
- `tests/test_hermes_runtime_worker.py`
- `docs/tasks/117-bootstrap-runtime-defaults-for-live-part2.md`

## Acceptance criteria
- [x] Fresh-home happy path does not require `agent tune` before first `agent start`
- [x] `maia setup` / `agent new` provide enough runtime default state for `agent start` to attempt a real Hermes worker launch
- [x] `agent tune` still works as an override surface, not a required bootstrap step
- [x] README/help/PRD/tests all agree on the same first-run and Part 2 live story
- [x] Representative live validation covers `setup -> new -> agent setup -> start -> conversation`
- [x] Targeted tests green
- [x] `bash scripts/verify.sh` green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py tests/test_hermes_runtime_worker.py`
- `cd /home/asle/maia && bash scripts/verify.sh`
- Representative host smoke:
  - `maia doctor`
  - `maia setup`
  - `maia agent new planner`
  - `maia agent new reviewer`
  - `maia agent setup planner`
  - `maia agent setup reviewer`
  - `maia agent start planner`
  - `maia agent start reviewer`
  - live broker-backed request/reply confirmation
  - `maia thread show <thread_id>`

## Forbidden changes
- Reframing the product back into a manual CLI messenger story
- Solving the mismatch only by weakening README/help back to `agent tune` as a required hidden prerequisite
- Broad unrelated refactors outside the bootstrap/runtime contract

## Closeout evidence
- Targeted validation passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py tests/test_hermes_runtime_worker.py`
  - Result: `149 passed`
- Full validation passed:
  - `cd /home/asle/maia && bash scripts/verify.sh`
  - Result: `299 passed`
- Fresh-home live runtime bootstrap passed without `agent tune`:
  - `maia doctor`
  - `maia setup`
  - `maia agent new planner`
  - `maia agent new reviewer`
  - `maia agent setup planner`
  - `maia agent setup reviewer`
  - `maia agent start planner`
  - `maia agent start reviewer`
- Representative live broker-backed conversation and handoff visibility passed in a follow-up fresh-home run:
  - planner sent a live broker-backed request to reviewer
  - reviewer runtime replied with `reply_to_message_id` set to the original request
  - `thread show` reflected the request/reply exchange
  - a file handoff pointer was recorded and visible in both `handoff show` and `thread show`
  - reviewer later confirmed the handoff id and location in a follow-up reply
