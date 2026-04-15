# Task 047 - Phase 2 contract hardening

## Goal
Phase 2 계약에서 남은 abstraction leak와 operation-specific semantics 누수를 정리한다.

## Non-goals
- 실제 RabbitMQ 구현
- 실제 Docker 구현
- CLI 변경
- 다른 모델 수정

## Allowed files
- `docs/tasks/047-phase2-contract-hardening.md`
- `src/maia/broker.py`
- `src/maia/runtime_adapter.py`
- `tests/test_broker_contract.py`
- `tests/test_runtime_adapter_contract.py`

## Acceptance criteria
- [x] runtime contract에서 Docker-specific `container_id` public naming을 제거하거나 일반화한다.
- [x] broker result model이 operation-specific status semantics를 가진다.
- [x] invalid status/result combinations를 거부한다.
- [x] 테스트가 새 semantics를 검증한다.
- [x] 지정된 pytest 묶음이 통과한다.

## Required validation commands
- `python3 -m pytest -q tests/test_broker_contract.py tests/test_runtime_adapter_contract.py`

## Forbidden changes
- 허용 파일 밖 수정
- 실제 transport/runtime 구현
