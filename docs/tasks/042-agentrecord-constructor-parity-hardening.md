# Task 042 - AgentRecord constructor parity hardening

## Goal
`AgentRecord` direct construction 경로가 `from_dict()`와 동일하게 `role`, `model`, `tags`, `runtime_spec`, `messaging_spec`를 검증하도록 맞춘다.

## Non-goals
- payload shape 변경
- 다른 모델 수정
- CLI/registry/storage 수정

## Allowed files
- `docs/tasks/042-agentrecord-constructor-parity-hardening.md`
- `src/maia/agent_model.py`
- `tests/test_agent_model.py`

## Acceptance criteria
- [ ] direct construction에서 invalid `role`/`model`을 거부한다.
- [ ] direct construction에서 invalid `tags`를 거부한다.
- [ ] direct construction에서 invalid `runtime_spec`를 거부한다.
- [ ] direct construction에서 invalid `messaging_spec`를 거부한다.
- [ ] 기존 legacy serialization shape는 유지된다.
- [ ] 관련 회귀 테스트가 추가된다.
- [ ] 지정된 pytest 묶음이 통과한다.

## Required validation commands
- `python3 -m pytest -q tests/test_agent_model.py tests/test_runtime_spec.py tests/test_message_model.py tests/test_handoff_model.py tests/test_presence_model.py`

## Forbidden changes
- 허용 파일 밖 수정
- reviewer 승인 없이 범위 확장
