# Task 013 - Restore-ready state layout paths

## Goal
- Maia home 아래의 restore-ready state layout을 코드로 고정한다.
- 이번 단계에서는 기존 registry 경로는 유지하면서, export snapshot과 runtime state를 위한 명시적 디렉토리 경로 helper를 추가하고 export 기본 경로를 제공한다.

## Why this slice
- 지금은 registry export/import는 생겼지만, 어디에 portable snapshot을 두고 어디가 runtime-only 인지 코드상 경계가 없다.
- 이 단계에서는 경로 레이아웃만 먼저 고정해서, 이후 backup manifest나 full restore를 붙일 기반을 만든다.

## Non-goals
- registry 기본 저장 위치 migration
- Docker/DB/queue state 저장
- full restore command 추가
- encrypted backup
- timestamp/history rotation 정책 구현

## Allowed files
- `src/maia/app_state.py`
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/013-restore-ready-state-layout-paths.md`

## Acceptance criteria
- [ ] `app_state.py` 에 restore-ready path helper가 추가된다:
  - Maia home
  - registry path (기존 유지)
  - exports dir
  - runtime dir
  - default export path
- [ ] 기본 registry 경로는 계속 `~/.maia/registry.json` 이다.
- [ ] `PYTHONPATH=src python3 -m maia agent export` 를 path 없이 실행하면 default export path로 저장된다.
- [ ] default export path는 `~/.maia/exports/registry.json` 이다.
- [ ] path를 명시한 export는 기존처럼 그대로 동작한다.
- [ ] export 출력에는 실제 저장된 path가 나온다.
- [ ] direct `main(["agent", "export"])` 는 placeholder contract를 유지한다.
- [ ] runtime test가 최소 4개 추가/보강된다:
  - default export path is used when omitted
  - explicit export path still works
  - exports dir helper path under HOME
  - runtime dir helper path under HOME
- [ ] README에 portable vs runtime layout 설명이 최소한으로 추가된다.

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent export`
- `PYTHONPATH=src python3 -m maia agent export <path>`

## Forbidden changes
- registry serialization format 변경
- import semantics 변경
- lifecycle/tune/purge 의미 변경
- registry 기본 위치를 `~/.maia/registry.json` 에서 바꾸기

## Notes
- 이번 task는 state layout의 경로 계약만 다룬다.
- default export path는 single-file snapshot만 제공한다.
- exports dir은 portable snapshot용, runtime dir은 향후 ephemeral/runtime-only state용으로 예약한다.
