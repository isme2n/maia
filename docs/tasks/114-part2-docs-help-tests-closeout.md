# Task 114 — Part 2 docs/help/tests closeout

## Goal
- Part 2 public story를 README, help, PRD, roadmap, phase plan, tests에서 같은 closeout narrative로 닫는다.
- running-agent broker conversation은 제품 본체로, `send`/`reply`/`inbox`는 diagnostic/operator-check surface로 유지한다.
- operator visibility flow는 `thread -> handoff -> workspace -> status/logs` 순서로 고정한다.

## Non-goals
- broker/runtime behavior 변경
- new CLI verbs 추가
- collaboration schema 변경
- Part 3 export/import scope 작업

## Allowed files
- `README.md`
- `docs/prd/maia-core-product.md`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`
- `docs/plans/maia-product-roadmap-5-parts.md`
- `docs/tasks/114-part2-docs-help-tests-closeout.md`

## Acceptance criteria
- [x] top-level help가 Part 2 conversation contract와 Part 2 visibility flow를 함께 보여준다.
- [x] README가 Part 2 visibility flow를 operator-facing path로 설명한다.
- [x] PRD와 phase plan이 같은 Part 2 completion criteria를 설명한다.
- [x] roadmap가 Part 2 complete 상태로 갱신된다.
- [x] targeted tests green
- [x] full verify green
- [x] reviewer approve

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia thread --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia handoff --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia workspace --help`

## Forbidden changes
- runtime adapter changes
- broker semantics changes
- storage model/schema changes
- unrelated README cleanup outside Part 2 closeout narrative
