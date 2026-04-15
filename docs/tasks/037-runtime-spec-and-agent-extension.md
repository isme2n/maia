# Task 037 - Runtime spec and agent extension

## Goal
AgentRecord를 runtime/messaging 확장이 가능한 형태로 넓히고, 별도 RuntimeSpec 모델을 도입한다.

## Non-goals
- thread/message/handoff/presence 구현
- broker 구현
- docker 실행 구현
- CLI 명령 추가

## Allowed files
- `src/maia/agent_model.py`
- `src/maia/runtime_spec.py`
- `tests/test_agent_model.py`
- `tests/test_runtime_spec.py`

## Acceptance criteria
- [ ] `RuntimeSpec` dataclass가 새 파일에 정의된다.
- [ ] `RuntimeSpec`은 최소 `image`, `workspace`, `command`, `env`를 가진다.
- [ ] `RuntimeSpec`은 `to_dict()` / `from_dict()` round-trip을 지원한다.
- [ ] `AgentRecord`가 `runtime_spec`과 `messaging_spec`을 선택 필드로 가진다.
- [ ] 기존 agent round-trip은 유지된다.
- [ ] 새 필드가 있어도 기존 직렬화/역직렬화가 깨지지 않는다.
- [ ] 새 테스트가 추가된다.

## Required validation commands
- `python3 -m pytest -q tests/test_agent_model.py tests/test_runtime_spec.py`

## Forbidden changes
- 다른 모델 파일 추가
- CLI 수정
- registry/storage 수정
