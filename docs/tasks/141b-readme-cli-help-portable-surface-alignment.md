# Task 141B — README and CLI help portable-surface alignment

## Goal
Align README and CLI help wording so Part 3 portable-state story is simple and consistent.

## Roadmap position
- Execution task for Part 3.

## Non-goals
- Runtime logic changes
- Broad docs rewrite outside portable-state contract

## Allowed files
- `docs/tasks/141b-readme-cli-help-portable-surface-alignment.md`
- `README.md`
- `src/maia/cli_parser.py`

## Required changes
1) README:
   - present user mental model as:
     - export all (default)
     - export to explicit path (user/project snapshot)
     - import safely (preview + confirm)
   - keep `inspect` as secondary/support command, not primary first-run path
2) CLI help constants/examples:
   - keep `export`/`import` prominent and explicit
   - keep import safety wording (`--preview`, `--verbose-preview`, `--yes`)
   - avoid wording that makes `inspect` mandatory for normal flow

## Acceptance criteria
- README and `maia --help`/`maia import --help` tell the same Part 3 contract.
- Primary user flow is `export` + `import`, with safety-first import.
- No active wording contradicts import safety contract.

## Validation
- `python3 -m maia --help`
- `python3 -m maia export --help`
- `python3 -m maia import --help`
- `python3 -m pytest -q tests/test_cli.py`
