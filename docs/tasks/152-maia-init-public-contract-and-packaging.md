# Task 152 — Maia init public contract and packaging story

## Goal
- Make `maia init` the canonical public onboarding path in Maia’s docs/help/package metadata, while keeping decomposed operator commands available as advanced surfaces.
- Align the OSS first-run story with a one-command product posture similar to modern CLI tools.

## Non-goals
- Full `maia init` implementation
- Runtime/gateway orchestration logic
- Hermes setup passthrough changes
- Docker/runtime startup changes

## Allowed files
- `README.md`
- `pyproject.toml`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `docs/tasks/152-maia-init-public-contract-and-packaging.md`

## Acceptance criteria
- [x] README top-level quickstart makes `maia init` the canonical happy path.
- [x] README install section no longer centers `python3 -m pip install .` as the only story; it explains the intended OSS-facing try/install path clearly.
- [x] `pyproject.toml` description no longer says `Maia CLI skeleton`.
- [x] Top-level help text introduces `init` as the public one-command onboarding path.
- [x] Existing decomposed commands (`doctor`, `setup`, `agent new`, `agent setup`, `agent start`) remain documented as advanced/manual flow, not deleted from the product.
- [x] Focused tests lock the new wording/help contract.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- No edits outside allowed files
- No implementation of init orchestration yet
- No Docker/gateway/runtime code changes
- No broad docs cleanup unrelated to onboarding contract

## Notes
- Public wording must remain gateway/platform agnostic.
- Keep the product contract truthful: `init` is the canonical path, advanced commands remain available.

## Closeout evidence
- Validation: `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- Validation result: `81 passed`
- Live help check: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m maia --help`
- Re-review verdict: `approve`
- Review-confirmed contract: README and top-level help now present `maia init` as the canonical onboarding path, install guidance includes `uvx maia init` / `pipx install maia` / local dev install, `pyproject.toml` no longer says `Maia CLI skeleton`, and the decomposed bootstrap commands remain available as the advanced/manual flow.
