# Task 121 — public contract and active-conversation anchor lock

## Goal
- Maia의 direct-agent delegation story를 public contract로 먼저 고정한다.
- 핵심은 “사용자는 특정 agent와 직접 대화하고, 그 agent가 내부적으로 다른 agent에게 부탁하더라도 사용자-facing anchor는 계속 그 agent”라는 점을 문서/help/tests에 잠그는 것이다.
- 이번 태스크는 wording/tests/docs-only 범위이며 runtime/state machine behavior는 구현하지 않는다.

## Roadmap position
- This is design input for the later Part 4 execution path.
- Do not treat this task alone as permission to pull broader implementation ahead of Part 3 unless explicitly chosen.

## Non-goals
- 실제 delegation state machine 구현
- gateway/platform integration expansion
- giant operator dashboard
- export/import work

## Allowed files
- `README.md`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `docs/plans/phase18-direct-agent-delegation-and-user-anchored-collaboration.md`
- `docs/tasks/120-direct-agent-delegation-first-conversation-ux.md`
- `docs/tasks/121-public-contract-and-active-conversation-anchor-lock.md`
- `docs/plans/maia-product-roadmap-5-parts.md`

## Acceptance criteria
- [x] README/help/tests explicitly describe the active conversation agent as the user-facing anchor
- [x] Maia no longer reads as a central dispatcher/front-desk story for this flow
- [x] The public example includes user -> A -> B -> A -> user shape
- [x] The task spec and phase plan stay aligned
- [x] Scoped review approves the wording/contract change

## Closeout evidence
- Validation passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
  - Result: `70 passed`
- Live help check passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
  - Help output now includes `Direct-agent delegation contract:` with the active-agent anchor wording and `user -> economist -> tech -> economist -> user` example.
- Scoped spec review: `approve`
- Scoped quality review: `approve`


## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- Live help check:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`

## Forbidden changes
- sneaking implementation work into this contract task
- introducing new abstract jargon into public wording
- rewriting Maia into a centralized relay product story

## Worker/reviewer notes
- Worker should touch wording/tests only.
- Keep public wording concrete: user -> A -> B -> A -> user, not abstract routing jargon.
- Reviewer should focus on public contract clarity and user-facing anchor preservation.
- If wording is ambiguous, patch this task spec before rerunning the worker.
