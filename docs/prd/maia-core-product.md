# Maia Core Product PRD

## Product definition
Maia는 shared infra를 확인하고 띄운 뒤, agent identity를 만들고, agent별 `hermes setup`을 열고, runtime lifecycle을 운영하는 control plane이다. 공개 first-run story는 `maia init`이며, decomposed `doctor → setup → agent new → agent setup → agent start` 흐름은 advanced/manual operator flow로 유지한다.

## Core principles
1. Maia의 Part 1 public story는 `maia init` 중심이다.
2. `maia init`은 truthful onboarding command다. success는 selected agent가 실제로 conversation-ready일 때만 나온다.
3. decomposed `doctor → setup → agent new → agent setup → agent start`는 public advanced/manual operator flow로 남는다.
4. Maia는 Hermes를 재구현하지 않는다.
5. `doctor`는 infra readiness만 본다.
6. `setup`은 shared infra bootstrap만 담당한다.
7. `agent new`는 identity creation이다.
8. `agent setup`은 해당 agent에 대한 interactive CLI-only `hermes setup` passthrough 진입점이다.
9. messaging/thread/handoff surfaces는 남아 있어도 Part 1의 public golden flow는 아니다.

## In scope (Part 1 public contract)
- `maia init`
- `maia doctor`
- `maia setup`
- `maia agent new <name>`
- `maia agent setup <name>`
- `maia agent setup-gateway <name>`
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
- repo-level proof를 host-level smoke proof처럼 과장하는 release wording
- deeper runtime/setup implementation details

## Part 1 public onboarding story
1. 운영자는 `uvx maia init` 또는 설치 후 `maia init`로 Maia onboarding을 시작한다.
2. `maia init`은 shared infra, agent identity, agent setup, gateway/default destination, runtime 상태를 truthfully 보고하고, 부족하면 다음 명령을 바로 보여준다.
3. first-run path에서 필요하면 shared infra를 bootstrap하고, 첫 agent identity를 만들거나 선택하고, interactive CLI-only `hermes setup`을 열고, skipped gateway/default destination setup을 복구하고, 가능한 경우 runtime start까지 진행한다.
4. `maia init` success는 selected agent runtime이 실제로 running이고 conversation-ready일 때만 나온다.
5. decomposed public operator flow는 `maia doctor -> maia setup -> maia agent new -> maia agent setup -> maia agent start` 순서로 남는다.
6. canonical Maia SQLite DB filename is `~/.maia/maia.db`, and Keryx collaboration data remains stored as tables inside that same DB.
7. 운영자는 필요할 때 `status`, `logs`, `stop`으로 운영 상태를 본다.

## Public CLI direction
### Public onboarding
- `uvx maia init`
- `maia init`

### Advanced/manual operator flow
- `maia doctor`
- `maia setup`
- `maia agent new <name>`
- `maia agent setup <name>`
- `maia agent setup-gateway <name>`
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
- `maia init` wording은 readiness, next step, success condition을 truthfully 설명한다.
- `doctor` wording은 Docker / Keryx HTTP API / DB 같은 infra-only wording을 쓴다.
- `setup` wording은 shared infra bootstrap만 설명한다.
- `agent new` wording은 identity creation만 설명한다.
- `agent setup` wording은 `hermes setup` passthrough만 설명한다.
- public examples는 `uvx maia init` 또는 `maia init`을 먼저 보여주고, advanced/manual examples는 `doctor → setup → agent new → agent setup → agent start`를 유지한다.

## Release-readiness proof boundary
- repo-level proof는 README/help/tests 정렬과 fake-docker 기반 `maia init` orchestration coverage를 뜻한다.
- host-level proof는 Docker CLI, reachable daemon, 그리고 setup이 필요한 경우 Hermes CLI가 있는 실제 머신에서의 별도 smoke다.
- repo-level proof를 host-level proof처럼 말하지 않는다.

## Part 2 direction
- Part 2의 제품 목표는 Keryx를 canonical collaboration root로 삼아 running agents가 multi-turn으로 협업하는 것이다.
- Maia는 control plane과 Keryx-backed visibility surface를 제공하고, live delivery 세부 구현은 public collaboration identity가 아니다.
- legacy broker/call-era `send` / `reply` / `inbox` CLI contract는 제거 대상이며 유지 계약이 아니다.
- Maia public surface에서는 Keryx collaboration object를 `thread` / `thread_id`로 부르고, Hermes의 `session` 개념과 섞지 않는다.
- `thread` / `handoff` / `workspace`는 Keryx-backed open collaboration visibility surface로 남고, `workspace`는 operator가 collaboration follow-up에 필요한 participant runtime/workspace context를 보는 surface다.
- public operator visibility flow는 `thread list -> thread show -> handoff show -> workspace show -> agent status -> agent logs` 순서로 닫는다.

## Success criteria for this contract lock
- README/help/PRD/roadmap/tests가 같은 `maia init` public onboarding story를 말한다.
- `maia init`은 readiness, next step, conversation-ready success condition을 truthfully 설명한다.
- advanced/manual operator flow는 public이지만 canonical first-run story보다 2차적 surface로 남는다.
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
