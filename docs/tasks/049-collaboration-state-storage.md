# Task 049 - Collaboration state storage

## Goal
Thread/message state를 local Maia state에 안전하게 저장/복원하는 storage layer를 추가한다.

## Scope
- 새 collaboration state path 추가
- thread list + message list persistence
- invalid JSON / malformed records clear error handling
- local state와 portable export scope는 분리 유지

## Suggested file surface
- `src/maia/app_state.py`
- `src/maia/collaboration_storage.py`
- `tests/test_collaboration_storage.py`

## Data shape
```json
{
  "threads": [...],
  "messages": [...]
}
```

## Rules
- `ThreadRecord` / `MessageRecord`를 그대로 public model boundary로 사용한다.
- 저장소는 insertion order를 보존한다.
- missing collaboration file은 empty state로 로드한다.
- malformed thread/message entry는 clear error로 거부한다.

## Validation
- `python3 -m pytest -q tests/test_collaboration_storage.py`
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
