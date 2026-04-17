# Maia Product Roadmap — 5 Parts

> **For Hermes:** Use subagent-driven-development skill to execute this roadmap one part at a time. Do not expand scope between parts. Finish, verify, and close each part before starting the next.

**Goal:** Maia를 5개의 큰 파트로 나눠 끝까지 밀어서, 최종적으로는 오픈소스로 공개 가능한 깔끔한 멀티 에이전트 control plane 제품으로 닫는다.

**Product definition:** Maia는 여러 Hermes 에이전트 컨테이너를 생성·설정·실행·관찰하는 control plane이다. 에이전트 간 실제 상호작용은 queue/message/toolcall plane에서 일어나고, Maia는 인프라/lifecycle/상태/관찰을 관리한다.

**Completion rule:** 각 파트는 구현 + 테스트 + 문서 정렬 + reviewer approve + clean worktree까지 끝나야 완료로 본다.

---

## Part 1 — Bootstrap / Control Plane Foundation

**Goal:** 일반 사용자가 `doctor → setup → agent new → agent setup → agent start` 흐름으로 첫 에이전트를 띄울 수 있게 만든다.

**What must be true at the end of Part 1:**
- `maia doctor`는 인프라만 점검한다.
- `maia setup`은 shared infra를 준비한다.
- `maia agent new <name>`는 agent identity를 만든다.
- `maia agent setup <name>`는 해당 agent 환경에서 `hermes setup`을 그대로 열어준다.
- `maia agent start <name>`는 setup이 끝난 agent만 시작한다.
- public docs/help/tests가 이 흐름으로 정렬된다.

**Includes:**
- Docker / queue / DB readiness
- shared infra bootstrap
- agent identity creation
- agent setup passthrough
- setup-gated runtime start

**Current working plan:**
- `docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md`

---

## Part 2 — Real Agent Conversation

**Goal:** 실제 실행 중인 agent들이 queue와 toolcall 중심으로 여러 번 왕복 대화할 수 있게 만든다.

**What must be true at the end of Part 2:**
- running agent 두 개 이상이 실제 broker를 통해 메시지를 주고받는다.
- multi-turn question / answer / report 흐름이 된다.
- Maia는 `thread`, `handoff`, `workspace`, `agent status`, `agent logs`를 하나의 operator visibility flow로 묶어 보여준다.
- operator는 누가 대기 중인지, 어떤 thread가 열려 있는지, 최근 handoff와 participant runtime 상태를 볼 수 있다.
- 이 흐름이 “CLI가 대신 대화하는 제품”처럼 보이지 않고, 실제 agent-to-agent message plane으로 정리된다.

**Includes:**
- broker-backed messaging hardening
- actual queue delivery/ack semantics
- thread/message visibility
- toolcall/message plane story alignment

**Current working plan:**
- `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`
- Closeout note: Task 117 restored the public first-run bootstrap path so `agent start` no longer needs a hidden `agent tune` prerequisite, and fresh-home live validation covered broker-backed reply plus file handoff visibility.

---

## Part 3 — Export / Import

**Goal:** Maia 팀 상태를 안전하게 export/import/inspect 할 수 있게 마무리한다.

**What must be true at the end of Part 3:**
- export/import/inspect가 제품의 정식 이동/백업/복구 surface로 닫힌다.
- preview/diff/warning/confirm 흐름이 안정적이다.
- portable state와 runtime-only state 경계가 명확하다.
- operator가 팀 상태를 안전하게 옮길 수 있다.

**Includes:**
- portable state scope finalization
- preview/risk/warning UX hardening
- import/export docs/help/tests alignment
- bundle stability

---

## Part 4 — UX Closeout

**Goal:** 전체 제품 표면을 군더더기 없이 정리해서 일반 사용자가 흐름을 바로 이해할 수 있게 만든다.

**What must be true at the end of Part 4:**
- help text, README, examples, command wording이 하나의 제품 서사로 정렬된다.
- operator-facing 에러 메시지가 평이하고 직접적이다.
- setup/new/start/status/logs/export/import 등 핵심 흐름이 혼란 없이 보인다.
- 제품 표면에서 불필요한 내부 용어/임시 서사/debug-like surface가 정리된다.
- direct-agent conversation과 agent-to-agent 부탁 UX가 제품 문장으로 자연스럽게 보인다.

**Includes:**
- command naming and help cleanup
- README golden flow rewrite
- plain-language operator messages
- surface simplification
- direct-agent delegation-first conversation UX wording and closeout

**Planned design input:**
- `docs/plans/phase18-direct-agent-delegation-and-user-anchored-collaboration.md`
- Part 4 wording must keep the public story as `user -> A -> B -> A -> user`, with agent A staying the user-facing anchor instead of Maia becoming a front desk.

---

## Part 5 — Open Source Polish

**Goal:** Maia를 외부에 공개해도 되는 수준으로 제품 표면, 문서, 구조를 정리한다.

**What must be true at the end of Part 5:**
- README 첫인상이 제품답다.
- 설치/빠른 시작/개념 설명이 짧고 분명하다.
- contributor-facing 문서와 user-facing 문서가 분리된다.
- 내부 테스트 인프라/과도기 surface/debug 경로가 공개 제품 표면에 덜 드러난다.
- 공개 저장소 기준으로 어색한 군더더기가 정리된다.

**Includes:**
- public README cleanup
- CONTRIBUTING / TESTING / architecture docs separation
- internal vs public surface separation
- final repo polish for open-source release

---

## Execution order
1. Part 1 — Bootstrap / Control Plane Foundation
2. Part 2 — Real Agent Conversation
3. Part 3 — Export / Import
4. Part 4 — UX Closeout
5. Part 5 — Open Source Polish

## Rules for execution
- Never work on later parts before the current part is closed.
- Each part needs:
  - targeted tests
  - full verify where relevant
  - docs/help/tests alignment
  - reviewer approve
  - clean worktree
- If product scope feels ambiguous, prefer the simpler control-plane interpretation.
- Do not reintroduce unnecessary abstraction layers, defaults hierarchies, or product-surface clutter.

## Progress tracker
- [x] Part 1 complete
- [x] Part 2 complete
- [ ] Part 3 complete
- [ ] Part 4 complete
- [ ] Part 5 complete
