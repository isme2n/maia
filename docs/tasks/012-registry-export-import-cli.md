# Task 012 - Registry export/import CLI

## Goal
- 현재 Maia registry를 사람이 옮길 수 있는 JSON 파일로 export/import 하는 최소 CLI를 추가한다.
- 이 단계의 목적은 복구/이사 방향의 가장 작은 portable path를 만드는 것이다.

## Non-goals
- Docker/queue/DB backup
- merge import
- encrypted export
- multi-file project bundle
- automatic restore workflow

## Allowed files
- `src/maia/cli.py`
- `src/maia/storage.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/012-registry-export-import-cli.md`

## Acceptance criteria
- [ ] `PYTHONPATH=src python3 -m maia agent export <path>` 가 현재 registry JSON을 지정 경로에 쓴다.
- [ ] export 출력은 `exported registry path=<path> agents=<count>` 형식이다.
- [ ] 부모 디렉토리가 없으면 export 경로도 자동 생성된다.
- [ ] `PYTHONPATH=src python3 -m maia agent import <path>` 가 지정 JSON을 읽어 현재 registry를 교체한다.
- [ ] import 출력은 `imported registry path=<path> agents=<count>` 형식이다.
- [ ] 없는 import 파일은 명확한 에러를 반환한다.
- [ ] invalid import JSON 은 기존 storage 에러를 통해 명확히 실패한다.
- [ ] import 후 `list`/`status` 로 복원된 agent를 확인할 수 있다.
- [ ] direct `main(["agent", "export" ...])` / `main(["agent", "import" ...])` placeholder contract 는 유지된다.
- [ ] runtime test가 최소 5개 추가/보강된다:
  - export writes registry file
  - export creates parent dirs
  - import restores exported registry
  - import missing file error
  - import invalid file error

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent export <path>`
- `PYTHONPATH=src python3 -m maia agent import <path>`
- `PYTHONPATH=src python3 -m maia agent list`

## Forbidden changes
- agent model 변경
- registry in-memory semantics 변경
- storage format 변경
- lifecycle/purge/tune 의미 변경
- import를 merge 동작으로 바꾸기

## Notes
- 이번 task의 import는 replace semantics다.
- export/import 포맷은 현재 registry JSON 그대로 사용한다.
- 사람이 git이나 파일 복사로 다루기 쉬운 plain JSON path를 목표로 한다.
