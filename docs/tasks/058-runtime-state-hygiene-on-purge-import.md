# Task 058 - runtime state hygiene on purge/import

## Goal
purge/import 후 dangling runtime state가 남지 않도록 정리한다.

## Non-goals
- actual docker cleanup orchestration
- CLI public surface expansion

## Allowed files
- `src/maia/runtime_state_storage.py`
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- 필요 시 관련 최소 범위 파일

## Acceptance criteria
- [ ] agent purge 시 해당 agent의 runtime state가 제거된다.
- [ ] import로 registry가 교체될 때 존재하지 않는 agent의 runtime state는 정리된다.
- [ ] status/logs가 dangling runtime state 때문에 잘못된 결과를 내지 않는다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli_runtime.py`

## Forbidden changes
- docker runtime adapter public contract 변경
