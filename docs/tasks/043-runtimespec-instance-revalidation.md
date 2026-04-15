# Task 043 - RuntimeSpec instance revalidation in AgentRecord

## Goal
`AgentRecord`가 `RuntimeSpec` 인스턴스를 직접 받을 때도 재검증을 거치도록 해서 constructor parity를 완성한다.

## Non-goals
- payload shape 변경
- 다른 모델 수정
- CLI/registry/storage 수정

## Allowed files
- `docs/tasks/043-runtimespec-instance-revalidation.md`
- `src/maia/agent_model.py`
- `tests/test_agent_model.py`

## Acceptance criteria
- [ ] mutated invalid `RuntimeSpec` instance를 `AgentRecord` direct construction이 거부한다.
- [ ] valid `RuntimeSpec` instance는 계속 허용된다.
- [ ] legacy serialization shape는 유지된다.
- [ ] 회귀 테스트가 추가된다.
- [ ] 지정된 pytest 묶음이 통과한다.

## Required validation commands
- `python3 -m pytest -q tests/test_agent_model.py tests/test_runtime_spec.py tests/test_message_model.py tests/test_handoff_model.py tests/test_presence_model.py`

## Forbidden changes
- 허용 파일 밖 수정
- reviewer 승인 없이 범위 확장
