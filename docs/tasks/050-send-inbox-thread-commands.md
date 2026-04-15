# Task 050 - send inbox thread commands

## Goal
Phase 3 협업 UX의 핵심인 `send`, `inbox`, `thread` command를 구현한다.

## Scope
### `maia send`
- 새 thread 생성:
  - `maia send <from_agent> <to_agent> --body <text> --topic <topic> [--kind <kind>]`
- 기존 thread로 전송:
  - `maia send <from_agent> <to_agent> --body <text> --thread-id <thread_id> [--kind <kind>]`

### `maia inbox`
- `maia inbox <agent_id> [--limit <n>]`
- 대상 agent가 받은 메시지를 newest-first로 출력

### `maia thread`
- `maia thread <thread_id> [--limit <n>]`
- thread 메타데이터 + 메시지 목록을 chronological order로 출력

## Rules
- `send`는 `--topic` xor `--thread-id`를 요구한다.
- `send`는 from/to agent id가 모두 registry에 존재해야 한다.
- 기존 thread에 보낼 때 sender/recipient는 thread participants에 포함되거나 새 participant로 확장 가능하다.
- thread status는 v1에서 기본 `open`으로 유지한다.

## Validation
- `python3 -m pytest -q tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
