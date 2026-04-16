# Task 106 — agent setup passthrough for hermes setup

## Goal
- `maia agent setup <name>`를 실제로 동작시켜서, agent별 dedicated Hermes home/context에서 `hermes setup` interactive flow를 실행한다.

## Non-goals
- Maia가 Hermes setup wizard를 재구현하는 것
- start gating까지 이번 태스크에서 확장하는 것
- runtime image / broker wiring 확장
- gateway/chat surface에서 interactive setup 지원

## Allowed files
- `README.md`
- `docs/tasks/106-agent-setup-passthrough-for-hermes-setup.md`
- `src/maia/agent_setup_session.py`
- `src/maia/app_state.py`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [ ] `maia agent setup <name>`가 clean placeholder가 아니라 실제 Hermes setup passthrough를 실행한다.
- [ ] agent별 dedicated Hermes home path가 준비된다.
- [ ] successful setup이면 setup completion marker가 저장된다.
- [ ] failed/interrupted setup이면 incomplete marker가 저장되고 rerun guidance가 나온다.
- [ ] public help/README wording이 더 이상 “next task” placeholder를 말하지 않는다.
- [ ] targeted tests green
- [ ] full verify green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- agent start gating 구현
- broad runtime adapter refactors unrelated to setup marker persistence
- Hermes wizard screen parsing/reformatting
- new team/model/provider setup UX in Maia
