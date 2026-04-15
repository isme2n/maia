# Task 048 - Phase 3 collaboration CLI surface

## Goal
Phase 3에서 Maia를 실제 협업형 control plane으로 느끼게 만드는 최소 CLI surface를 추가한다.

## Scope
이번 Phase 3에서 구현할 public commands:
- `maia send`
- `maia inbox`
- `maia thread`
- `maia reply`

## Product rules
- 기존 agent lifecycle verbs(`new/start/stop/archive/restore/list/status/tune/purge`)는 유지한다.
- 협업 UX는 queue/job이 아니라 thread/message 중심으로 노출한다.
- `send`는 새 thread 생성 또는 기존 thread에 direct message 추가를 표현한다.
- `reply`는 기존 message를 기준으로 같은 thread 안에서 응답 message를 만든다.
- `inbox`는 특정 agent가 받은 메시지 목록을 보여준다.
- `thread`는 thread 메타데이터와 해당 thread의 메시지 흐름을 보여준다.

## Out of scope
- 실제 RabbitMQ transport
- 실제 runtime adapter 연동
- read/ack semantics
- message deletion/editing
- attachment payload 저장

## Output contract principles
- 현재 Maia CLI 스타일을 유지한다.
- 한 줄 key=value 출력 위주로 간결하게 유지한다.
- preview/import 쪽처럼 whitespace-safe encoding을 유지한다.

## Required validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`

## Follow-up tasks
- Task 049: collaboration state storage
- Task 050: send/inbox/thread commands
- Task 051: reply command and thread-aware validation
