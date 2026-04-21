# Contributing to Maia

This document is the contributor entry point. Keep product-facing onboarding in `README.md`, test commands in `TESTING.md`, and system boundaries in `ARCHITECTURE.md`.

## Development environment

Requirements:
- Python 3.11+
- Docker CLI and a reachable Docker daemon for runtime commands such as `maia doctor`, `maia setup`, and `maia agent start`

Recommended setup from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .
```

If you are only editing docs or pure unit-tested code, you usually do not need live Docker services. Runtime commands still depend on host Docker, queue, and DB readiness.

## Harness workflow

Maia uses a small-task worker/verify/reviewer loop:

1. Write or update a task spec in `docs/tasks/<slug>.md`.
2. Keep the spec explicit about goal, non-goals, allowed files, and validation commands.
3. Let the worker implement only the spec scope.
4. Run the spec's required validation commands before review.
5. Let the reviewer check the diff against the spec and the validation output.
6. Fix blocking review issues, rerun validation, and request re-review.

Done means all three are true:
- the spec is satisfied
- validation passes
- the reviewer approves

## Working rules

- Keep tasks small and scoped.
- Do not change files outside the spec's allowed paths.
- Do not skip validation.
- Do not treat worker output as approval; worker and reviewer stay separate.
- If the worktree already contains unrelated changes, leave them alone unless your task explicitly requires coordination.

The detailed harness runbook lives in [`docs/harness-runbook.md`](docs/harness-runbook.md), and the deeper harness rationale lives in [`docs/harness-engineering.md`](docs/harness-engineering.md).

## Commit and PR rules

- Keep each commit and PR scoped to one task or one review fix loop.
- Link the task spec in the PR description.
- Include the validation commands you ran and the result of each command.
- Call out remaining risks or follow-up work instead of hiding them in the diff.
- Do not merge with failing validation or unresolved blocking review feedback.
