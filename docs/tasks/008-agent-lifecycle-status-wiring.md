# Task 008 - Agent lifecycle status wiring

## Goal
- `maia agent start|stop|archive|restore` 를 실제 registry 상태 전이로 연결한다.
- 이번 단계에서는 Docker 없이 registry 상태값만 변경하고 출력한다.

## Non-goals
- Docker/Compose 컨테이너 제어
- purge 구현
- persona 변경 기능 확장
- 스케줄러/auto-start 구현
- 다중 프로세스 동시성 처리

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/008-agent-lifecycle-status-wiring.md`

## Acceptance criteria
- [ ] `PYTHONPATH=src python3 -m maia agent start <agent_id>` 가 `running` 으로 바꾼다.
- [ ] `PYTHONPATH=src python3 -m maia agent stop <agent_id>` 가 `stopped` 로 바꾼다.
- [ ] `PYTHONPATH=src python3 -m maia agent archive <agent_id>` 가 `archived` 로 바꾼다.
- [ ] `PYTHONPATH=src python3 -m maia agent restore <agent_id>` 가 `stopped` 로 바꾼다.
- [ ] 없는 agent_id 는 각 명령에서 명확한 에러를 반환한다.
- [ ] 성공 출력은 `updated agent_id=<id> status=<status>` 형식이다.
- [ ] `status` 와 `list` 는 변경된 상태를 그대로 반영한다.
- [ ] direct `main([...])` placeholder contract 는 유지된다.
- [ ] runtime test가 최소 5개 추가/보강된다:
  - start sets running
  - stop sets stopped after start
  - archive sets archived
  - restore sets stopped after archive
  - missing agent error for one lifecycle command

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent start <agent_id>`
- `PYTHONPATH=src python3 -m maia agent archive <agent_id>`
- `PYTHONPATH=src python3 -m maia agent restore <agent_id>`
- `PYTHONPATH=src python3 -m maia agent status <agent_id>`

## Forbidden changes
- agent model 변경
- registry API 변경
- storage format 변경
- Docker/Compose 코드 추가
- purge 의미 변경

## Notes
- 이번 task는 상태값 연결만 다룬다.
- 상태 전이는 단순하게 처리한다:
  - start -> running
  - stop -> stopped
  - archive -> archived
  - restore -> stopped
- 복잡한 상태 검증 규칙은 다음 단계로 미룬다.
