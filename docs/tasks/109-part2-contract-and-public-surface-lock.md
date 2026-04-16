# Task 109 — Part 2 contract and public surface lock

## Goal
- Part 2를 `running agents talk over the broker` 기준으로 먼저 잠그고, README/PRD/help/tests에서 collaboration surface를 실제 message plane + visibility story로 재정렬한다.

## Non-goals
- broker delivery semantics 구현 변경
- runtime lifecycle 변경
- daemonized consumer loop 추가
- export/import surface 수정

## Allowed files
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/maia-product-roadmap-5-parts.md`
- `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`
- `docs/tasks/109-part2-contract-and-public-surface-lock.md`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`

## Acceptance criteria
- [x] README에 Part 2가 running-agent broker conversation story로 명시된다.
- [x] PRD가 Part 2를 agent-to-agent message plane + visibility story로 설명한다.
- [x] top-level/help wording이 collaboration surface를 public Part 2 visibility/debug surface로 정렬한다.
- [x] docs/help/tests가 Maia를 operator-mediated CLI messenger처럼 보이게 하지 않는다.
- [x] targeted tests green

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia thread --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia send --help`

## Forbidden changes
- broker adapter code
- runtime adapter code
- collaboration storage semantics
- new CLI verbs
