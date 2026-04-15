# Task 061 - phase5 host-independent final hardening

## Goal
Phase 5 host-independent 범위의 최종 reviewer feedback을 반영하고 문구/행동 불일치를 없앤다.

## Non-goals
- host package install
- Phase 6 설계 선행

## Allowed files
- Phase 5에서 변경된 파일 일체
- `README.md` (필요 시 최소 수정)

## Acceptance criteria
- [ ] blocking review issue가 없다.
- [ ] doctor/status/runtime hygiene 동작과 테스트가 일치한다.
- [ ] `bash scripts/verify.sh` 통과.

## Required validation commands
- `bash scripts/verify.sh`

## Forbidden changes
- unrelated cleanup 끼워넣기
