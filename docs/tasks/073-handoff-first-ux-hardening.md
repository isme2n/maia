# Task 073 — Handoff-first UX and operator flow hardening

## Goal
- top-level help, command help, README operator examples를 handoff-first workflow로 정리하고, Phase 8 public surface를 과장 없이 닫는다.

## Non-goals
- new runtime features
- import/export wording overhaul
- messaging semantics 변경

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] top-level help/operator flow가 `start -> send/reply -> handoff -> thread/workspace -> status` 흐름을 보여준다.
- [ ] handoff/workspace examples가 현재 실제 구현 상태를 과장하지 않는다.
- [ ] legacy wording (`artifact`)이 public help/README에 남지 않는다.
- [ ] targeted tests와 full verify가 통과한다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- runtime adapter files
- broker adapter files
- export/import files

## Notes
- 여기서는 UX/DX 정리가 핵심이다. 문서와 help가 실제 surface와 딱 맞아야 한다.
