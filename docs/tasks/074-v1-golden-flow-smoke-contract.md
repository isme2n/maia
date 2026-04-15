# Task 074 — v1 golden-flow smoke contract and operator examples

## Goal
- Maia v1의 대표 operator flow를 문서와 테스트 기준으로 고정한다.

## Non-goals
- 새 기능 추가
- daemon/orchestrator 추가

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] create -> tune -> start -> send/reply -> handoff -> thread/workspace -> status/logs 흐름이 명시적 smoke 계약으로 정리된다.
- [ ] README/top-level help/operator examples가 이 흐름을 일관되게 보여준다.
- [ ] integration test 또는 smoke-style test가 이 흐름을 잠근다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- broker adapter files
- runtime adapter files
- storage schema files
