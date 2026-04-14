# Task 010 - Agent tune persona file input

## Goal
- `maia agent tune` 에 `--persona-file <path>` 입력을 추가해서, 긴 persona를 파일에서 안전하게 읽어 적용할 수 있게 한다.
- 기존 `--persona <text>` 동작은 유지하되, 둘 중 하나만 선택하도록 강제한다.

## Non-goals
- SOUL 파일 수정
- interactive editor 지원
- preset registry 구현
- multi-file merge
- lifecycle/purge 정책 변경

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/tasks/010-agent-tune-persona-file.md`

## Acceptance criteria
- [ ] `PYTHONPATH=src python3 -m maia agent tune <agent_id> --persona-file <path>` 가 동작한다.
- [ ] `--persona` 와 `--persona-file` 는 동시에 줄 수 없다.
- [ ] 둘 다 생략할 수 없다.
- [ ] persona-file 내용은 UTF-8 text로 읽는다.
- [ ] 파일의 trailing newline은 제거하지 않고 그대로 저장한다.
- [ ] 없는 파일 경로는 명확한 에러를 반환한다.
- [ ] `status` 는 파일에서 읽은 persona를 그대로 보여준다.
- [ ] 기존 `--persona <text>` 경로는 계속 동작한다.
- [ ] direct `main(["agent", "tune", ...])` placeholder contract 는 유지된다.
- [ ] 테스트가 최소 5개 추가/보강된다:
  - persona-file updates persona
  - persona-file preserves trailing newline
  - missing persona-file error
  - parser rejects both persona sources together
  - parser rejects missing persona source

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia agent new demo`
- `PYTHONPATH=src python3 -m maia agent tune <agent_id> --persona-file <path>`
- `PYTHONPATH=src python3 -m maia agent status <agent_id>`

## Forbidden changes
- agent model 변경
- registry API 변경
- storage format 변경
- purge/lifecycle 의미 변경
- persona-file 내용을 trim/normalize 하도록 변경

## Notes
- 이번 task는 persona UX 개선용 작은 slice다.
- 구현은 CLI 레벨에서만 처리하고 저장 포맷은 그대로 둔다.
- 파일 read 에러는 사람이 읽을 수 있는 plain-text 에러로 노출한다.
