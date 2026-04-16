# Task 112 — running-agent multi-turn conversation regression flow

## Goal
- 실제 running agent 2개가 request → inbox → answer → inbox → handoff → thread/status/logs visibility로 이어지는 multi-turn flow를 regression으로 잠근다.

## Non-goals
- broker transport 구현 변경
- daemonized agent loop 추가
- CLI surface redesign
- runtime adapter 구현 변경

## Allowed files
- `docs/tasks/112-running-agent-multi-turn-conversation-regression-flow.md`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [x] running agent 두 개가 request/answer 왕복 흐름을 통합 regression으로 가진다.
- [x] reviewer inbox와 planner inbox가 각각 올바른 message context를 보여준다.
- [x] thread visibility가 running participant_runtime / pending_on / handoff state를 반영한다.
- [x] status/logs visibility가 conversation flow 이후에도 유지된다.
- [x] targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py`

## Forbidden changes
- production runtime adapter changes
- broker adapter changes
- parser/help/docs broad rewrite
