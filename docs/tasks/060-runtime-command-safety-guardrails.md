# Task 060 - runtime command safety guardrails

## Goal
runtime start/stop/logs/status 경로에서 stale state와 invalid transition을 더 안전하게 다룬다.

## Non-goals
- compose/runtime orchestration 확대
- broker 연동

## Allowed files
- `src/maia/cli.py`
- `src/maia/docker_runtime_adapter.py`
- `tests/test_cli_runtime.py`
- `tests/test_docker_runtime_adapter.py`

## Acceptance criteria
- [ ] 이미 running 상태에서 start 시나리오를 안전하게 처리한다.
- [ ] 이미 stopped 상태에서 stop/logs 경로의 에러가 operator-friendly 하다.
- [ ] stale runtime state가 발견되면 misleading output 대신 명확한 에러/정리 경로를 준다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- 새 daemon/background service 추가
