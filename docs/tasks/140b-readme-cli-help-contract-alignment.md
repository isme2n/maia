# Task 140B — README and CLI help contract alignment

## Goal
Align active product wording in README and CLI help with Phase 1 contract lock.

## Non-goals
- Runtime behavior changes
- Test fixture refactors outside contract wording

## Allowed files
- `docs/tasks/140b-readme-cli-help-contract-alignment.md`
- `README.md`
- `src/maia/cli_parser.py`

## Required changes
1) README:
   - explicitly describe user collaboration entry as `/keryx <instruction>`
   - explicitly state `/call` and `/agent-call` are removed from active contract
   - include delivery contract wording (`delivery_mode`: `agent_only`/`user_direct`; user_direct failure is explicit `failed`)
2) CLI help constants/epilog:
   - include concise `/keryx <instruction>` contract sentence
   - include concise `delivery_mode` contract sentence
   - avoid presenting `/call`/`/agent-call` as active user entrypoints

## Acceptance criteria
- README and `maia --help` tell the same collaboration contract.
- No active wording contradicts `/keryx`-first policy.
- `delivery_mode` semantics appear in both README and CLI help contract text.

## Validation
- `python3 -m maia --help`
- `python3 -m maia thread --help`
- `python3 -m pytest -q tests/test_cli.py`
