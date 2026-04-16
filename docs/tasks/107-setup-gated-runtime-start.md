# Task 107 — setup-gated runtime start

## Goal
- `maia agent start|status|logs`가 agent setup completion과 shared infra readiness를 반영하도록 만들고, runtime launch가 agent별 Hermes home을 실제로 사용하게 한다.

## Non-goals
- Hermes setup passthrough 자체 재설계
- broad runtime lifecycle redesign
- messaging/broker scope expansion
- gateway interactive setup support

## Allowed files
- `README.md`
- `docs/tasks/107-setup-gated-runtime-start.md`
- `src/maia/cli.py`
- `src/maia/docker_runtime_adapter.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_docker_runtime_adapter.py`

## Acceptance criteria
- [x] `agent start`는 shared infra bootstrap이 ready가 아니면 clean operator error로 막힌다.
- [x] `agent start`는 agent setup completion marker가 없거나 incomplete이면 clean operator error로 막힌다.
- [x] successful runtime launch uses the saved per-agent Hermes home/config path in Docker run args.
- [x] `agent status` exposes setup state + runtime state while preserving the operator-facing overall status.
- [x] `agent logs` distinguishes setup-not-done from runtime-not-running.
- [x] targeted tests green
- [x] full verify green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- changing Task 106 passthrough scope
- reintroducing broad internal metadata into `agent list`
- changing broker behavior
- unrelated docs/help cleanup outside Task 107 scope
