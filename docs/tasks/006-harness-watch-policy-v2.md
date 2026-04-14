# Task 006 - Harness watch policy v2

## Goal
- Codex 개발 하네스의 백그라운드 감시 정책을 역할별(worker/reviewer)로 분리하고,
  문서에 적힌 예시 문자열 때문에 생기는 오탐을 구조적으로 줄인다.
- reviewer 판정은 watch pattern에 기대지 않고, 고정 출력 형식 파싱으로 다룰 수 있게 만든다.

## Non-goals
- Maia 제품 기능 변경
- Docker/Compose/DB/queue 구현
- Hermes 본체의 process watch 동작 변경
- planner/worker/reviewer 전체 오케스트레이터 구현

## Allowed files
- `AGENTS.md`
- `docs/harness-engineering.md`
- `docs/harness-runbook.md`
- `docs/tasks/006-harness-watch-policy-v2.md`
- `scripts/codex-worker.sh`
- `scripts/codex-review.sh`
- `scripts/codex-watch-patterns.sh`
- `scripts/codex-parse-review.py`
- `tests/test_harness_watch_policy.py`
- `README.md`

## Acceptance criteria
- [ ] 문서에 watch policy v2 원칙이 있다.
- [ ] worker와 reviewer의 감시 기준이 분리되어 설명된다.
- [ ] 문서에는 literal watch 예시 단어 나열 대신 "허용되는 신호 종류" 중심 규칙이 있다.
- [ ] `scripts/codex-watch-patterns.sh worker` 는 worker용 watch pattern 목록을 출력한다.
- [ ] `scripts/codex-watch-patterns.sh reviewer` 는 reviewer용 watch pattern 목록을 출력한다.
- [ ] worker 패턴은 리뷰 verdict/섹션 이름 같은 문자열을 포함하지 않는다.
- [ ] reviewer 스크립트 프롬프트는 `REVIEW_RESULT_START` / `REVIEW_RESULT_END` 블록 안에 고정 형식을 출력하라고 요구한다.
- [ ] `scripts/codex-parse-review.py` 는 reviewer 출력에서 verdict를 추출할 수 있다.
- [ ] approve / request_changes 두 경우 모두 파싱 테스트가 있다.
- [ ] marker가 없거나 verdict가 없으면 명확한 non-zero exit과 에러 메시지를 반환한다.
- [ ] `bash scripts/verify.sh` 와 `python3 -m pytest -q` 가 통과한다.

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `bash scripts/codex-watch-patterns.sh worker`
- `bash scripts/codex-watch-patterns.sh reviewer`
- `python3 scripts/codex-parse-review.py <sample-review-output-file>`

## Forbidden changes
- src/maia 제품 코드 수정
- 기존 task 005 범위 코드 변경
- watch 패턴을 문서 예시 문자열 기준으로 다시 되돌리기

## Notes
- 핵심 원칙은 "watch는 런타임 실패 신호만", "review 판정은 구조화된 결과 파싱으로" 이다.
- shell 스크립트는 POSIX sh보다 bash 전용으로 유지해도 된다.
- parser는 Python 표준 라이브러리만 사용한다.
