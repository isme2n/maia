# Maia runtime permission policy

## Status
Proposed direction for runtime behavior and approval policy.

## Problem
We observed a repeatable ownership failure in mounted Hermes agent homes.

When a runtime container runs as root and writes into a host-mounted agent home, it leaves behind root-owned files on the host. After that, normal host-side maintenance can fail: skill install, updates to the agent home, and other routine cleanup no longer work without manual repair.

This is the root cause to fix.

## Decision
Maia should use a 3-layer permission model:

1. Container-internal permissions
   - Inside the runtime container, normal agent work should stay permissive and practical.
   - The goal is to avoid making routine agent execution brittle.
   - Most normal work inside the container should run automatically without extra approval.

2. Mounted host state
   - Anything written to mounted host paths should have deterministic, non-root ownership.
   - Runtime containers should run as the host uid/gid so files created in mounted agent homes stay owned by the same user on the host.
   - This prevents new ownership drift across skill installs, agent-home updates, and other ongoing maintenance.

3. Control-plane state
   - Control-plane data and mounts should stay protected and minimal-privilege.
   - Use read-only access where possible, and only grant write access where Maia truly needs it.
   - This keeps runtime agents from gaining broader access than their task requires.

## Approval policy split
The permission model also defines how approvals should feel in practice:

- Container-internal normal work: mostly automatic.
- Host-destructive or system-wide actions: require explicit approval.

That keeps day-to-day agent work fast while still putting a clear checkpoint in front of actions that can damage host state or affect the wider machine.

## Rationale
This split matches the actual risk boundaries:

- Internal container work is expected, frequent, and usually recoverable.
- Mounted host state is durable and must keep correct ownership.
- Control-plane state is sensitive and should be exposed as narrowly as possible.

Running the runtime container as the host uid/gid is the key fix because it addresses the observed failure at the source instead of trying to clean it up afterward.

## Expected outcome
- New runtime sessions should stop creating root-owned files in mounted Hermes agent homes.
- Host-side skill install and agent-home maintenance should continue to work normally for new runs.
- Approval prompts should focus on genuinely risky host-destructive or system-wide actions, not routine internal work.

## Non-goal: retroactive repair
This policy is forward-looking.

It should stop new runs from causing ownership drift, but it does not automatically repair agent homes that were already corrupted by earlier root-owned writes. Those existing homes may still need a one-time manual ownership repair.
