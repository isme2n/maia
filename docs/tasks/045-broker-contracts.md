# Task 045 - Broker contracts

## Goal
Phase 2의 message plane 계약으로 사용할 broker interface와 관련 데이터 구조를 정의한다. 실제 RabbitMQ 구현은 하지 않는다.

## Non-goals
- 실제 네트워크 연결
- RabbitMQ client 도입
- CLI 변경
- runtime adapter 구현

## Allowed files
- `src/maia/broker.py`
- `tests/test_broker_contract.py`

## Acceptance criteria
- [x] broker용 status/result model이 정의된다.
- [x] broker message envelope model이 정의된다.
- [x] broker interface가 정의된다.
- [x] 최소 연산으로 `publish`, `pull/read`, `ack` 또는 그에 준하는 contract가 표현된다.
- [x] thread/message 중심 public model을 해치지 않는다.
- [x] 테스트가 contract shape와 validation을 커버한다.

## Required validation commands
- `python3 -m pytest -q tests/test_broker_contract.py`

## Forbidden changes
- CLI 수정
- 실제 RabbitMQ 구현
- runtime adapter 구현
- registry/storage 수정
