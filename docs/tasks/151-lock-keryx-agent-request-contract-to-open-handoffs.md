# Task 151 — lock Keryx agent-request contract to open handoffs

## Goal
- Close the live regression where agent-to-agent Keryx requests can be created as message-only threads that never enter worker pending-work.
- Align Maia’s built-in `/keryx` skill contract with the actual worker/runtime implementation so agent-targeted requests always produce processable pending work.

## Root-cause evidence
- Live thread `tomo-da-9077b3` had:
  - a session
  - a `question` message to agent `337a5b9e`
  - no handoff
  - therefore `KeryxService.list_pending_work('337a5b9e') == []`
- `src/maia/keryx_storage.py::list_pending_work()` only yields work when there is an OPEN handoff targeting the agent.
- Current built-in Keryx skill text still says simple question/answer can proceed without a handoff, which contradicts the live worker contract.
- Manually creating an OPEN handoff for the same thread caused `다` to answer successfully, proving the contract mismatch.

## Non-goals
- Change runtime worker pending-work logic
- Redesign Keryx storage or thread model
- Add new CLI commands or HTTP endpoints
- Broaden to multi-agent batching or new delivery modes

## Allowed files
- `src/maia/keryx_skill.py`
- `tests/test_cli.py`
- `docs/tasks/151-lock-keryx-agent-request-contract-to-open-handoffs.md`

## Acceptance criteria
- [ ] Built-in `/keryx` skill explicitly instructs agents that agent-targeted requests must create an OPEN handoff, not message-only fire-and-forget.
- [ ] Skill text no longer recommends skipping handoff for simple question/answer when another agent is expected to respond.
- [ ] Skill text explains that the handoff is what makes the request visible to worker pending-work.
- [ ] Regression tests lock the new contract wording in the embedded skill content and installed agent skill content.
- [ ] Focused pytest coverage passes.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- No edits outside allowed files
- No runtime worker logic changes in this task
- No Docker/gateway/model config changes
- No unrelated README/docs cleanup

## Notes
- This repo is dirty; reviewer must judge only this task scope.
- Treat this as a contract-lock task: fix the public agent skill wording to match the already-shipped pending-work implementation.
