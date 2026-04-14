# Task 011 - Registry mutation API cleanup

## Goal
- CLI가 `registry._records` / `registry._order` 내부 구현에 직접 접근하지 않도록, registry에 필요한 최소 mutation API를 추가한다.
- 이번 단계에서는 tune/purge 동작은 그대로 유지하고, 내부 접근만 정리한다.

## Non-goals
- 새 CLI 명령 추가
- storage format 변경
- 상태 전이 정책 변경
- persona-file UX 변경
- DB/queue 도입

## Allowed files
- `src/maia/registry.py`
- `src/maia/cli.py`
- `tests/test_registry.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/011-registry-mutation-api-cleanup.md`

## Acceptance criteria
- [ ] `AgentRegistry` 에 persona 갱신용 public method가 추가된다.
- [ ] `AgentRegistry` 에 purge/remove용 public method가 추가된다.
- [ ] CLI는 더 이상 `registry._records` 나 `registry._order` 에 직접 접근하지 않는다.
- [ ] `tune` 동작은 기존과 동일하다.
- [ ] `purge` 동작은 기존과 동일하다.
- [ ] purge 후 list order 보존은 계속 유지된다.
- [ ] registry unit test가 새 public methods를 직접 검증한다.
- [ ] runtime test는 회귀 없이 계속 통과한다.
- [ ] README가 필요한 범위 내에서만 업데이트된다.

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `python3 -m pytest -q tests/test_registry.py tests/test_cli_runtime.py`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent tune <agent_id> --persona analyst`
- `PYTHONPATH=src python3 -m maia agent archive <agent_id>`
- `PYTHONPATH=src python3 -m maia agent purge <agent_id>`

## Forbidden changes
- agent model 변경
- registry serialization format 변경
- direct `main([...])` placeholder contract 변경
- 새로운 preset/policy 개념 추가

## Notes
- 이번 task는 순수한 내부 구조 정리다.
- public API는 최소한으로만 추가한다.
- 구현은 DRY/YAGNI 원칙으로, CLI 변경은 public API 사용으로 한정한다.
