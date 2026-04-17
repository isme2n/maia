# Task 120 — direct-agent delegation-first conversation UX

## Goal
- Maia의 다음 제품 중심 흐름을 “사용자가 각 에이전트와 직접 대화하고, 대화 중인 에이전트가 다른 에이전트에게 부탁한 뒤 결과를 다시 가져오는 경험”으로 고정한다.
- 즉 Maia를 거대한 운영 대시보드보다 먼저, direct conversation + agent-to-agent 부탁 UX가 자연스러운 control plane으로 발전시킨다.

## Why this task is next product-wise
- Part 1/2 closeout으로 이제 기본 bootstrap, live broker reply, self-discovery, stale runtime image guard까지 닫혔다.
- 하지만 현재 제품 체감 가치는 아직 “실행되는 인프라”에 더 가깝고, 사용자가 바로 느끼는 핵심 경험은 덜 닫혀 있다.
- 사용자가 원하는 1차 흐름은 다음과 같다:
  - 사용자는 경제/테크/퍼스널 같은 각 에이전트와 직접 대화한다.
  - 예: “경제야, 테크한테 크롤러 하나 만들어달라고 해.”
  - 경제는 테크에게 부탁하고, 필요하면 중간 질문/보고를 왕복한 뒤, 최종 결과를 다시 사용자에게 가져온다.
- 동적 에이전트 추가는 필요하지만, 이 흐름보다 앞선 1차 제품 가치로 두지 않는다.

## Product behavior to lock
- 사용자는 메인 창구 하나가 아니라 개별 에이전트와 직접 대화한다.
- 대화 중인 에이전트는 다른 에이전트에게 request / question / report / handoff를 보낼 수 있다.
- 내부 부탁 흐름은 one-shot queue가 아니라 multi-turn 메시징이어야 한다.
- 사용자에게는 “지금 누구에게 부탁 보냄 / 답 기다리는 중 / 답 받음” 정도의 최소 가시성이 보여야 한다.
- 최종 결과는 내부 thread에 갇히지 않고, 원래 사용자와 대화하던 에이전트의 대화로 되돌아와야 한다.

## Non-goals
- 거대한 운영 대시보드/관제 UI를 먼저 만드는 것
- 동적 agent 추가 UX를 이번 태스크의 중심 가치로 두는 것
- Slack/Telegram/Discord 전체 플랫폼 통합을 한 번에 끝내는 것
- fully autonomous planner/router를 먼저 만드는 것
- 새로운 추상 용어를 public surface에 늘리는 것

## Recommended scope
- direct conversation 중인 agent가 다른 agent에게 부탁할 수 있는 public contract 정의
- 부탁/응답/재질문/중간보고/결과복귀 흐름의 thread contract 정의
- 최소 visibility surface 정의
- representative live smoke contract 정의
- docs/help/tests가 이 제품 서사와 맞도록 정렬

## Core public story
1. 사용자는 특정 agent와 직접 대화한다.
2. 그 agent가 다른 agent의 도움이 필요하다고 판단한다.
3. 현재 대화 agent는 상대 agent에게 부탁을 보낸다.
4. 상대 agent는 추가 질문이나 중간 보고를 보낼 수 있다.
5. 현재 대화 agent는 그 흐름을 이어받아 사용자에게 설명하거나 추가 정보를 요청한다.
6. 상대 agent가 결과를 보내면, 현재 대화 agent는 그것을 사용자 대화 맥락으로 다시 전달한다.

## Example product flow
- User -> economist:
  - “테크한테 크롤러 하나 만들어달라고 해.”
- Economist -> tech:
  - request: crawler implementation request
- Tech -> economist:
  - question/report: target site or output format clarification
- Economist -> User:
  - “테크가 사이트/출력 형식을 물어봅니다.”
- User -> economist:
  - clarification
- Economist -> tech:
  - answer with clarification
- Tech -> economist:
  - report/handoff with result
- Economist -> User:
  - final summarized result + optional handoff pointer

## Product contract requirements
- Maia should not look like a fake CLI message relay pretending to be collaboration.
- Maia should support real running agent-to-agent conversation with multiple turns.
- The user-facing active conversation agent must remain the primary anchor.
- Internal collaboration artifacts must be visible enough for trust/debugging, but should not force the user to inspect raw internal state for normal use.

## Minimum visibility contract
At minimum, the active conversation surface should be able to show:
- delegated_to=<agent>
- delegation_status=pending|needs_user_input|answered|handoff_ready
- current_thread_id
- latest_internal_update summary

### Delegation status transition contract
| Event | delegation_status | Meaning |
|---|---|---|
| A sends delegated request to B | `pending` | waiting on B |
| B sends a blocking question that needs user clarification | `needs_user_input` | A must ask the user and relay the answer |
| A sends B an answer relaying the user's clarification, or B sends a progress/non-final answer back to A | `answered` | A has relayed or received a meaningful internal answer/update, but final handoff is not complete |
| B sends final result/handoff to A | `handoff_ready` | final result is ready to return to the original conversation |

### Minimum anchor and relay semantics
- The original conversation anchor is always the user-facing conversation between the user and the currently active agent A.
- In `user -> A -> B -> A -> user`, all A <-> B messages are internal agent-to-agent turns, and all user-visible updates remain in the original user <-> A conversation.
- `delegation_status` is attached to that original user <-> A anchor conversation, not to a synthetic Maia relay surface and not to B's internal subthread.
- Reviewers should reject any implementation that allows status changes or user-visible relays without a corresponding stored internal A <-> B message turn.

Avoid turning this into a heavy dashboard-first product.

## Candidate implementation surface
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/hermes_runtime_worker.py`
- `src/maia/message_model.py`
- `src/maia/collaboration_storage.py`
- `src/maia/rabbitmq_broker.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_hermes_runtime_worker.py`
- `README.md`
- `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`
- `docs/plans/maia-product-roadmap-5-parts.md`
- `docs/tasks/120-direct-agent-delegation-first-conversation-ux.md`

## Suggested implementation breakdown
### Task 121 — contract-first wording/spec lock
- Define the exact public story for “talk to one agent, that agent asks another agent, result returns to original conversation”.
- Lock the wording that the user starts with a specific named agent and that same agent remains the user-facing anchor.
- Include a concrete public example shaped like `user -> A -> B -> A -> user`.
- Keep Task 121 docs/help/tests-only; do not pull runtime or state-machine behavior into it.
- Decide which existing surfaces carry this story:
  - direct chat surface
  - thread/handoff visibility
  - status summaries

### Task 122 — delegation state contract and transition table
- Lock the exact event/state semantics for:
  - original conversation anchor
  - delegated request
  - clarification request
  - progress report
  - final result return
- Ensure reviewers can distinguish real delegation from fake local shortcuts.

### Task 123 — user-facing active conversation updates
- Add minimal visibility so the user can tell:
  - which agent the current agent asked
  - whether the system is waiting on another agent or the user
  - whether a result is ready

### Task 124 — live runtime regression flow
- Add a representative live smoke where:
  - user talks to agent A
  - A asks B for help
  - B asks a follow-up question or sends a progress update
  - A relays that back to the user
  - B returns the final result
  - A delivers the final answer back in the original conversation

## Acceptance criteria
- [ ] Maia has an explicit public product story for direct-agent conversation with agent-to-agent 부탁
- [ ] The active conversation agent remains the user-facing anchor while collaborating internally
- [ ] Multi-turn internal collaboration is supported: request -> question/report -> answer -> final result
- [ ] The user can see minimal delegation status without opening a separate heavy operator dashboard
- [ ] Representative live smoke proves result return to the original conversation context
- [ ] README/help/tests align with this story

## Required validation direction
- Targeted tests for message/thread semantics
- Targeted tests for user-visible delegation status summaries
- Live smoke covering user -> A -> B -> A -> user loop
- Scoped review focused on contract compliance and “not just a fake relay” risk

## Forbidden changes
- Reframing Maia back into a central dispatcher/chatbot front desk
- Making dynamic agent addition the main product story for this task
- Replacing real agent-to-agent flow with a fake local shortcut that only updates stored state
- Adding large dashboard-like surfaces before the core direct conversation loop is solid
- Introducing new public jargon when plain language works

## Deliverable of this task
- A phase/task design package that is safe to execute later and makes “talk to one agent, that agent asks another, result comes back to you” the explicit Maia product behavior.
- This task itself is design-first input for later execution; it does not authorize pulling Part 4 implementation ahead of the roadmap order unless the user explicitly chooses to do so.
- Under this phase, Tasks 121-124 are the only execution units; Task 120 is the parent framing/spec task.
