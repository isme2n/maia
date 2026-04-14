# Task 007 - Agent tune/persona wiring

## Goal
- `maia agent tune` 를 실제 동작으로 연결해서 agent의 persona만 안전하게 수정할 수 있게 한다.
- 이번 단계에서는 SOUL/모델/툴 정책 같은 다른 설정은 건드리지 않고, persona 문자열만 저장/조회한다.

## Non-goals
- SOUL 수정 기능
- start/stop/archive/restore/purge 구현
- persona 파일 분리 저장
- multi-line editor / interactive prompt
- 모델/툴 정책 변경

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/007-agent-tune-persona.md`

## Acceptance criteria
- [ ] `PYTHONPATH=src python3 -m maia agent tune <agent_id> --persona <text>` 가 동작한다.
- [ ] `tune` 는 기존 agent가 없으면 명확한 에러를 반환한다.
- [ ] `tune` 는 persona 필드만 변경하고, name/status/agent_id 는 유지한다.
- [ ] `tune` 성공 시 `updated agent_id=<id> persona=<persona>` 형식으로 출력한다.
- [ ] `status` 는 수정된 persona를 그대로 출력한다.
- [ ] `list` 출력 형식은 기존 그대로 유지한다.
- [ ] 빈 문자열 persona도 허용해서 초기화/삭제 용도로 쓸 수 있다.
- [ ] placeholder 명령의 의미는 바꾸지 않는다.
- [ ] runtime test가 최소 4개 추가/보강된다:
  - tune updates persona for existing agent
  - tune preserves name/status
  - tune missing agent error
  - tune empty persona clears value

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent tune <agent_id> --persona analyst`
- `PYTHONPATH=src python3 -m maia agent status <agent_id>`

## Forbidden changes
- agent model 변경
- registry API 변경
- storage format 변경
- start/stop/archive/restore/purge 의미 변경
- persona 외 다른 설정 필드 추가

## Notes
- 이번 task의 핵심은 "안전하게 persona만 수정"이다.
- 구현은 기존 registry/storage 흐름을 그대로 재사용한다.
- `main([...])` placeholder contract는 유지하고, 실제 module entrypoint(`python -m maia`)에서만 runtime 동작을 연결한다.
