# Maia Codex Harness Runbook

이 문서는 Maia를 개발할 때 Codex를 어떻게 굴릴지에 대한 실전 운영 절차다.

## 역할
- planner: 작업을 작은 task spec으로 자른다.
- worker: spec대로 구현한다.
- reviewer: diff/spec/검증 결과를 기준으로 승인 또는 수정 요청을 한다.

## 기본 규칙
- planner는 큰 작업 또는 애매한 작업일 때만 쓴다.
- worker는 항상 spec이 있어야 시작한다.
- reviewer 승인 없이는 완료로 보지 않는다.
- verify 실패 상태로 다음 단계로 넘어가지 않는다.
- fix loop는 최대 3회까지만 반복한다.

## 표준 흐름
1. 큰 요구를 받으면 planner가 작은 spec으로 만든다.
2. spec을 `docs/tasks/<slug>.md`에 저장한다.
3. worker가 spec 범위 안에서만 구현한다.
4. `scripts/verify.sh`를 실행한다.
5. reviewer가 현재 diff를 리뷰한다.
6. blocking issue가 있으면 worker가 수정한다.
7. verify와 review를 다시 돌린다.
8. reviewer 승인 시에만 다음 task로 넘어간다.

## 표준 명령
- planner 초안 생성: `scripts/codex-plan.sh <brief>`
- worker 실행: `scripts/codex-worker.sh docs/tasks/<slug>.md`
- verify 실행: `scripts/verify.sh`
- reviewer 실행: `scripts/codex-review.sh docs/tasks/<slug>.md`

## 백그라운드 감시 규칙
- watch pattern은 "실패했을 때만 거의 나타나는 런타임 신호"만 쓴다.
- worker와 reviewer의 watch는 분리한다.
- worker watch의 목적:
  - 구현/검증 중 uncaught stacktrace, pytest 실패, assertion 실패를 빨리 감지하는 것
- reviewer watch의 목적:
  - reviewer 실행 자체가 깨졌는지(스택트레이스, assertion 실패)만 감지하는 것
- reviewer의 `approve` / `request_changes` / 섹션 이름은 watch로 보지 않는다.
- `exited 1` 같은 문자열은 watch로 쓰지 않는다.
  - 이유: Codex 로그는 내부 probe 명령의 `exited 1 in 0ms:` 같은 줄도 그대로 보여줄 수 있어서 오탐이 난다.
- 피해야 할 패턴:
  - 프롬프트나 문서에 적어둔 예시 단어
  - 리뷰 verdict 값이나 리뷰 섹션 이름
  - 일반 예외명/클래스명/도메인 용어
- 이유:
  - Codex가 AGENTS.md, runbook, 프롬프트를 읽거나 인용하면 그 단어가 그대로 출력되어 오탐이 난다.
  - 리뷰 verdict/항목명은 watch가 아니라 결과 본문 파싱으로 처리해야 한다.
- 운영 방식:
  - worker 패턴 목록은 `scripts/codex-watch-patterns.sh worker`
  - reviewer 패턴 목록은 `scripts/codex-watch-patterns.sh reviewer`
  - reviewer 결과 판정은 `python3 scripts/codex-parse-review.py <review-output-file>`

## 리뷰 기준
- spec 불일치가 없는가?
- 범위 초과 변경이 없는가?
- 검증 명령이 실제로 통과했는가?
- 회귀 위험이 큰가?
- 테스트가 너무 느슨하지 않은가?

## 언제 planner를 쓰나
- 상태 모델 변경
- CLI 계약 변경
- DB 스키마 변경
- 여러 파일/레이어를 건드리는 작업
- 요구사항이 아직 모호한 작업

## 언제 planner 없이 가나
- 단일 파일의 작은 수정
- 명확한 버그 수정
- 리뷰 코멘트 반영 같은 좁은 범위 작업

## 완료 정의
- task spec 충족
- verify 통과
- reviewer approve
