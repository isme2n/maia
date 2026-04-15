# Task 044 - AgentRecord core identity field validation

## Goal
`AgentRecord`의 핵심 identity/persona 필드(`agent_id`, `name`, `persona`)도 direct construction과 `from_dict()`에서 일관되게 검증한다.

## Non-goals
- payload shape 변경
- 다른 모델 수정
- CLI/registry/storage 수정

## Allowed files
- `docs/tasks/044-agentrecord-core-identity-validation.md`
- `src/maia/agent_model.py`
- `tests/test_agent_model.py`

## Acceptance criteria
- [ ] invalid `agent_id`를 거부한다.
- [ ] invalid `name`을 거부한다.
- [ ] invalid `persona`를 거부한다.
- [ ] direct construction과 `from_dict()`에서 일관되게 동작한다.
- [ ] legacy serialization shape는 유지된다.
- [ ] 회귀 테스트가 추가된다.
- [ ] 지정된 pytest 묶음이 통과한다.

## Required validation commands
- `python3 -m pytest -q tests/test_agent_model.py tests/test_runtime_spec.py tests/test_message_model.py tests/test_handoff_model.py tests/test_presence_model.py`

## Forbidden changes
- 허용 파일 밖 수정
- reviewer 승인 없이 범위 확장
