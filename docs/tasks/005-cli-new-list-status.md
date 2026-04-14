# Task 005 - CLI wiring for new/list/status

## Goal
- Maia CLI를 실제 registry/storage 계층과 연결해서 최소한의 end-to-end 동작을 만든다.
- 이번 단계에서는 `new`, `list`, `status`만 실제 동작시키고 나머지 명령은 placeholder로 유지한다.

## Why this slice
- 현재 Maia에는 CLI 골격, agent 모델, registry, JSON persistence가 이미 있다.
- 가장 작은 실제 사용자 흐름은 `new -> list -> status`다.
- `start/stop/archive/restore/tune/purge`까지 한 번에 연결하면 상태 전이/정책 범위가 너무 커진다.

## Non-goals
- `start`, `stop`, `archive`, `restore`, `tune`, `purge` 구현
- Docker/Compose 연동
- queue/DB 연동
- 복잡한 표 출력
- 멀티 유저/멀티 프로세스 동시성 처리

## Allowed files
- `src/maia/cli.py`
- `src/maia/app_state.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] 기본 registry 파일 경로는 `~/.maia/registry.json` 이다.
- [ ] 부모 디렉토리가 없으면 자동 생성된다.
- [ ] `PYTHONPATH=src python3 -m maia agent new <name>` 가 동작한다.
- [ ] `new`는 새로운 agent를 생성하고 기본 상태를 `stopped`로 저장한다.
- [ ] `new`는 기본 persona를 빈 문자열로 저장한다.
- [ ] `new` 결과로 생성된 agent의 `agent_id`, `name`, `status`를 출력한다.
- [ ] 중복 name 생성은 명확한 에러로 거부된다.
- [ ] `PYTHONPATH=src python3 -m maia agent list` 가 저장된 agent 목록을 출력한다.
- [ ] `list` 출력은 저장 순서를 유지한다.
- [ ] `PYTHONPATH=src python3 -m maia agent status <agent_id>` 가 단일 agent 상태를 출력한다.
- [ ] 없는 agent_id 조회는 명확한 에러로 거부된다.
- [ ] 아직 구현하지 않은 명령은 기존 placeholder 동작을 유지한다.
- [ ] 테스트는 최소 5개 있다:
  - new persists record
  - duplicate name error
  - list order
  - status output for existing agent
  - missing agent error

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent list`
- `PYTHONPATH=src python3 -m maia agent status <agent_id>`

## Forbidden changes
- agent model 변경
- registry API 변경
- storage format 변경
- Docker/DB/queue 코드 추가
- 다른 placeholder 명령의 의미 변경

## Implementation notes
- Python 표준 라이브러리만 사용
- `app_state.py`에서 Maia home / registry path 계산을 캡슐화한다.
- agent_id는 `uuid.uuid4().hex[:8]` 같은 짧고 단순한 방식 허용
- 중복 검사는 `name` 기준으로 수행한다.
- 출력은 기계적으로 읽기 쉬운 plain text로 유지한다.
- 테스트는 `HOME` 환경변수를 임시 디렉토리로 오버라이드해서 실제 사용자 홈을 오염시키지 않는다.

## Suggested output shape
- `agent new demo`
  - `created agent_id=<id> name=demo status=stopped`
- `agent list`
  - 한 줄당 `agent_id=<id> name=<name> status=<status>`
- `agent status <id>`
  - `agent_id=<id> name=<name> status=<status> persona=<persona>`
