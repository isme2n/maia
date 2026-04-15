# Task 076 — Handoff/workspace/status/logs operator-link hardening

## Goal
- operator가 thread/handoff/workspace/status/logs 사이를 자연스럽게 오갈 수 있게 출력과 연결 정보를 다듬는다.

## Non-goals
- file sync
- new runtime features

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] thread/handoff/workspace/status/logs 사이 operator-facing linkage가 명확하다.
- [ ] field naming과 wording이 handoff-first로 일관된다.
- [ ] logs/status 확인이 golden flow 예시 안에 자연스럽게 들어간다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- runtime adapter implementation
- broker adapter implementation
- export/import files
