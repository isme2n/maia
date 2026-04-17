# Task 124 — live runtime delegation loop regression and closeout

## Goal
- representative live runtime flow를 current Maia의 truthful anchor-thread model로 잠가서, direct-agent delegation loop를 실제 running agents 기준으로 검증한다.
- closeout 기준은 “내부 위임이 실제로 일어나고, intermediate turn과 final result/handoff readiness가 같은 anchor thread/context에 누적되어 보인다”이다.

## Roadmap position
- This is the closeout task for the later direct-agent UX execution track.
- Do not run this before Task 121/122/123 are closed.

## Non-goals
- all-platform rollout
- web UI
- export/import work
- unrelated roadmap part closeout

## Allowed files
- `README.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/hermes_runtime_worker.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_hermes_runtime_worker.py`
- `docs/tasks/124-live-runtime-delegation-loop-regression-and-closeout.md`
- `docs/plans/phase18-direct-agent-delegation-and-user-anchored-collaboration.md`
- `docs/plans/maia-product-roadmap-5-parts.md`

## Acceptance criteria
- [x] targeted regression covers the current anchor-thread delegation loop A -> B -> A -> B -> A
- [x] B sends at least one intermediate `question` or `report` before final result
- [x] that intermediate turn is persisted/visible in thread/message state
- [x] A's anchor thread/context preserves the intermediate state without inventing a separate fake user-conversation subsystem
- [x] B sends a final result or handoff back to A
- [x] the same anchor thread/context surfaces final `handoff_ready` state
- [x] representative live smoke passes on real runtimes
- [x] docs/tests/plan alignment reflects the same truthful story
- [x] scoped review approves the closeout

## Closeout evidence
- Targeted validation passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py`
  - Result: `146 passed`
- Full verify passed:
  - `cd /home/asle/maia && bash scripts/verify.sh`
  - Result: `315 passed`
- Scoped review: `approve`
- Truthful closeout shape now locked:
  - delegated request A -> B
  - intermediate question/report B -> A
  - continuation on the same anchor thread A -> B
  - final handoff/result B -> A
  - final `handoff_ready` visibility on the same anchor thread/context
- Current Maia limitation acknowledged explicitly:
  - no separate first-class `user <-> agent` conversation object yet
  - Task 124 therefore closes out on the honest A-owned anchor-thread model rather than inventing a fake extra subsystem

## Closeout note
- Maia still does not have a separate first-class `user <-> agent` conversation object.
- Task 124 is therefore closed out truthfully by treating the anchor thread created by agent A as the original conversation context for the delegated loop.
- The regression must prove continuity on that same anchor thread/context: A -> B delegated request, B -> A intermediate question/report, A -> B continuation, B -> A final result/handoff, and final readiness visible on the same thread.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py`
- `cd /home/asle/maia && bash scripts/verify.sh`
- Representative live smoke evidence must show:
  - delegated request A -> B
  - intermediate turn B -> A
  - continuation on the same anchor thread A -> B
  - final result/handoff B -> A
  - final `handoff_ready` visibility on the same anchor thread/context

## Forbidden changes
- claiming success from stored-state simulation only
- accepting a local shortcut that skips the real internal message path
- broad unrelated cleanup outside the allowed files

## Worker/reviewer notes
- Reviewer must reject any implementation that cannot prove the five evidence points above.
- In the current Maia model, do not require a fake new `user <-> agent` conversation object just to satisfy wording. The truthful proof is continuity on the same anchor thread/context owned by agent A.
- If live validation fails because of stale runtime artifacts, fix the artifact path rather than weakening the product story.
