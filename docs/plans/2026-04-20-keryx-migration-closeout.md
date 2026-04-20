# Keryx Migration Closeout

> For Maia implementation work, use the Codex harness loop on every task: worker Codex -> validation -> scoped reviewer Codex -> fix -> re-validate/re-review.

## Scope closed here
This document closes the Keryx migration sequence that started from the preserved Phase 1 substrate and continued through Tasks 131–135.

Preserved Phase 1 baseline:
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

## Tasks completed
### Task 131 — Phase 2–4 contract lock
Locked the migration contract so later implementation would not drift back into a mixed broker/call/Keryx story.

Closed decisions:
- Maia = control plane
- Keryx = collaboration plane
- Phase 2 = runtime cutover
- Phase 3 = public-surface cutover
- Phase 4 = legacy deletion
- `/call`, broker-first collaboration wording, and old collaboration compatibility are deletion targets

### Task 132 — Maia-managed Keryx shared-infra bootstrap
Made shared infra own one runtime-reachable Keryx endpoint.

Closed outcomes:
- shared infra bootstrap creates or verifies one Maia-managed Keryx endpoint for the local DB
- `maia doctor` / `maia setup` surface Keryx readiness as shared infra state
- runtime containers receive `KERYX_BASE_URL`
- existing mismatched Keryx containers are recreated against the correct local DB mount

### Task 133 — Runtime worker Keryx collaboration cutover
Moved active runtime collaboration from broker polling/direct SQLite collaboration reads to Keryx.

Closed outcomes:
- runtime worker discovers pending work through Keryx
- prompt/context assembly comes from Keryx roster/session/message/handoff data
- replies are appended into the same Keryx session backing the Maia thread
- handoff lifecycle is updated through Keryx after reply publication
- a narrow Keryx pending-work route exists: `GET /agents/{agent_id}/pending-work`

### Task 134 — Keryx public surface and operator visibility cutover
Made Keryx the public collaboration story while preserving operator visibility.

Closed outcomes:
- CLI/help/docs present Keryx as the canonical collaboration root
- thread/handoff/workspace are explained as Keryx-backed operator views
- broker/message-plane wording is removed from the active public collaboration contract

### Task 135 — Legacy collaboration deletion
Removed obsolete collaboration entrypoints and stale contract surfaces.

Closed outcomes:
- legacy send/inbox/reply/call-era active collaboration surface removed
- stale compatibility wording removed from docs/help/tests
- stale test helper parsing for deleted collaboration prefixes removed
- remaining broker presence is infra support, not the collaboration model

## Resulting product structure
### Control plane
Maia owns:
- agent lifecycle
- setup/bootstrap/doctor
- runtime state
- operator-facing control surfaces

### Collaboration plane
Keryx owns:
- collaboration roster
- canonical collaboration session records behind Maia thread views
- messages
- handoffs
- runtime collaboration context and pending-work discovery

## Final locked principles
1. Maia is the control plane.
2. Keryx is the collaboration plane.
3. Maia's public collaboration resource is `thread` / `thread_id`, backed internally by Keryx session records.
4. Internal Keryx continuity may still use `session_id`, but Maia operator wording uses `thread_id`.
5. Handoff is first-class.
6. Canonical persistence remains a single Maia-owned SQLite DB.
7. Agent runtimes must not use direct SQLite collaboration reads as the active path.
8. Public/internal collaboration story is Keryx.
9. Broker-era collaboration surfaces are not the active product contract.

## What remains after this closeout
The migration itself is closed at the product-contract level.
The main follow-up decided after closeout is naming cleanup for the canonical SQLite file:
- prefer a Maia-oriented DB filename (`maia.db`) over neutral or Keryx-oriented names
- keep the DB as Maia-owned canonical state even though Keryx uses tables inside it

That follow-up is intentionally separate from the Keryx migration closeout so naming cleanup does not blur the already-finished collaboration migration.
