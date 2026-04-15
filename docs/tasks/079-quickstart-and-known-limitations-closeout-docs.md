# Task 079 — Quickstart and known-limitations closeout docs

## Goal
- README/usage surface에 quickstart와 known limitations를 명확히 적어서 지금 되는 것과 아직 아닌 것을 분리한다.

## Non-goals
- architecture rewrite
- new implementation features

## Allowed files
- `README.md`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`

## Acceptance criteria
- [ ] quickstart가 실제 동작하는 최소 흐름만 보여준다.
- [ ] known limitations/support boundary가 문서에 명시된다.
- [ ] unsupported scope(daemon, sync, DB migration 등)가 분명히 적힌다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- runtime adapter files
- broker adapter files
- storage files
