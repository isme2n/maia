# Task 071 — Workspace show CLI foundation

## Goal
- `maia workspace show <agent_id>`를 추가해서 operator가 해당 agent의 workspace context를 바로 볼 수 있게 만든다.

## Non-goals
- 파일 목록 브라우징
- workspace sync/copy
- remote filesystem inspection

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] `maia workspace show <agent_id>`가 동작한다.
- [ ] runtime spec이 있는 agent면 `workspace`, `runtime_image`, `runtime_command`, `runtime_env_keys` 요약을 보여준다.
- [ ] runtime spec/workspace가 없으면 operator-facing clear error를 준다.
- [ ] 출력은 terse key=value format을 유지한다.
- [ ] help/examples가 추가된다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- Docker runtime adapter implementation
- collaboration storage schema
- export/import files

## Notes
- workspace show는 실제 파일을 나열하는 기능이 아니라 workspace location/context를 보여주는 control-plane surface다.
