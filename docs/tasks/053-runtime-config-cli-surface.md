# Task 053 - runtime config CLI surface

## Goal
`agent tune`를 통해 `runtime_spec`를 설정/수정/제거할 수 있게 한다.

## Non-goals
- 실제 Docker 실행
- runtime state persistence

## Allowed files
- `src/maia/cli_parser.py`
- `src/maia/cli.py`
- `src/maia/registry.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [ ] `agent tune`에서 runtime spec 변경 플래그를 받을 수 있다.
- [ ] 최소 항목은 `image`, `workspace`, `command`, `env`다.
- [ ] runtime spec 전체 제거 플래그를 제공한다.
- [ ] 기존 persona/profile tune surface와 충돌 없이 동작한다.
- [ ] registry persistence에 runtime spec이 저장된다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- broker/message plane 변경
- start/stop real runtime wiring 선행
