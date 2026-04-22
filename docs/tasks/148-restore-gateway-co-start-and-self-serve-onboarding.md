# Task 148 — restore gateway co-start and self-serve onboarding

## Goal
- `maia agent start <name>`가 Maia runtime worker만 띄우는 상태로 회귀한 문제를 복구한다.
- start 시 Hermes gateway bridge도 함께 올라오게 하고, Telegram DM 신규 사용자는 운영자 수동 pairing 없이 self-serve로 바로 대화할 수 있게 복구한다.
- live 상태에서 `token-only` gateway readiness라도 start 후 실제 대화 경로가 살아나도록 worker/bridge/runtime 테스트를 다시 잠근다.

## Non-goals
- speaking style / persona / storage 관련 현재 진행 중 변경의 범위 확대
- Keryx thread/product wording 추가 수정
- 새로운 messaging 플랫폼 추가
- Docker permission 문제 자체 해결

## Allowed files
- `src/maia/hermes_runtime_worker.py`
- `src/maia/hermes_gateway_bridge.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_hermes_gateway_bridge.py`
- `docs/tasks/148-restore-gateway-co-start-and-self-serve-onboarding.md`

## Acceptance criteria
- [ ] `src/maia/hermes_runtime_worker.py`가 gateway readiness가 start-ready(`complete` 또는 `token-only`)일 때 managed child process로 Maia bridge를 띄운다.
- [ ] worker shutdown 시 child gateway/bridge process를 terminate -> wait -> kill fallback으로 정리한다.
- [ ] bridge 엔트리포인트 `src/maia/hermes_gateway_bridge.py`가 존재하고, Hermes gateway 런너 auth 경로를 패치해 Telegram DM self-serve auto-approve를 지원한다.
- [ ] bridge는 `MAIA_GATEWAY_ONBOARDING_MODE`와 `MAIA_GATEWAY_SELF_SERVE_PLATFORMS`를 읽고, 기본 동작은 `self_serve` + `telegram`로 유지한다.
- [ ] 승인 경로는 PairingStore private/public method drift(`approve`, `approve_user`, `_approve_user` 등)와 platform enum/string drift를 견딘다.
- [ ] auto-approve 후에는 원래 auth check를 다시 호출하고, 무조건 `True`를 반환하지 않는다.
- [ ] 테스트가 worker co-start/token-only/self-serve bridge behavior를 모두 잠근다.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_hermes_gateway_bridge.py tests/test_hermes_runtime_worker.py`
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_hermes_gateway_bridge.py`

## Forbidden changes
- `src/maia/cli.py`, `src/maia/agent_setup_session.py` 등 이번 task 범위 밖 파일 수정
- bridge 없이 worker가 직접 unrelated gateway internals를 여기저기 중복 구현
- self-serve 승인 후 원래 auth check를 생략하는 unsafe shortcut
- token-only를 다시 start-blocking으로 되돌리는 변경

## Design notes
- 현재 repo는 dirty worktree이므로 worker/reviewer 모두 이 task의 allowed files만 봐야 한다.
- 기존 live intent는 `maia agent start` 하나로 worker + gateway bridge까지 기동되는 것임.
- bridge는 Hermes upstream을 직접 포크하지 말고 Maia side patch layer로 유지한다.
- first-contact Telegram DM에서는 pairing code를 보여주지 않고 self-serve 승인 후 바로 대화 가능한 상태가 목표다.
- live verification 단계에서는 Docker socket 권한 문제와 product regression을 혼동하지 말고, host-side agent Hermes logs/state도 함께 본다.
- Hermes upstream reference points:
  - gateway runner class: `/home/asle/.hermes/hermes-agent/gateway/run.py:512` (`GatewayRunner`)
  - auth check method: `/home/asle/.hermes/hermes-agent/gateway/run.py:2260` (`_is_user_authorized`)
  - unauthorized DM pairing branch: `/home/asle/.hermes/hermes-agent/gateway/run.py:2400`
  - pairing private approve helper: `/home/asle/.hermes/hermes-agent/gateway/pairing.py:128` (`_approve_user`)
  - gateway entrypoint: `/home/asle/.hermes/hermes-agent/gateway/run.py:8772` (`start_gateway`)
- worker implementation should prefer a minimal bridge patch layer that imports `gateway.run`, patches compatible auth methods on `GatewayRunner`, then calls `start_gateway(...)` rather than reimplementing gateway logic.
- worker runtime should launch `python -m maia.hermes_gateway_bridge` (not plain `hermes gateway run`) when gateway readiness is start-ready.
