# Task 139 — Keryx product contract lock: `/keryx` single entry + delivery_mode command contract

## Goal
Lock the Maia/Keryx collaboration contract in code/tests so the active surface is consistent with the product decision:
- user-facing collaboration instruction is `/keryx <instruction>`
- legacy `/call` and `/agent-call` are not active collaboration commands
- collaboration message delivery intent uses imperative `delivery_mode` semantics (`agent_only` / `user_direct`)

## Non-goals
- Implementing full user-channel gateway delivery routing
- Runtime anchor-policy redesign
- Broad legacy docs cleanup outside touched files

## Allowed files
- `src/maia/keryx_models.py`
- `src/maia/keryx_storage.py`
- `src/maia/keryx_server.py`
- `tests/test_keryx_models.py`
- `tests/test_keryx_storage.py`
- `tests/test_keryx_server.py`
- `tests/test_cli.py`
- `docs/tasks/139-keryx-product-contract-lock-delivery-mode.md`

## Required changes
1. Add an explicit Keryx message delivery mode contract in domain models:
   - enum values: `agent_only`, `user_direct`
   - default: `agent_only`
   - serialization/deserialization must preserve the value
   - invalid values must fail with a clear `ValueError`
2. Ensure HTTP/session message ingestion preserves `delivery_mode` end-to-end (POST and GET).
3. Lock test expectations so the built-in keryx skill does not assert `/call` as a recommended/public command.

## Acceptance criteria
- Keryx message model round-trip includes `delivery_mode`
- invalid `delivery_mode` payload is rejected
- server/storage tests confirm persisted payload includes delivery mode
- CLI test for built-in keryx skill no longer encodes `/call` as active guidance
- targeted tests pass

## Validation
Run:
- `python3 -m pytest -q tests/test_keryx_models.py tests/test_keryx_storage.py tests/test_keryx_server.py tests/test_cli.py::test_builtin_keryx_skill_locks_grounded_http_workflow`
