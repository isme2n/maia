# Task 054 - docker runtime adapter foundation

## Goal
실제 `RuntimeAdapter` 구현체와 runtime state storage를 추가한다.

## Non-goals
- CLI wiring 전체 완성
- compose orchestration

## Allowed files
- `src/maia/runtime_adapter.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/runtime_state_storage.py`
- `src/maia/app_state.py`
- `tests/test_runtime_adapter_contract.py`
- `tests/test_docker_runtime_adapter.py`

## Acceptance criteria
- [ ] `DockerRuntimeAdapter`가 `start/stop/status/logs`를 구현한다.
- [ ] subprocess 기반 Docker CLI invocation을 사용한다.
- [ ] fake docker binary로 테스트 가능해야 한다.
- [ ] runtime state persistence가 도입된다.
- [ ] Docker 미설치/command failure 경로를 명확히 에러 처리한다.

## Required validation commands
- `python3 -m pytest -q tests/test_runtime_adapter_contract.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- CLI public surface 대규모 개편
- broker 구현 착수
