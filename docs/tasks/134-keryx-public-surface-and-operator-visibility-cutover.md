# Task 134 - Keryx public surface and operator visibility cutover

## Goal
Make Keryx the public collaboration story in CLI/help/docs while preserving a strong operator visibility surface for active collaboration state.

## Non-goals
- Phase 1 Keryx foundation work
- runtime worker collaboration internals beyond what is needed to expose Keryx-backed visibility
- legacy code deletion that belongs in Phase 4

## Allowed files
- `docs/tasks/134-keryx-public-surface-and-operator-visibility-cutover.md`
- `README.md`
- `docs/prd/maia-core-product.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`

## Acceptance criteria
- [x] CLI/help/docs present Keryx as the canonical collaboration root.
- [x] no public wording presents `/call` or broker/message-plane as the active collaboration identity.
- [x] operator visibility surfaces remain clear and are explained as Keryx-backed views.
- [x] help output and tests tell one collaboration story instead of mixed broker/call/Keryx stories.
- [x] targeted CLI/help tests pass.

## Implementation notes
- Top-level help now frames Keryx as the collaboration contract and labels thread/handoff/workspace as Keryx-backed operator visibility views.
- README and PRD now describe Part 2 as Keryx-rooted collaboration while keeping `send`/`reply`/`inbox` explicitly diagnostic.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia agent --help`

## Forbidden changes
- restoring `/call` as the public collaboration root
- deleting operator visibility without equivalent Keryx-backed replacements
- broad runtime refactors outside the allowed files
