# Task 001 - Maia CLI skeleton

## Goal
- Maia의 최소 CLI 골격을 만든다.
- 아직 실제 Docker/DB/Queue 동작은 구현하지 않고, 명령 구조와 출력 흐름만 고정한다.

## Non-goals
- 실제 에이전트 생성/실행
- Docker Compose 연동
- DB 저장
- Queue 처리
- memory 저장

## Allowed files
- `src/maia/__init__.py`
- `src/maia/__main__.py`
- `src/maia/cli.py`
- `src/maia/main.py`
- `tests/test_cli.py`
- `pyproject.toml`
- `README.md`

## Acceptance criteria
- [ ] `maia --help`가 동작한다.
- [ ] `maia agent --help`가 동작한다.
- [ ] 아래 하위 명령이 골격으로 존재한다:
  - `new`
  - `start`
  - `stop`
  - `archive`
  - `restore`
  - `status`
  - `list`
  - `tune`
  - `purge`
- [ ] 각 명령은 아직 미구현이어도 일관된 placeholder 메시지를 출력한다.
- [ ] 테스트가 최소 3개 있다:
  - top-level help
  - agent help
  - representative subcommand placeholder output
- [ ] `PYTHONPATH=src python3 -m maia --help`가 동작한다.

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia --help`
- `PYTHONPATH=src python3 -m maia agent --help`

## Forbidden changes
- Docker 관련 코드 추가
- 외부 서비스 설치/호출
- 실제 상태 저장 로직 구현
- CLI 네이밍 변경

## Implementation notes
- Python 표준 라이브러리 `argparse` 우선 사용
- placeholder 문구는 짧고 일관되게 유지
- 기본 구조는 이후 registry/runtime 연결이 쉬운 형태로 작성

## Suggested placeholder style
- `maia agent new <name>` 실행 시:
  - `Not implemented yet: agent new`
- 다른 서브커맨드도 같은 패턴 사용
