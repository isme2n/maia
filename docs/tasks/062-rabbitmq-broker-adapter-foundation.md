# Task 062 - RabbitMQ broker adapter foundation

## Goal
`src/maia/broker.py` contract를 만족하는 첫 실제 transport adapter를 RabbitMQ 기준으로 추가한다.

## Non-goals
- CLI wiring 완료
- message history migration
- production-grade HA/retry tuning

## Allowed files
- `src/maia/rabbitmq_broker.py` (new)
- `src/maia/broker.py` (필요 시 최소 contract helper만)
- `src/maia/app_state.py` (broker runtime path helper가 정말 필요할 때만)
- `tests/test_rabbitmq_broker.py` (new)
- `tests/test_broker_contract.py` (필요 시 최소 보강)

## Acceptance criteria
- [ ] `MessageBroker` 구현체 `RabbitMQBroker`가 추가된다.
- [ ] publish / pull / ack가 기존 contract shape (`BrokerPublishResult`, `BrokerPullResult`, `BrokerAckResult`)를 지킨다.
- [ ] queue naming은 v1에서 agent inbox 기준으로 단순하고 명확하다.
- [ ] connection/channel/resource cleanup이 테스트로 검증된다.
- [ ] broker unavailable / malformed payload / missing queue 등의 오류가 operator-facing `ValueError`로 정리된다.

## Required validation commands
- `python3 -m pytest -q tests/test_broker_contract.py tests/test_rabbitmq_broker.py`

## Forbidden changes
- CLI surface 변경 끼워넣기
- multi-recipient/broadcast 추가
- unrelated refactor
