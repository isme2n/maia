# Maia Core Product PRD

## Product definition
Maia는 shared infra를 확인하고 띄운 뒤, agent identity를 만들고, agent별 `hermes setup`을 열고, runtime lifecycle을 운영하는 control plane이다.

## Core principles
1. Maia의 Part 1 public story는 operator flow 중심이다.
2. Maia는 Hermes를 재구현하지 않는다.
3. `doctor`는 infra readiness만 본다.
4. `setup`은 shared infra bootstrap만 담당한다.
5. `agent new`는 identity creation이다.
6. `agent setup`은 해당 agent에 대한 interactive CLI-only `hermes setup` passthrough 진입점이다.
7. messaging/thread/handoff surfaces는 남아 있어도 Part 1의 public golden flow는 아니다.

## In scope (Part 1 public contract)
- `maia doctor`
- `maia setup`
- `maia agent new <name>`
- `maia agent setup <name>`
- `maia agent start <name>`
- `maia agent stop <name>`
- `maia agent status <name>`
- `maia agent logs <name>`
- import/export/inspect는 보조 운영 surface로 유지

## Out of scope (for this contract lock)
- Maia-managed Hermes login/provider/auth wizard
- team defaults/model defaults/policy wizard
- `agent new` 단계에서 runtime image/provider/model 설정 강제
- messaging CLI surfaces를 Part 1 public story의 중심으로 두는 문서/도움말
- deeper runtime/setup implementation details

## Part 1 operator story
1. 운영자는 `maia doctor`로 Docker, queue, DB readiness를 확인한다.
- 운영자는 `maia setup`으로 shared infra를 bootstrap한다.
- canonical Maia SQLite DB filename is `~/.maia/maia.db`, and Keryx collaboration data remains stored as tables inside that same DB.
3. 운영자는 `maia agent new planner`로 agent identity를 만든다.
4. 운영자는 `maia agent setup planner`로 그 agent의 `hermes setup`을 연다.
5. 운영자는 `maia agent start planner`로 agent runtime을 시작한다.
6. 운영자는 필요할 때 `status`, `logs`, `stop`으로 운영 상태를 본다.

## Public CLI direction
### Shared infra
- `maia doctor`
- `maia setup`

### Agent lifecycle
- `maia agent new <name>`
- `maia agent setup <name>`
- `maia agent start <name>`
- `maia agent stop <name>`
- `maia agent status <name>`
- `maia agent logs <name>`

### Secondary surfaces
- `maia export [path]`
- `maia import <path>`
- `maia inspect <path>`
- Keryx collaboration visibility commands (`thread`, `handoff`, `workspace`) are secondary/operator-facing

## UX / DX rules
- help text는 현재 구현 상태를 과장하지 않는다.
- `doctor` wording은 Docker / queue / DB 같은 infra-only wording을 쓴다.
- `setup` wording은 shared infra bootstrap만 설명한다.
- `agent new` wording은 identity creation만 설명한다.
- `agent setup` wording은 `hermes setup` passthrough만 설명한다.
- public examples는 `doctor → setup → agent new → agent setup → agent start`를 먼저 보여준다.

## Part 2 direction
- Part 2의 제품 목표는 Keryx를 canonical collaboration root로 삼아 running agents가 multi-turn으로 협업하는 것이다.
- Maia는 control plane과 Keryx-backed visibility surface를 제공하고, live delivery 세부 구현은 public collaboration identity가 아니다.
- legacy broker/call-era `send` / `reply` / `inbox` CLI contract는 제거 대상이며 유지 계약이 아니다.
- Maia public surface에서는 Keryx collaboration object를 `thread` / `thread_id`로 부르고, Hermes의 `session` 개념과 섞지 않는다.
- `thread` / `handoff` / `workspace`는 Keryx-backed open collaboration visibility surface로 남고, `workspace`는 operator가 collaboration follow-up에 필요한 participant runtime/workspace context를 보는 surface다.
- public operator visibility flow는 `thread list -> thread show -> handoff show -> workspace show -> agent status -> agent logs` 순서로 닫는다.

## Success criteria for this contract lock
- README/help/tests/plan이 같은 public flow를 말한다.
- `doctor` 설명에 Hermes auth/provider/login checks가 없다.
- `setup` 설명에 team/model defaults wizard 서사가 없다.
- messaging commands are removed from public golden flow examples.
- `agent setup` is described as an interactive CLI-only passthrough to `hermes setup`.
- Part 2 is described as Keryx-rooted real agent collaboration, not a CLI messenger product.

## Part 2 completion criteria
- running agent 두 개 이상이 Keryx-rooted collaboration state를 통해 multi-turn message exchange를 한다.
- Maia는 `thread`, `handoff`, `workspace`, `agent status`, `agent logs`를 하나의 operator visibility story로 보여준다.
- operator는 `thread list`와 `thread show`에서 pending thread, recent handoff, participant runtime 상태를 직접 볼 수 있다.
- README/help/tests/roadmap/phase plan이 같은 Part 2 closeout story를 말한다.
