# Task 039 - Handoff and presence models

## Goal
결과물 포인터용 Handoff 모델과 agent runtime 상태용 Presence 모델을 도입한다.

## Non-goals
- broker transport 구현
- docker runtime 구현
- file copy logic 구현
- CLI 구현

## Allowed files
- `src/maia/handoff_model.py`
- `src/maia/presence_model.py`
- `tests/test_handoff_model.py`
- `tests/test_presence_model.py`

## Acceptance criteria
- [ ] `HandoffKind` enum이 정의된다.
- [ ] `HandoffRecord` dataclass가 정의된다.
- [ ] `HandoffRecord`는 최소 `handoff_id`, `thread_id`, `from_agent`, `to_agent`, `kind`, `location`, `summary`, `created_at`를 가진다.
- [ ] `PresenceStatus` enum이 정의된다.
- [ ] `PresenceRecord` dataclass가 정의된다.
- [ ] `PresenceRecord`는 최소 `agent_id`, `runtime_status`, `last_heartbeat_at`를 가진다.
- [ ] `container_id`는 optional이다.
- [ ] 둘 다 `to_dict()` / `from_dict()` round-trip을 지원한다.
- [ ] validation test가 추가된다.

## Required validation commands
- `python3 -m pytest -q tests/test_handoff_model.py tests/test_presence_model.py`

## Forbidden changes
- broker/runtime adapter 구현
- CLI 수정
- registry/storage 수정
