# Keryx Phase 2–4 Migration Lock

> For Maia implementation work, use the Codex harness loop on every task: worker Codex -> validation -> scoped reviewer Codex -> fix -> re-validate/re-review.

## Goal
Finish the migration from the preserved Phase 1 Keryx substrate without reviving a mixed broker/call/Keryx story. Phase 2 is runtime cutover. Phase 3 is public-surface cutover. Phase 4 is legacy deletion.

## Locked principles
1. Maia is the control plane.
2. Keryx is the collaboration plane.
3. Canonical collaboration resources are `agents`, `sessions`, `messages`, and `handoffs`.
4. Collaboration continuity uses explicit `session_id`, not participant-set inference.
5. Handoffs remain first-class resources with explicit lifecycle.
6. Maia state stays single-source-of-truth in the existing SQLite state DB.
7. Agent runtimes must not read collaboration state directly from SQLite once Phase 2 is complete; they go through Keryx APIs.
8. `/call`, broker-first collaboration wording, and old collaboration compatibility are deletion targets, not long-term product contracts.

## Current baseline
Phase 1 is already complete and is the only preserved Keryx substrate for later phases:
- `src/maia/keryx_models.py`
- `src/maia/keryx_storage.py`
- `src/maia/keryx_service.py`
- `src/maia/keryx_server.py`
- `src/maia/sqlite_state.py`
- `tests/test_keryx_models.py`
- `tests/test_keryx_storage.py`
- `tests/test_keryx_service.py`
- `tests/test_keryx_server.py`
- `tests/test_sqlite_state.py`

Do not reopen or expand Phase 1 scope while executing later phases unless a blocking bug is found in this preserved substrate.

## Phase handoff contract
Phase 1 is the foundation and stopping point for substrate work. Later phases consume it; they do not redesign it.

- Phase 1 preserved the Keryx models, storage, service, server, and SQLite integration.
- Phase 2 attaches live runtime behavior to that substrate.
- Phase 3 replaces public collaboration language and operator surfaces with Keryx-backed equivalents.
- Phase 4 deletes the old collaboration contract once runtime and public-surface cutovers are complete.

## Execution order
### Pre-Phase 2 lock
Before runtime cutover, lock this contract so implementation cannot drift back into broker/call-era mixed product stories.

### Phase 2 — Runtime cutover
Objective: real agent collaboration runtime behavior flows through Keryx while Phase 1 substrate remains intact.

Required outcomes:
- Maia-managed shared infra exposes one runtime-reachable Keryx endpoint.
- runtime workers consume pending collaboration work through Keryx APIs.
- runtime prompt/context assembly stops using direct SQLite collaboration reads and uses Keryx APIs instead.
- producer ingress creates Keryx sessions, messages, and handoffs instead of broker-era collaboration state.
- session continuity is carried with explicit `session_id`.

Non-goals:
- broad CLI/help/docs replacement
- deleting every legacy surface in the same task

### Phase 3 — Public surface cutover
Objective: user-facing and operator-facing collaboration story becomes Keryx-only after runtime cutover is complete.

Required outcomes:
- CLI/help/docs use Keryx as the collaboration root.
- operator visibility surfaces (`thread`, `handoff`, `workspace`) are either Keryx-backed or explicitly replaced by equivalent Keryx views.
- no public help, README, or PRD text presents `/call`, broker-first collaboration wording, or broker/message-plane identity as the active collaboration surface.

### Phase 4 — Legacy deletion
Objective: remove the old collaboration implementation and stale contract surfaces once Phase 2 and Phase 3 are proven.

Required outcomes:
- `/call` compatibility is removed.
- old collaboration compatibility paths are removed.
- broker-first collaboration wording is deleted.
- broker/call-era collaboration code no longer drives active runtime behavior.
- stale docs, tests, and scripts are deleted or rewritten to the Keryx story.
- remaining broker usage, if any, is not the collaboration model.

## Task map
- Task 131 — Phase 2–4 migration contract lock
- Task 132 — Maia-managed Keryx shared-infra bootstrap
- Task 133 — Runtime worker Keryx collaboration cutover
- Task 134 — Keryx public surface and operator visibility cutover
- Task 135 — Legacy collaboration deletion

## Guardrails
- Keep task scopes narrow and phase-specific.
- In this dirty-repo workflow, do not mix public-surface cleanup into runtime-cutover tasks unless the task explicitly allows it.
- If a task exposes a missing Keryx API needed for later phases, add the smallest possible extension and keep it in the task spec.
- Do not revive mixed legacy migration stories or alternate collaboration roots.
- Treat reviewer blockers as product-contract evidence, not just patch requests.

## Definition of done
The migration is complete only when:
- runtime collaboration is Keryx-backed,
- public collaboration wording is Keryx-backed,
- `/call`, broker-first collaboration wording, and old collaboration compatibility are deleted,
- and the product story can be explained in one sentence:
  - Maia runs agents.
  - Keryx handles collaboration.
