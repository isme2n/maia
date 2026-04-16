# Task 115 — runtime network and broker env wiring

## Goal
- Maia runtime containers should join the shared Maia Docker network by default.
- Maia runtime containers should receive broker connection info automatically so real agent runtimes can reach the shared queue without per-agent manual wiring.

## Non-goals
- Implement Hermes-side Maia broker consumers/publishers
- Build or publish a production Hermes runtime image
- Change public Part 2 README/help story
- Add new CLI verbs

## Allowed files
- `src/maia/docker_runtime_adapter.py`
- `src/maia/infra_runtime.py`
- `tests/test_docker_runtime_adapter.py`
- `docs/tasks/115-runtime-network-and-broker-env-wiring.md`

## Acceptance criteria
- [x] Docker runtime adapter adds `--network maia` on `docker run`
- [x] Docker runtime adapter injects a default `MAIA_BROKER_URL` for local shared infra containers
- [x] Explicit `runtime_spec.env["MAIA_BROKER_URL"]` still wins over the default
- [x] Targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_docker_runtime_adapter.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- CLI surface/help churn
- RabbitMQ broker semantics changes
- collaboration/thread storage changes
- speculative Hermes runtime orchestration beyond network/env wiring
