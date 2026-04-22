# Task 149 — runtime container HOME/XDG env for gateway bridge

## Goal
- Task 148로 worker+gateway bridge co-start는 복구됐지만, live container에서 gateway가 `/.local/state/hermes/gateway-locks`를 만들려다 permission denied로 바로 죽는 문제를 닫는다.
- Maia Docker runtime가 Hermes gateway/lock/state 경로를 쓸 수 있도록 runtime container env를 제품 수준으로 고정한다.

## Non-goals
- gateway bridge/self-serve logic 재설계
- CLI gating 재변경
- unrelated runtime image packaging changes
- host Docker 권한 문제 해결

## Allowed files
- `src/maia/docker_runtime_adapter.py`
- `tests/test_docker_runtime_adapter.py`
- `docs/tasks/149-runtime-container-home-xdg-env-for-gateway-bridge.md`

## Acceptance criteria
- [ ] Docker runtime adapter가 Maia worker container 시작 시 Hermes runtime이 writable state/cache/home 경로를 갖도록 env를 주입한다.
- [ ] 최소한 live failure였던 `/.local/...` 경로 접근이 재발하지 않도록 `HOME`이 명시적으로 container-writable 경로로 잡힌다.
- [ ] 필요하다면 `XDG_STATE_HOME` 등도 함께 주입해 gateway scoped lock/state가 writable 경로로 향하게 한다.
- [ ] 기존 HERMES_HOME mount 계약(`/maia/hermes`)은 유지한다.
- [ ] docker argv 검증 테스트가 새 env를 잠근다.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_docker_runtime_adapter.py`
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`

## Forbidden changes
- worker/bridge/auth logic 수정
- runtime image build script 수정
- broad CLI/docs cleanup

## Design notes
- live failure evidence from `docker logs 90e271...`:
  - `PermissionError: [Errno 13] Permission denied: '/.local'`
  - traceback showed Hermes gateway lock path creation under `/.local/state/hermes/gateway-locks`
- current Docker runtime adapter already injects `HERMES_HOME=/maia/hermes` but not container `HOME`.
- fix should be general for Maia-managed Hermes workers, not a one-off per-agent env tweak.
- prefer stable writable paths under `/maia/hermes` so mounted agent-scoped state survives restart and stays host-visible.
