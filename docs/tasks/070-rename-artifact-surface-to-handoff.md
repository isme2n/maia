# Task 070 — Rename public artifact surface to handoff

## Goal
- public CLI, help text, README, and thread summary wording에서 `artifact`를 `handoff`로 되돌린다.
- internal model은 이미 `HandoffRecord`이므로 public surface를 그에 맞춘다.

## Non-goals
- workspace CLI 추가
- handoff storage schema 변경
- broker/runtime behavior 변경

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] `maia artifact ...` public surface가 `maia handoff ...`로 바뀐다.
- [ ] help/README/examples가 handoff terminology로 통일된다.
- [ ] thread summary field도 `artifacts=`가 아니라 `handoffs=`로 출력된다.
- [ ] existing behavior/validation은 유지된다.
- [ ] legacy artifact alias를 둘지 말지 policy를 명시하고 테스트로 고정한다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- `src/maia/collaboration_storage.py`
- broker adapter files
- runtime adapter files
- export/import files

## Notes
- 사용자 선호상 컨셉을 다시 artifact로 키우지 말고 handoff를 메인 용어로 유지한다.
- alias를 남긴다면 transitional compatibility로만 두고 help/main docs에는 노출하지 않는 쪽이 기본이다.
