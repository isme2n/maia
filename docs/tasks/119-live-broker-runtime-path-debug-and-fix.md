# Task 119 — live broker runtime path debug and fix

## Goal
- Close the remaining live blocker after Task 118 by making a real running Maia runtime worker consume broker messages and publish replies successfully in fresh-home host validation.
- Keep the fix tightly scoped to the live broker/runtime path rather than broad product-story changes.

## Root symptom
- Task 118 code/tests/review are green, but fresh-home live validation still fails:
  - `maia agent start reviewer` succeeds
  - planner sends a live request
  - reviewer runtime container stays running
  - planner never receives a reply
  - thread shows only the request message
- Container logs are empty, so the failure path is not yet visible through current operator surfaces.

## Likely investigation targets
- default runtime broker URL injected into containers
- difference between host-side broker endpoint and container-side broker endpoint
- whether Maia injects a display-redacted broker URL into real runtime env instead of a usable AMQP URL
- worker pull / publish / ack path under the real container runtime

## Non-goals
- New public CLI commands
- Broad SQLite/context-layer redesign
- PostgreSQL migration
- RabbitMQ contract redesign
- README/help churn

## Allowed files
- `src/maia/infra_runtime.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/hermes_runtime_worker.py`
- `tests/test_docker_runtime_adapter.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_cli_runtime.py`
- `scripts/rebuild-runtime-worker-image.sh`
- `docs/tasks/119-live-broker-runtime-path-debug-and-fix.md`

## Acceptance criteria
- [x] Real runtime containers receive a usable non-redacted broker URL for actual AMQP connections
- [x] Fresh-home live runtime validation succeeds for request -> reply with a running reviewer worker
- [x] Existing targeted tests stay green
- [x] A regression test locks the broker URL/runtime path that caused the live failure
- [x] Scoped review approves the change

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_docker_runtime_adapter.py tests/test_hermes_runtime_worker.py tests/test_cli_runtime.py`
- Fresh-home live smoke:
  - `maia setup`
  - `maia agent new planner`
  - `maia agent new reviewer`
  - `maia agent setup planner`
  - `maia agent setup reviewer`
  - `maia agent start reviewer`
  - send live request to reviewer
  - planner receives reply via broker-backed inbox pull

## Forbidden changes
- Broad dirty-repo cleanup outside allowed files
- Weakening docs instead of fixing the runtime path
- Requiring manual per-run runtime-env overrides as the primary happy path fix

## Closeout evidence
- Investigation result:
  - the live blocker was a stale local Docker image for `maia-local/hermes-worker:latest`
  - the running container still had the old `WorkerConfig` shape and did not include the Task 118 self-discovery code
  - this was confirmed by running Python inside the live container and observing `WorkerConfig.__init__() got an unexpected keyword argument 'state_db_path'`
- Remediation:
  - rebuilt `maia-local/hermes-worker:latest` from the current `/home/asle/maia` source tree
  - added `scripts/rebuild-runtime-worker-image.sh` so future live smokes can rebuild and freshness-check the runtime image against the current git revision before validation
- Fresh-home live validation passed after rebuild:
  - reviewer runtime started successfully
  - reviewer replied to planner over the broker
  - the reply referenced the dynamically added `researcher` agent without the operator spelling out the roster in the message body
  - `thread show` reflected both the request and the reply
- Representative reply evidence:
  - reviewer answered with the known agents list including `planner`, `reviewer`, and `researcher`
  - reviewer correctly marked only itself as `running`
