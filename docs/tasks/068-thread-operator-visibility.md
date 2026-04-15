# Task 068 — Thread list/show operator visibility

## Goal
- operator가 열린 collaboration 흐름을 한눈에 볼 수 있도록 `thread list`를 추가하고, `thread show`를 richer control-plane view로 확장한다.

## Non-goals
- new thread state machine
- inbox ack semantics 변경
- agent lifecycle 변경

## Allowed files
- `src/maia/cli_parser.py`
- `src/maia/cli.py`
- `tests/test_cli.py`
- `README.md`

## Acceptance criteria
- [ ] `maia thread list`가 thread overview를 출력한다.
- [ ] `maia thread list --agent <id>`가 participant filter를 지원한다.
- [ ] `maia thread list --status <open|closed>`가 status filter를 지원한다.
- [ ] overview line에 `thread_id`, `topic`, `participants`, `status`, `updated_at`, `pending_on`, `handoffs`, `messages`가 포함된다.
- [ ] `maia thread show <thread_id>`가 existing message history와 함께 thread summary를 richer하게 출력한다.
- [ ] latest message 기준 `pending_on` derivation이 테스트로 고정된다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- broker adapter implementation
- runtime adapter implementation
- portable import/export paths

## Notes
- broad CLI churn은 피한다. 현재 `thread` surface를 최대한 자연스럽게 확장하되 operator UX를 더 명확하게 만든다.
- waiting state는 explicit queue state를 새로 만들지 말고 latest directed message에서 derive하라.
