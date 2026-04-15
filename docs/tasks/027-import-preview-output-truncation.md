# Task 027 — import preview output truncation

## Goal
Keep Maia import preview readable when many agents are added, removed, or changed by truncating long id/name/detail lists while preserving the summary counts.

## Why now
- Task 026 added a risk line, which improved fast triage.
- The remaining readability problem is long preview lines when many agents are affected.
- Operators need the preview to stay scan-friendly even for large or replacement-like imports.

## Scope
- Truncate long `added`, `removed`, and `changed` value lists.
- Apply truncation to:
  - ids
  - names
  - changed details
- Keep summary counts unchanged.
- Use a deterministic compact suffix so operators can tell more items exist.

## Non-goals
- No paging.
- No multiline per-agent expansion.
- No JSON output mode.
- No color formatting.

## Output contract
Existing line structure stays the same:
- `added ids=... names=...`
- `removed ids=... names=...`
- `changed ids=... names=... details=...`

If a list exceeds the display limit, show the first N entries followed by a compact suffix:
- `...(+X)`

Example:
- `added ids=a1,a2,a3,a4,a5,...(+2) names=alpha,beta,gamma,delta,eps,...(+2)`
- `changed ids=id1,id2,id3,id4,id5,...(+3) names=n1,n2,n3,n4,n5,...(+3) details=id1:persona:...,...(+3)`

## Proposed rules
- Display limit: 5 items per list.
- If list length <= 5, render the full comma-separated list.
- If list length > 5, render:
  - first 5 items
  - then `...(+<remaining>)`
- Empty lists still render `-`.

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- Small previews are unchanged.
- Large `added`, `removed`, and `changed` lists truncate after 5 items.
- Truncation preserves the summary counts on the `preview` line.
- The truncation marker is machine-readable and contains the hidden count.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
