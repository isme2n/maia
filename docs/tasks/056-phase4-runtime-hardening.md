# Task 056 - phase4 runtime hardening

## Goal
Phase 4 구현을 reviewer 기준으로 하드닝하고 문구/행동 불일치를 없앤다.

## Non-goals
- broker 구현
- compose/cluster 기능 추가

## Allowed files
- Phase 4에서 바뀐 파일 일체
- `README.md` (필요 시 최소 수정)

## Acceptance criteria
- [ ] blocking review issue가 없어진다.
- [ ] runtime command help/output이 실제 동작과 맞는다.
- [ ] fake docker 기반 end-to-end 흐름이 안정적으로 녹색이다.
- [ ] `bash scripts/verify.sh` 통과.

## Required validation commands
- `bash scripts/verify.sh`

## Forbidden changes
- unrelated cleanup 끼워넣기
- phase 5 범위 선행
