# Task 142A — Part 4 UX contract matrix and drift-check baseline (doctor 포함)

## Goal
Part 4 UX closeout의 public wording 계약을 matrix + drift-check 형태로 고정한다.

## Roadmap position
- Execution task for Part 4.

## Non-goals
- README/help/test 실제 문구 수정(142B/142C에서 처리)
- 런타임 동작 변경

## Allowed files
- `docs/tasks/142a-ux-contract-matrix-and-drift-check.md`
- `docs/contracts/part4-ux-public-contract-matrix.md`
- `docs/contracts/part4-ux-drift-checks.md`

## Required outputs
1) Contract matrix with fields:
   - surface/command
   - status (`primary`, `secondary`, `legacy-history`)
   - canonical wording
   - assert locations (README/help/tests/code)
2) Drift-check command doc containing:
   - text checks for first-run/doctor/setup/agent core flow and Part 3 portable-state wording
   - help checks (`python3 -m maia --help`, `python3 -m maia doctor --help`, `python3 -m maia setup --help`, `python3 -m maia agent --help`)
   - test checks (`pytest` targets)

## Acceptance criteria
- matrix가 `doctor -> setup -> agent new -> agent setup -> agent start`를 Part 4 primary UX로 고정한다.
- `doctor`를 infra-only UX surface로 명시한다.
- `inspect`/visibility surfaces는 primary bootstrap이 아닌 support/secondary로 유지한다.
- drift-check 문서가 실행 가능하고 과도한 토큰-매칭으로 false-pass 나지 않도록 구성된다.

## Validation
- `python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- src 코드/테스트 수정 금지
