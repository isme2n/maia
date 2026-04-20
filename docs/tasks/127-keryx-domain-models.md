# Task 127 - Keryx domain models

## Goal
Add first-class Keryx resource models for roster summaries, sessions, messages, and handoffs with strict validation and stable serialization contracts.

## Non-goals
- SQLite schema or persistence
- HTTP server code
- runtime worker cutover
- CLI changes
- old collaboration model removal

## Allowed files
- `docs/tasks/127-keryx-domain-models.md`
- `src/maia/keryx_models.py`
- `tests/test_keryx_models.py`

## Acceptance criteria
- [x] `src/maia/keryx_models.py` defines Keryx model contracts for agent summaries, sessions, messages, and handoffs.
- [x] Session status is explicit and constrained (`active`, `idle`, `closed`).
- [x] Handoff status is explicit and constrained (`open`, `accepted`, `done`).
- [x] Models round-trip through `to_dict()` / `from_dict()`.
- [x] Invalid enum/field values fail with clear `ValueError`s.
- [x] Tests cover constructor validation and serialization/deserialization parity.

## Required validation commands
- `python3 -m pytest -q tests/test_keryx_models.py`

## Forbidden changes
- modifying old collaboration models
- touching storage/runtime/CLI files
- adding third-party dependencies
