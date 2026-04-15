# Task 041 - Phase 1 model constructor hardening

## Goal
Phase 1 core models의 public constructor 경로가 `from_dict()`와 같은 수준의 불변성/방어 복사 규칙을 보장하도록 강화한다.

## Non-goals
- CLI 변경
- registry/storage 변경
- 새로운 모델 추가
- payload shape 변경

## Allowed files
- `docs/tasks/041-phase1-model-constructor-hardening.md`
- `src/maia/agent_model.py`
- `src/maia/runtime_spec.py`
- `src/maia/message_model.py`
- `tests/test_agent_model.py`
- `tests/test_runtime_spec.py`
- `tests/test_message_model.py`

## Acceptance criteria
- [ ] `ThreadRecord.participants`는 생성 시 외부 리스트와 alias되지 않는다.
- [ ] `AgentRecord` direct construction은 invalid status를 허용하지 않는다.
- [ ] `RuntimeSpec` direct construction은 invalid image/workspace/command/env를 허용하지 않는다.
- [ ] 기존 legacy serialization shape는 유지된다.
- [ ] 추가 회귀 테스트가 들어간다.
- [ ] 지정된 pytest 묶음이 통과한다.

## Required validation commands
- `python3 -m pytest -q tests/test_agent_model.py tests/test_runtime_spec.py tests/test_message_model.py tests/test_handoff_model.py tests/test_presence_model.py`

## Forbidden changes
- 허용 파일 밖 수정
- reviewer 승인 없이 범위 확장
