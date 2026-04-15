# Task 055 - runtime CLI wiring

## Goal
CLI `agent start/stop/status/logs`를 실제 runtime adapter에 연결한다.

## Non-goals
- compose orchestration
- collaboration plane 변경

## Allowed files
- `src/maia/cli_parser.py`
- `src/maia/cli.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/runtime_state_storage.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [ ] `agent start`는 runtime_spec이 있는 agent만 실제 runtime adapter를 통해 시작한다.
- [ ] `agent stop`은 runtime adapter를 통해 종료한다.
- [ ] `agent status`는 registry 상태와 runtime 상태를 함께 보여준다.
- [ ] `agent logs`가 최근 로그를 보여준다.
- [ ] runtime 관련 오류가 한 줄 error contract로 출력된다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- import/export semantics 변경
- broker/message behavior 변경
