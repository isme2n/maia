# Task 111 — broker pull merge into local collaboration cache/thread state

## Goal
- broker pull 결과를 local collaboration cache/thread state에 merge하는 contract를 더 강하게 잠가서, reply/thread continuity와 thread visibility가 broker delivery 이후에도 안정적으로 유지되게 한다.

## Non-goals
- broker ack semantics 재작업
- new CLI verbs
- collaboration storage schema 변경
- runtime lifecycle 변경

## Allowed files
- `src/maia/cli.py`
- `docs/tasks/111-broker-pull-merge-into-local-collaboration-cache-thread-state.md`
- `tests/test_cli.py`

## Acceptance criteria
- [x] broker-delivered message는 local cache merge 후 `reply <message_id>` continuity를 유지한다.
- [x] merge는 existing thread의 missing topic / participants / updated_at을 올바르게 보강한다.
- [x] duplicate broker delivery는 local collaboration state에 duplicate message를 만들지 않는다.
- [x] thread visibility는 merged broker message context를 반영한다.
- [x] targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- new transport adapter
- runtime adapter changes
- broad README/help rewrite
