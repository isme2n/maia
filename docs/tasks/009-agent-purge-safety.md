# Task 009 - Agent purge safety

## Goal
- `maia agent purge <agent_id>` 를 실제 동작으로 연결하되, archived 상태의 agent만 삭제할 수 있게 안전장치를 둔다.
- purge는 registry에서 agent를 완전히 제거하는 hard delete로 정의한다.

## Non-goals
- Docker/Compose 리소스 정리
- purge 확인 프롬프트 추가
- multi-agent bulk purge
- archive 정책 변경
- memory/export/import 구현

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/009-agent-purge-safety.md`

## Acceptance criteria
- [ ] `PYTHONPATH=src python3 -m maia agent purge <agent_id>` 가 archived 상태 agent를 registry에서 삭제한다.
- [ ] archived가 아닌 agent를 purge하려고 하면 명확한 에러를 반환한다.
- [ ] 없는 agent_id 를 purge하려고 하면 명확한 에러를 반환한다.
- [ ] purge 성공 출력은 `purged agent_id=<id>` 형식이다.
- [ ] purge 후 `list` 에서 해당 agent가 보이지 않는다.
- [ ] purge 후 `status <agent_id>` 는 not found 에러를 반환한다.
- [ ] purge는 다른 agent들의 순서를 깨지 않는다.
- [ ] direct `main(["agent", "purge", ...])` placeholder contract 는 유지된다.
- [ ] 테스트가 최소 5개 추가/보강된다:
  - purge archived agent succeeds
  - purge running agent rejected
  - purge stopped agent rejected
  - purge missing agent error
  - purge preserves remaining list order

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent archive <agent_id>`
- `PYTHONPATH=src python3 -m maia agent purge <agent_id>`
- `PYTHONPATH=src python3 -m maia agent list`
- `PYTHONPATH=src python3 -m maia agent status <agent_id>`

## Forbidden changes
- agent model 변경
- registry API 변경
- storage format 변경
- start/stop/archive/restore 의미 변경
- purge를 archived 외 상태에서도 허용하도록 완화

## Notes
- 이번 task는 hard delete 정책만 다룬다.
- 구현은 기존 registry/storage 흐름을 재사용하되, 필요하면 CLI 레벨에서 안전정책을 강제한다.
- direct `main([...])` placeholder contract를 잠그는 테스트를 같이 추가한다.
