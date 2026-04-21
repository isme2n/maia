# Task 142 — Part 4 UX closeout (doctor 포함)

## Goal
Part 4(UX Closeout)을 contract-first 방식으로 닫기 위한 실행 태스크를 분리/고정한다.

## Roadmap position
- Execution task for Part 4.

## Non-goals
- Part 5 오픈소스 패키징 작업
- 런타임/브로커 기능 추가

## Allowed files
- `docs/tasks/142-part4-ux-closeout.md`
- `docs/tasks/142a-ux-contract-matrix-and-drift-check.md`
- `docs/tasks/142b-readme-cli-help-ux-alignment-doctor.md`
- `docs/tasks/142c-cli-tests-ux-contract-lock.md`
- `docs/tasks/142d-part4-roadmap-closeout-and-verify.md`

## Required outputs
1) 142A: Part 4 public UX contract matrix + drift-check baseline 문서
2) 142B: README/CLI help UX 정렬(`doctor` 포함)
3) 142C: `tests/test_cli.py` 계약 고정
4) 142D: roadmap closeout + 검증/리뷰 기록

## Acceptance criteria
- Part 4 scope가 docs/help/tests/roadmap으로 명확히 분해된다.
- 각 자식 태스크가 allowed files/validation을 독립적으로 가진다.
- `doctor`가 Part 4 UX closeout 대상에 명시된다.

## Validation
- 문서 리뷰(파일 존재 + 섹션 유효성)
