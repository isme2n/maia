# Maia Open Source Roadmap (Draft v0)

Date: 2026-04-21
Owner: Maia core (initial draft by Hermes)
Status: Draft (changeable)

## Product stance (locked for this draft)
- Maia = control plane
- Keryx = collaboration plane
- User collaboration entry = `/keryx <instruction>`
- `/call`, `/agent-call` are removal targets (not active product contract)
- Collaboration delivery contract = `delivery_mode`
  - `agent_only`
  - `user_direct`
- `user_direct` delivery failure must be explicit `failed` (no silent downgrade)

## Recommended defaults (initial)
- License: Apache-2.0
- Governance: BDFL + lightweight RFC process
- Official support scope (v0.x): Linux + Docker first
- Security disclosure: private channel + response SLA
- Telemetry: default OFF (opt-in only)

## 6-stream execution plan
1) Contract Freeze (first)
2) Runtime Reliability Hardening
3) Collaboration Boundary Security
4) Open-source Minimum Packaging
5) Contributor Onboarding System
6) Small-beta operation and v0.x release

---

## Stream 1 — Contract Freeze (first focus)

### Goal
Close all active contract drift so README/CLI-help/tests/code tell the same collaboration story.

### Must-close items
- `/keryx` single user instruction entrypoint policy is explicit.
- `/call` and `/agent-call` are not presented as active commands.
- `delivery_mode` command semantics are explicit in code/tests/docs.
- `user_direct` failure semantics are explicit (`failed`).

### Done criteria
- Contract mismatch count across docs/help/tests/code = 0
- Golden contract tests green

### Immediate task pack
- Task 139 (in progress/landed): message-level `delivery_mode` model + tests
- Task 140 (next): contract freeze surface alignment spec
- Task 141 (next): user_direct failure semantics hardening spec

---

## Stream 2 — Runtime Reliability Hardening

### Goal
Show operational trust through measurable reliability, not claims.

### Targets
- 7-day soak with zombie=0
- restart/self-heal success >= 99%
- reproducible failure drills + regression automation

---

## Stream 3 — Collaboration Boundary Security

### Goal
No internal collaboration leak to user channels; strict user-direct policy gates.

### Targets
- non-anchor cannot issue `user_direct`
- gateway is single user-channel send path
- delivery receipts (`sent|failed`) fed back into thread timeline

---

## Stream 4 — OSS minimum packaging

### Goal
New user can run local Maia in <=30 minutes.

### Targets
- license/notice/3rd-party clean
- `.env` manual hacking not required for first-run baseline
- quickstart and compose samples stable under CI

---

## Stream 5 — Contributor onboarding

### Goal
External contributor can independently create one passing PR.

### Targets
- CONTRIBUTING/ARCHITECTURE/ROADMAP/GOOD_FIRST_ISSUE
- issue/PR templates + style/test policy
- Codex harness dev loop docs

---

## Stream 6 — Beta ops

### Goal
Close P0/P1 from real users before public confidence claims.

### Targets
- 5~10 user beta
- P0/P1 closure before release tag
- v0.x changelog + known limitations + migration notes

---

## Decision log
- This is intentionally draft-first and changeable.
- At each stream boundary, tighten with explicit metrics and acceptance tests.
- Part 3 portable-state contract is the current Maia baseline: `maia export` default snapshot, `maia export <path>` explicit snapshot, safety-first `maia import <path>`, and optional-support `maia inspect <path>`. Recorded closeout evidence: `python3 -m maia --help`, `python3 -m maia export --help`, `python3 -m maia import --help`, and `python3 -m pytest -q tests/test_cli.py tests/test_keryx_models.py tests/test_keryx_storage.py tests/test_keryx_server.py`. Runtime-focused portable-state checks are tracked in `docs/contracts/portable-state-drift-checks.md` as follow-up drift checks. Later OSS streams should package and document this baseline, not quietly expand portable-state scope.
