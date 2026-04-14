# Maia Codex Harness v1

## Goal
- Maia 개발용 Codex 작업 하네스를 최소 형태로 고정한다.

## Non-goals
- Maia 런타임 멀티에이전트 기능 구현
- Docker/Compose/DB/Queue 구현
- eval 플랫폼 구축

## Allowed files
- `AGENTS.md`
- `docs/harness-*.md`
- `docs/tasks/*.md`
- `docs/reviews/*.md`
- `scripts/codex-*.sh`
- `scripts/verify.sh`

## Acceptance criteria
- [ ] planner / worker / reviewer 역할 정의가 문서에 있다.
- [ ] planner 사용 조건이 문서에 있다.
- [ ] worker -> verify -> reviewer -> fix loop 흐름이 문서에 있다.
- [ ] 실제 실행 가능한 shell 스크립트가 있다.
- [ ] reviewer 승인 없이는 완료가 아니라는 규칙이 있다.
- [ ] fix loop 최대 3회 규칙이 있다.

## Required validation commands
- `bash scripts/verify.sh`

## Forbidden changes
- Maia 제품 코드 구현 시작
- Docker 설치 시도
- DB/queue 선택 확정

## Notes
- 이 task는 Maia를 만드는 개발 공정만 다룬다.
- 제품 기능이 아니라 Codex 운용 방식 정의가 목적이다.
