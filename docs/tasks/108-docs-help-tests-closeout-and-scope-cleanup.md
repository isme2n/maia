# Task 108 — docs/help/tests closeout and scope cleanup

## Goal
- Part 1 public story를 `doctor → setup → agent new → agent setup → agent start`로 완전히 닫고, help/README/PRD/tests에서 남은 군더더기와 generic wording을 정리한다.

## Non-goals
- runtime lifecycle behavior 변경
- broker/collaboration 기능 제거
- import/export surface redesign
- Hermes setup passthrough 동작 재구현

## Allowed files
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md`
- `docs/tasks/108-docs-help-tests-closeout-and-scope-cleanup.md`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [x] README first-run section leads with `doctor → setup → agent new → agent setup → agent start`.
- [x] README and PRD explicitly say `agent setup` is an interactive CLI-only passthrough to `hermes setup`.
- [x] top-level/agent help avoids generic or stale wording that weakens the Part 1 operator story.
- [x] docs/help/tests no longer imply Maia is a CLI messenger product.
- [x] targeted tests green
- [x] full verify green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- changing runtime start/stop/status/logs behavior
- changing collaboration command semantics
- broad README cleanup outside Part 1 public story alignment
