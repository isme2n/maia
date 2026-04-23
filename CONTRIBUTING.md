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

If you are only editing docs or pure unit-tested code, you usually do not need live Docker services. Runtime commands still depend on host Docker and SQLite/Keryx readiness.

## Scoped task workflow

Keep work small and reviewable:

1. Write a short scoped task note in the repo root or your PR description.
2. Be explicit about goal, non-goals, touched files, and validation commands.
3. Implement only that scope.
4. Run the required validation commands before review.
5. Ask for review against the scoped task note and validation output.

Done means all three are true:
- the scoped task is satisfied
- validation passes
- review approves the change

## Working rules

- Keep tasks small and scoped.
- Do not change files outside the stated task boundary.
- Do not skip validation.
- If the worktree already contains unrelated changes, leave them alone unless your task explicitly requires coordination.

## Commit and PR rules

- Keep each commit and PR scoped to one task or one review fix loop.
- Link the task spec in the PR description.
- Include the validation commands you ran and the result of each command.
- Call out remaining risks or follow-up work instead of hiding them in the diff.
- Do not merge with failing validation or unresolved blocking review feedback.
