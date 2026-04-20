# Task 135 - Legacy collaboration deletion

## Goal
Delete obsolete broker/call-era collaboration code and stale contracts after Keryx-backed runtime behavior and public surface are in place.

## Non-goals
- reopening public contract choices
- adding new collaboration abstractions
- broad unrelated cleanup outside the legacy collaboration path

## Allowed files
- `docs/tasks/135-legacy-collaboration-deletion.md`
- `README.md`
- `docs/prd/maia-core-product.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/infra_runtime.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_docker_runtime_adapter.py`

## Acceptance criteria
- [x] legacy collaboration entrypoints and wording that are no longer part of the Keryx product story are removed.
- [x] old collaboration compatibility is removed instead of maintained as an active product contract.
- [x] remaining broker use, if any, is not the active collaboration model.
- [x] stale tests/docs for deleted collaboration paths are removed or rewritten.
- [x] targeted validation passes after deletion.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_docker_runtime_adapter.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`

## Forbidden changes
- leaving dead compatibility shims for convenience once replacement Keryx paths exist
- deleting Keryx-backed operator visibility needed by the final product
- mixing new feature work into the deletion task
