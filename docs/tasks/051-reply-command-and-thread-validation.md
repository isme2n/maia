# Task 051 - reply command and thread-aware validation

## Goal
기존 메시지에 대한 빠른 응답 UX와 thread-aware validation을 추가한다.

## Scope
### `maia reply`
- `maia reply <message_id> --from-agent <agent_id> --body <text> [--kind <kind>]`
- reply target message를 찾아 같은 thread에 새 메시지를 추가한다.
- 기본 응답 대상(`to_agent`)은 원본 message의 `from_agent`다.

## Rules
- 원본 message가 존재해야 한다.
- `from-agent`는 원본 thread participant여야 한다.
- `from-agent`는 원본 message의 `to_agent`와 같아야 한다. v1에서는 direct reply만 허용한다.
- `reply_to_message_id`는 원본 message id로 채운다.
- 기본 kind는 `answer`.

## Validation
- `python3 -m pytest -q tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
