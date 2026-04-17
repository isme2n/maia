# Task 122 — delegation state contract and transition table lock

## Goal
- direct-agent delegation loop에 필요한 최소 state contract를 먼저 잠근다.
- 구현보다 먼저 delegation_status, anchor preservation, internal turn semantics를 명확히 정의해서 worker/reviewer 해석 차이를 줄인다.

## Roadmap position
- This is design input for the later Part 4 execution path.
- Do not treat this task alone as permission to pull broader implementation ahead of Part 3 unless explicitly chosen.

## Non-goals
- CLI status rendering 구현
- live runtime smoke closeout
- broad storage/runtime refactor

## Allowed files
- `docs/tasks/120-direct-agent-delegation-first-conversation-ux.md`
- `docs/tasks/122-delegation-state-contract-and-transition-table-lock.md`
- `docs/plans/phase18-direct-agent-delegation-and-user-anchored-collaboration.md`
- `src/maia/message_model.py`
- `tests/test_cli.py`

## Acceptance criteria
- [x] the delegation loop defines an original conversation anchor explicitly
- [x] the task spec defines when delegation_status becomes pending / needs_user_input / answered / handoff_ready
- [x] the task spec defines which events are internal agent-to-agent turns versus user-facing relays
- [x] reviewer can decide fake relay vs real delegation using the written contract
- [x] scoped review approves the state contract

## Closeout evidence
- Validation passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
  - Result: `70 passed`
- Scoped spec review: `approve`
- Scoped quality review: `approve`
- Contract lock outcome:
  - original user <-> anchor-agent conversation is now explicit
  - delegation_status transitions are explicit and aligned across Task 120, Task 122, and Phase 18
  - fake relay vs real delegation rejection criteria are explicit for future reviewers

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- broad implementation bundled into the state-contract task
- leaving status semantics implicit
- using vague prose instead of concrete event/state mapping

## Worker/reviewer notes
- Worker should prefer exact event/state tables over descriptive paragraphs.
- Reviewer should reject any contract that still leaves anchor preservation ambiguous.

## Minimum contract to lock

### Original conversation anchor
- `original conversation anchor` means the specific user <-> agent conversation where the request started.
- In the canonical loop `user -> A -> B -> A -> user`, agent `A` is the anchor agent.
- The anchor is preserved for the whole delegation loop even while agent `B` and any later delegate agents exchange internal messages.
- Final user-facing completion must return into that original `user -> A` conversation context, not into a synthetic Maia relay surface and not into B's internal thread.

### Internal delegation thread vs user-facing relay
| Event | Internal agent-to-agent turn? | User-facing relay? | Notes |
|---|---|---|---|
| User asks anchor agent A for work | No | Yes | This creates or continues the original anchor conversation. |
| A sends delegated request to B | Yes | No | This must exist as a real A -> B message in collaboration state. |
| B asks A a follow-up question | Yes | No | Internal question turn; do not count this alone as the user-visible relay. |
| A relays B's blocking question to the user | No | Yes | This is the anchor agent speaking to the user in the original conversation. |
| User answers A | No | Yes | User stays attached to A, not directly to B. |
| A sends the user's answer back to B | Yes | No | Real internal answer turn that continues the delegation thread. |
| B sends non-blocking progress/report to A | Yes | No | Internal update; may later be summarized to the user by A. |
| A relays meaningful progress/report to the user | No | Yes | Optional user-facing relay from the anchor conversation. |
| B sends final result/handoff to A | Yes | No | Final internal result turn that makes return-to-user possible. |
| A returns the final answer/result to the user | No | Yes | Required closeout in the original user -> A conversation. |

### Delegation status transition table
The status values below are the minimum state contract for the direct delegation loop. They describe what the anchor agent currently owes or expects relative to the delegated agent.

| Triggering event | delegation_status | Set on which conversation? | Meaning | Required evidence |
|---|---|---|---|---|
| A creates a real delegated request message to B | `pending` | The original user <-> A anchor conversation | A is waiting on B's next internal turn. | Stored A -> B request in the delegation thread. |
| B sends a blocking `question` that requires user clarification before B can continue | `needs_user_input` | The original user <-> A anchor conversation | A must ask the user and cannot finish the delegation without a user answer. | Stored B -> A question turn, plus reviewer can see it is blocking. |
| A sends B an `answer` that relays the user's clarification | `answered` | The original user <-> A anchor conversation | A has answered B's blocking question and the delegation is back in B's hands. | Stored A -> B answer turn replying to the blocking question. |
| B sends a non-final `report` or non-blocking answer/update to A | `answered` | The original user <-> A anchor conversation | A has a meaningful internal update/result to relay, but the final handoff is not complete yet. | Stored B -> A report/answer turn that is not the final handoff. |
| B sends final `handoff` or final result/report to A for return to the user | `handoff_ready` | The original user <-> A anchor conversation | The delegated work is complete enough for A to deliver the result back into the anchor conversation. | Stored final B -> A handoff/result turn. |

### Status interpretation constraints
- `pending` begins only after a real agent-to-agent request exists. It must not be set from a local intent, a draft, or a fake summary line.
- `needs_user_input` is only for a delegated agent's blocking question that truly requires the user through the anchor agent. Pure progress reports do not set it.
- `answered` has exactly two allowed meanings in this narrow contract:
  1. A answered B's blocking question and B can continue.
  2. B sent A a meaningful but non-final answer/report/update.
- `handoff_ready` means B has already produced the final internal result for A. It is the precondition for A's final user-facing return, not the user-facing return itself.

### Fake relay vs real delegation review test
Reviewer should reject the change if the written contract still allows any of the following:
- `delegation_status` changing without a corresponding stored internal A <-> B message event.
- A synthesized "Tech is asking..." or "Tech finished..." relay to the user without an actual prior B -> A internal turn.
- Final completion that lands in an operator/relay surface instead of the original user <-> A anchor conversation.
- Any interpretation where Maia only mutates local state and pretends an internal delegation happened.
