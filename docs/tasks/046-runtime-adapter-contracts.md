# Task 046 - Runtime adapter contracts

## Goal
Phase 2의 runtime plane 계약으로 사용할 runtime adapter interface와 관련 request/result 모델을 정의한다. 실제 Docker 구현은 하지 않는다.

## Non-goals
- Docker SDK/CLI 호출
- broker 구현
- CLI 변경
- process supervision 구현

## Allowed files
- `src/maia/runtime_adapter.py`
- `tests/test_runtime_adapter_contract.py`

## Acceptance criteria
- [x] runtime status enum/model이 정의된다.
- [x] start/stop/status/logs 관련 request/result model이 정의된다.
- [x] runtime adapter interface가 정의된다.
- [x] AgentRecord/RuntimeSpec과 자연스럽게 연결되는 contract다.
- [x] 테스트가 contract shape와 validation을 커버한다.

## Required validation commands
- `python3 -m pytest -q tests/test_runtime_adapter_contract.py`

## Forbidden changes
- CLI 수정
- 실제 Docker 구현
- broker 구현
- registry/storage 수정
