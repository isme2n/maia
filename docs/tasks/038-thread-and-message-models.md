# Task 038 - Thread and message models

## Goal
Maia의 협업 중심 모델인 Thread와 Message를 도입한다. Message는 v1에서 단일 `to_agent`만 지원한다.

## Non-goals
- handoff/presence 구현
- broker 구현
- CLI 구현
- broadcast 지원

## Allowed files
- `src/maia/message_model.py`
- `tests/test_message_model.py`

## Acceptance criteria
- [ ] `ThreadRecord` dataclass가 정의된다.
- [ ] `ThreadRecord`는 최소 `thread_id`, `topic`, `participants`, `created_by`, `status`, `created_at`, `updated_at`를 가진다.
- [ ] `MessageKind` enum이 정의된다.
- [ ] `MessageRecord` dataclass가 정의된다.
- [ ] `MessageRecord`는 최소 `message_id`, `thread_id`, `from_agent`, `to_agent`, `kind`, `body`, `created_at`를 가진다.
- [ ] `reply_to_message_id`는 optional이다.
- [ ] `to_agent`는 단일 문자열만 허용한다.
- [ ] thread/message 모두 `to_dict()` / `from_dict()` round-trip을 지원한다.
- [ ] validation test가 추가된다.

## Required validation commands
- `python3 -m pytest -q tests/test_message_model.py`

## Forbidden changes
- agent_model 수정
- handoff/presence 구현
- CLI 수정
