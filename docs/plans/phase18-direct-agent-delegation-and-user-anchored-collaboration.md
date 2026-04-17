# Phase 18 Direct-Agent Delegation and User-Anchored Collaboration Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Use one fresh worker per task, then one fresh reviewer per task. Do not merge tasks. Do not broaden file scope. Re-run validation after every fix. If review finds contract ambiguity, patch the task spec first, then re-run the worker/reviewer loop.

**Goal:** Maia의 다음 제품 중심 흐름을 “사용자가 특정 에이전트와 직접 대화하고, 그 에이전트가 다른 에이전트에게 부탁한 뒤 결과를 다시 사용자 대화로 가져오는 경험”으로 닫는다.

**Architecture:** Maia는 계속 control plane으로 남되, 사용자 대화의 중심 anchor는 항상 현재 대화 중인 agent가 가진다. 내부 협업은 broker/thread/handoff plane에서 multi-turn으로 일어나고, 사용자는 무거운 대시보드 없이도 delegation 상태를 최소한으로 볼 수 있어야 한다. 동적 agent 추가는 깨지지 않게 유지하되, 이번 phase의 1차 제품 가치는 direct conversation + agent-to-agent 부탁 loop에 둔다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, SQLite collaboration state, RabbitMQ broker adapter, Docker runtime, pytest.

---

## Product story to lock
1. 사용자는 메인 창구 하나가 아니라 특정 agent와 직접 대화한다.
2. 현재 대화 agent는 다른 specialist agent의 도움이 필요하면 내부 delegation을 건다.
3. delegated agent는 request를 받고 질문 / 중간 보고 / 결과 전달을 여러 번 왕복할 수 있다.
4. 현재 대화 agent는 내부 흐름을 흡수해 사용자에게 필요한 최소 상태와 결과를 다시 전달한다.
5. 사용자는 normal flow에서 raw internal thread를 뒤지지 않아도 된다.
6. Maia itself must not read like the front desk for this loop; the currently active agent stays the visible anchor.

## Example story
- User -> economist: “테크한테 크롤러 하나 만들어달라고 해.”
- Economist -> tech: delegated request
- Tech -> economist: clarification question or progress report
- Economist -> User: “테크가 사이트 / 출력 형식을 물어봅니다.”
- User -> economist: clarification
- Economist -> tech: answer
- Tech -> economist: result report / handoff
- Economist -> User: final answer in the original conversation

## Hard rules
- Maia must not regress into a central dispatcher/front-desk chatbot story.
- The active conversation agent must remain the user-facing anchor.
- Internal collaboration must be real multi-turn agent-to-agent messaging, not a fake local shortcut that only mutates stored state.
- Visibility should be lightweight and embedded in the active conversation flow before any dashboard-first expansion.
- Dynamic agent addition stays supported, but it is not the primary value proposition of this phase.

## Scope
- direct-agent delegation product contract
- minimal metadata/state to preserve original conversation anchor
- active-conversation delegation status surface
- representative live runtime regression: user -> A -> B -> A -> user
- docs/help/tests alignment for this story

## Out of scope
- full Slack/Telegram/Discord productization in one shot
- giant operator dashboard
- autonomous routing/planning layer that hides the direct-agent story
- new storage backend or broker redesign
- export/import work (keep Part 3 order intact for implementation priority)

## Phase ordering note
- This phase is the correct next product-shaping design after Part 2, but code execution should still respect the roadmap’s current part ordering.
- That means: lock the design/spec now, then execute it when the roadmap order allows or when the user explicitly chooses to pull it forward.

---

## Recommended task breakdown
1. Task 121 — public contract and active-conversation anchor lock
2. Task 122 — delegation state contract and transition table lock
3. Task 123 — minimal user-facing status surface
4. Task 124 — live runtime delegation loop regression and closeout

### Task 121 contract note
- Scope is wording/help/tests/docs only.
- Lock the public example shape as `user -> A -> B -> A -> user`.
- Lock the phrase-level story that users talk directly to a specific agent and that same agent remains the user-facing anchor while delegating.

---

## Worker/reviewer execution protocol
For every task in this phase:
1. Freeze the task spec first.
2. Run one worker with only the allowed files.
3. Run targeted validation yourself outside the worker.
4. Run one scoped reviewer that ignores unrelated repo noise.
5. If reviewer finds ambiguity, patch the task spec before the next worker run.
6. Only commit after validation passes and reviewer approves.

### Review bar
- contract compliance first
- then regression risk in touched files
- then validation adequacy
- reject any implementation that feels like a fake relay instead of real agent collaboration

### Evidence reviewers must require for “real delegation”
A reviewer must not approve the phase closeout if the implementation only mutates local state or prints synthetic summaries.
At minimum, the closeout task must show:
- a real delegated request message from anchor agent A to delegate agent B
- at least one intermediate message from B back to A (`question` or `report`)
- persistence/visibility of that intermediate turn in thread/message state
- a relay from A back into the original user-facing conversation context
- a final result message from B to A
- a final result relay from A to the original user-facing conversation context

---

## Verification bar for the phase
- targeted pytest for each task
- broader CLI/runtime regression before closeout
- representative live smoke for user -> A -> B -> A -> user loop
- reviewer approve per task
- clean scoped commits
- docs/help/tests align to the same public story

## Acceptance criteria
- Maia has an explicit public story for direct-agent conversation with internal delegation.
- The active conversation agent remains the user-facing anchor while collaborating internally.
- Internal collaboration supports request -> question/report -> answer -> final result.
- The user can see minimal delegation status without a dashboard-first experience.
- A representative live smoke proves results return to the original conversation context.
- README/help/tests tell the same product story.
