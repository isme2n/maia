# Task 157 — Maia init closeout and OSS release readiness

## Goal
- Close the one-command onboarding slice with aligned README/help/tests and explicit repo-level vs host-level proof for open-source release.

## Non-goals
- New product features beyond onboarding
- Big architecture changes after the onboarding path is already implemented

## Allowed files
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/maia-product-roadmap-5-parts.md`
- scoped help/tests files required by final alignment
- `docs/tasks/157-maia-init-closeout-and-release-readiness.md`

## Acceptance criteria
- [x] README/help/PRD all tell the same `maia init` story.
- [x] Repo-level validation evidence is recorded.
- [x] Host-level smoke evidence is recorded separately when available.
- [x] Remaining limitations are explicit and honest.
- [x] The final onboarding story is suitable for open-source publication.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- any additional scoped release checks required by the final implementation task set

## Forbidden changes
- No unrelated feature expansion
- No broad roadmap rewriting outside the onboarding closeout scope

## Notes
- Distinguish repo proof from host proof.
- Treat this as a release-readiness closeout task, not a feature task.

## Closeout evidence
- Repo-level release checks:
  - `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia --help`
  - Result: help output verified with the new `Validation boundary` section and canonical `maia init` onboarding story
  - `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia init --help`
  - Result: help output verified with the truthful readiness contract and `conversation_ready` success rule
- Repo-level validation evidence:
  - `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
  - Result: `160 passed`
- Host-level smoke evidence:
  - Fresh Docker-group login-shell proof:
    - `sg docker -c 'cd /home/asle/maia && HOME=<tmp_home> PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia doctor'`
    - Result: host path passed `doctor` in a fresh Docker-group shell (`Docker OK`, `Keryx HTTP API OK`, `SQLite State DB OK`, `Shared infra ready`)
  - Host `maia init` interactive smoke attempt:
    - `sg docker -c 'set -a; . /home/asle/.hermes/.env; set +a; cd /home/asle/maia && HOME=<tmp_home> PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia init'`
    - Result: real host path reached interactive Hermes gateway setup under a TTY, but the run still exited non-success with `gateway_ready=no` / `default_destination_ready=no`; this is recorded as partial host evidence, not a full host success claim.
  - Boundary note: host proof remains separate from repo proof and only counts as full success when a real machine confirms the complete path under test end-to-end.
- Reviewer verdict: `approve`

## Review status
- Current review status: approved
