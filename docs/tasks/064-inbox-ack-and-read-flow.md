# Task 064 - inbox ack and read flow

## Goal
broker-backed inbox 읽기 동작에서 ack semantics를 명확히 해서, delivery와 history 조회가 뒤섞이지 않게 만든다.

## Non-goals
- dead-letter queue
- retry backoff 정책
- user-facing multi-step TUI

## Allowed files
- `src/maia/cli.py`
- `src/maia/rabbitmq_broker.py`
- `src/maia/broker.py` (contract helper 최소 보강만)
- `tests/test_cli.py`
- `tests/test_rabbitmq_broker.py`

## Acceptance criteria
- [ ] `inbox`가 pull된 delivery를 중복 없이 다룰 수 있는 최소 ack flow를 가진다.
- [ ] ack 시점 정책이 명시적이다 (예: successful print 후 ack).
- [ ] malformed delivery / ack failure / empty inbox가 구분된 출력/에러로 드러난다.
- [ ] contract tests와 CLI tests가 policy를 고정한다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_rabbitmq_broker.py`

## Forbidden changes
- hidden implicit retries 추가
- thread history storage 제거
- unrelated runtime adapter 수정
