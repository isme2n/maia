# Task 040 - Phase 1 final review aliasing fix

## Goal
- `AgentRecord`와 `RuntimeSpec`의 중첩 가변 상태 별칭을 제거해 복사본끼리 `tags`, `runtime_spec.command`, `runtime_spec.env`, `messaging_spec`를 공유하지 않게 만든다.

## Non-goals
- registry/storage/CLI 동작 변경
- 직렬화 payload shape 확장 또는 축소
- 다른 모델의 구조 변경

## Allowed files
- `docs/tasks/040-phase1-final-review-aliasing-fix.md`
- `src/maia/agent_model.py`
- `src/maia/runtime_spec.py`
- `tests/test_agent_model.py`
- `tests/test_runtime_spec.py`

## Acceptance criteria
- [ ] `AgentRecord` 생성 및 복사 시 `tags`, `runtime_spec`, `messaging_spec`가 방어 복사된다.
- [ ] `RuntimeSpec` 생성 및 복사 시 `command`, `env`가 방어 복사된다.
- [ ] 기존 legacy 직렬화 shape는 유지된다.
- [ ] 중첩 복사본이 원본과 상태를 공유하지 않음을 증명하는 회귀 테스트가 추가된다.
- [ ] 지정된 pytest 묶음이 통과한다.

## Required validation commands
- `python3 -m pytest -q tests/test_agent_model.py tests/test_runtime_spec.py tests/test_message_model.py tests/test_handoff_model.py tests/test_presence_model.py`

## Forbidden changes
- 허용 파일 밖 수정
- reviewer 결과 없이 범위 확장

## Notes
- 최종 reviewer Codex 단계는 별도 세션/위임 승인 시 수행한다.
