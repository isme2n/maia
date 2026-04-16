# Task 113 — operator visibility for pending threads and recent handoffs

## Goal
- operator가 `thread list`와 관련 visibility surface에서 누가 pending인지, 최근 handoff가 무엇인지, participant runtime 상태가 어떤지 더 직접적으로 볼 수 있게 한다.

## Non-goals
- new CLI verbs
- broker transport 변경
- runtime adapter 변경
- broad docs/help rewrite

## Allowed files
- `src/maia/cli.py`
- `docs/tasks/113-operator-visibility-for-pending-threads-and-recent-handoffs.md`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [x] `thread list`가 pending_on과 participant_runtime을 유지하면서 recent handoff summary를 함께 보여준다.
- [x] `thread show`와 `thread list`의 recent handoff semantics가 어긋나지 않는다.
- [x] running-agent flow에서도 thread list가 recent handoff visibility를 반영한다.
- [x] targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- parser-wide CLI churn
- handoff storage schema changes
- runtime adapter changes
