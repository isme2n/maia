# Task 138 - Restore Keryx migration baseline into git history

## Goal
Recover the remaining Keryx migration baseline artifacts into git history so the branch state matches the already-completed migration story that Task 137 now depends on.

## Non-goals
- new feature work beyond the previously completed Keryx migration baseline
- changing the Task 137 thread contract again
- broad cleanup of unrelated worktree noise outside this baseline set

## Allowed files
- `docs/tasks/138-restore-keryx-migration-baseline.md`
- `docs/plans/2026-04-19-keryx-phase1-core-plan.md`
- `docs/plans/2026-04-20-keryx-phase2-4-migration-lock.md`
- `docs/tasks/127-keryx-domain-models.md`
- `docs/tasks/128-keryx-sqlite-storage.md`
- `docs/tasks/129-keryx-service-layer.md`
- `docs/tasks/130-keryx-http-server.md`
- `docs/tasks/131-keryx-phase2-4-contract-lock.md`
- `docs/tasks/132-maia-managed-keryx-shared-infra-bootstrap.md`
- `docs/tasks/133-runtime-worker-keryx-collaboration-cutover.md`
- `docs/tasks/134-keryx-public-surface-and-operator-visibility-cutover.md`
- `docs/tasks/135-legacy-collaboration-deletion.md`
- `docs/tasks/136-canonical-sqlite-file-rename-to-maia-db.md`
- `src/maia/app_state.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/infra_runtime.py`
- `src/maia/keryx_server.py`
- `src/maia/keryx_storage.py`
- `tests/test_docker_runtime_adapter.py`
- `tests/test_keryx_models.py`
- `tests/test_keryx_storage.py`

## Acceptance criteria
- [x] the remaining untracked/tracked Keryx baseline files are either validated as-is and staged for commit, or corrected within allowed scope.
- [x] Phase 1 substrate artifacts (`keryx_storage`, model/storage tests, phase1/core task docs) are present and consistent.
- [x] shared infra / Keryx bootstrap / `maia.db` rename baseline files are present and consistent.
- [x] targeted validation passes for the remaining baseline set.
- [x] scoped reviewer approves that this baseline can be committed without bundling unrelated changes.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_docker_runtime_adapter.py tests/test_keryx_models.py tests/test_keryx_storage.py tests/test_keryx_service.py tests/test_keryx_server.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`

## Forbidden changes
- touching files outside the allowed baseline set
- reopening Task 137 contract decisions
- sweeping unrelated tracked changes into the same commit
