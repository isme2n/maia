# Task 066 — Collaboration storage v2 with handoff persistence

## Goal
- `CollaborationStorage`가 thread/message와 함께 `HandoffRecord`도 저장/복원할 수 있게 만든다.
- 기존 `collaboration.json`에 `handoffs` 키가 없어도 backward-compatible 하게 로드되게 유지한다.

## Non-goals
- artifact CLI 추가
- thread output 변경
- export/import bundle scope 확장

## Allowed files
- `src/maia/collaboration_storage.py`
- `tests/test_collaboration_storage.py`
- `tests/test_handoff_model.py`

## Acceptance criteria
- [ ] `CollaborationState`가 `handoffs`를 포함한다.
- [ ] 저장 시 `handoffs` 배열이 JSON에 직렬화된다.
- [ ] 로드 시 `handoffs`가 없으면 빈 리스트로 처리된다.
- [ ] invalid handoff record는 clear error로 surface 된다.
- [ ] 기존 thread/message round-trip 테스트가 유지된다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_collaboration_storage.py tests/test_handoff_model.py`

## Forbidden changes
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- broker/runtime adapter files

## Notes
- existing collaboration state file users를 깨지 않도록 `handoffs` missing path를 명시적으로 허용한다.
- artifact payload를 JSON에 넣지 말고 existing `HandoffRecord` 그대로 pointer metadata만 저장한다.
