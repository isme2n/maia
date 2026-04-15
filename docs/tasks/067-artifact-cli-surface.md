# Task 067 — Artifact CLI surface and validation

## Goal
- operator가 thread-linked artifact/handoff metadata를 추가·조회할 수 있도록 `artifact add`, `artifact list`, `artifact show`를 추가한다.
- public CLI는 `artifact` 용어를 쓰고, internal model은 `HandoffRecord`를 그대로 활용한다.

## Non-goals
- 실제 파일 업로드/복사
- workspace sync
- broker publish path 변경

## Allowed files
- `src/maia/cli_parser.py`
- `src/maia/cli.py`
- `tests/test_cli.py`
- `README.md`

## Acceptance criteria
- [ ] `maia artifact add --thread-id ... --from-agent ... --to-agent ... --type ... --location ... --summary ...`가 handoff record를 저장한다.
- [ ] thread id와 agent ids validation이 기존 state/registry against 수행된다.
- [ ] `maia artifact list`는 기본 전체 출력, `--thread-id` 필터를 지원한다.
- [ ] `maia artifact show <artifact_id>`가 단일 artifact detail을 출력한다.
- [ ] 출력은 concise key=value 스타일을 유지한다.
- [ ] README/help examples가 새 artifact flow를 반영한다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- broker contract files
- runtime adapter files
- export/import code paths

## Notes
- location은 path/url/repo-ref pointer 그대로 문자열로만 저장한다.
- artifact add 시 thread 참여자가 아니어도 자동 추가하지 말고, 명시적으로 validation policy를 정해 테스트로 고정한다.
