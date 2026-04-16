# Task 110 — broker delivery semantics and inbox ack policy hardening

## Goal
- broker inbox의 ack policy를 operator-facing contract로 고정하고, broker mode에서 partial-success나 stale local replay가 live inbox semantics를 흐리지 않게 한다.

## Non-goals
- 새로운 broker 추가
- daemonized consumer loop
- thread/message model 재설계
- runtime lifecycle 변경

## Allowed files
- `src/maia/cli.py`
- `docs/tasks/110-broker-delivery-semantics-and-inbox-ack-policy-hardening.md`
- `tests/test_cli.py`
- `tests/test_rabbitmq_broker.py` (필요 시 최소 보강)

## Acceptance criteria
- [x] broker-backed inbox는 live deliveries가 있을 때 `source=broker ack=after-print`를 유지한다.
- [x] broker-backed inbox는 empty pull일 때 cached local history를 재출력하지 않고 `source=broker ack=complete messages=0`만 출력한다.
- [x] ack failure는 agent context가 포함된 operator-facing 에러로 surface된다.
- [x] broker publish failure 시 send/reply는 local collaboration state를 mutate하지 않는다.
- [x] targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_rabbitmq_broker.py`

## Forbidden changes
- new CLI verbs
- collaboration storage schema 변경
- runtime adapter 변경
- broad docs/help rewrite
