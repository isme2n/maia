# Task 032 — portable state v2 scope planning

## Goal
Define the next portable-state boundary for Maia so future export/import work can expand deliberately beyond the current registry-only snapshot.

## Why now
- Import/export UX is now strong enough for the current v1 contract.
- The next meaningful step is not more preview polish, but deciding what should count as portable Maia state in v2.
- Without an explicit scope plan, future fields risk being added implicitly and weakening the portability contract.

## Planning decisions
### Current v1 reality
Portable today:
- registry entries containing:
  - `agent_id`
  - `name`
  - `status`
  - `persona`

Runtime-only today:
- `processes`
- `locks`
- `cache`
- `live-sessions`

### Proposed v2 principle
Portable state should contain durable operator intent, not transient execution residue.

That means v2 should only add state that answers:
- “If I move this Maia team to another machine, what configuration should still be true?”

It should not add state that answers:
- “What happened to be alive, cached, or locked on the old machine at export time?”

## Proposed v2 portable additions
### 1. Agent profile metadata
Intent: preserve agent identity beyond name/persona.

Candidate fields:
- `role`
  - short operational role like `research`, `reviewer`, `ops`
- `model`
  - preferred model id or model alias for that agent
- `tags`
  - operator-defined labels for grouping/filtering

Reason to include:
- these affect how the team is intentionally organized
- they remain meaningful after migration

### 2. Agent launch defaults
Intent: preserve restartable configuration without exporting live runtime state.

Candidate fields:
- `platform`
  - target interaction platform or runtime class
- `working_directory`
  - intended project or state directory
- `env_refs`
  - references to environment keys or secret names, not secret values
- `disabled`
  - optional operator intent that an agent exists but should not auto-start

Reason to include:
- these describe how an agent should be relaunched
- they are declarative, not ephemeral

Important rule:
- export references to secrets, not secret contents
- v2 must never bundle raw credentials

### 3. Team-level metadata
Intent: preserve the identity of the exported Maia team as a team, not just a flat list of agents.

Candidate fields:
- `team_name`
- `team_description`
- `team_tags`
- `default_agent_id`

Reason to include:
- useful when moving multiple Maia states around
- improves inspect/import clarity

## Explicit v2 non-goals
These should remain runtime-only in v2:
- live process ids
- terminal sessions
- active locks
- caches
- in-flight jobs
- message queues / broker contents
- transient logs
- browser/session cookies
- raw secret values
- container ids / docker runtime state

## Suggested manifest evolution
Current:
- `scope_version=1`
- `portable_state_kinds=["registry"]`

Suggested v2:
- `scope_version=2`
- `portable_state_kinds` may expand to something like:
  - `registry`
  - `agent-launch-defaults`
  - `team-metadata`

Important constraint:
- do not claim a new state kind in manifest until there is an import/export contract and validation for it.

## Recommended rollout order
### Phase 1
Add only team-level metadata.

Why first:
- lowest migration risk
- no runtime coupling
- improves inspect/export UX immediately

### Phase 2
Add agent profile metadata:
- `role`
- `model`
- `tags`

Why second:
- still highly portable
- useful for Maia control-plane identity
- minimal security risk

### Phase 3
Add agent launch defaults cautiously:
- `platform`
- `working_directory`
- `env_refs`
- `disabled`

Why third:
- highest chance of host-specific edge cases
- needs the strongest validation rules

## Validation rules to keep for v2
- portable state must stay declarative
- no secrets in cleartext
- no host-specific live runtime handles
- inspect must expose the expanded portable scope clearly
- import preview must show diffs for any new portable fields before apply
- scope_version must change only when the portable contract meaningfully expands

## Recommended next implementation task
Implement team-level metadata first.

Suggested next feature slice:
- add optional team metadata to manifest/export/import/inspect
- keep agent record schema unchanged for that slice
- avoid mixing team metadata with launch-default fields in the same task
