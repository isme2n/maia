# Task 131 - Phase 2–4 migration contract lock

## Goal
Lock the post-Phase-1 migration sequence so the preserved Keryx Phase 1 baseline hands off cleanly into Phase 2 runtime cutover, Phase 3 public-surface cutover, and Phase 4 legacy deletion without drifting back into a mixed broker/call/Keryx story.

## Non-goals
- runtime worker code changes
- CLI/help implementation changes
- deleting legacy code in this task
- reopening or expanding Phase 1 foundation work

## Allowed files
- `docs/plans/2026-04-20-keryx-phase2-4-migration-lock.md`
- `docs/tasks/131-keryx-phase2-4-contract-lock.md`

## Acceptance criteria
- [ ] The plan locks Maia as control plane and Keryx as collaboration plane.
- [ ] The plan states that Phase 2 is runtime cutover, Phase 3 is public-surface cutover, and Phase 4 is legacy deletion.
- [ ] The plan states that `/call`, broker-first collaboration wording, and old collaboration compatibility are deletion targets.
- [ ] The plan defines a clean handoff from the preserved Phase 1 substrate to later phases.

## Required validation commands
- `test -f /home/asle/maia/docs/plans/2026-04-20-keryx-phase2-4-migration-lock.md`
- `python3 - <<'PY'
from pathlib import Path
text = Path('/home/asle/maia/docs/plans/2026-04-20-keryx-phase2-4-migration-lock.md').read_text()
assert 'Phase 2 — Runtime cutover' in text
assert 'Phase 3 — Public surface cutover' in text
assert 'Phase 4 — Legacy deletion' in text
assert '/call' in text
assert 'Maia is the control plane.' in text
assert 'Keryx is the collaboration plane.' in text
assert '## Phase handoff contract' in text
print('ok')
PY`

## Forbidden changes
- touching `src/maia/*.py`
- reviving deleted migration docs with mixed legacy story
- adding optional alternate public collaboration roots
