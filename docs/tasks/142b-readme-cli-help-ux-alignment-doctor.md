# Task 142B — README/CLI help UX alignment (doctor 포함)

## Goal
Part 4 UX closeout 기준으로 README와 CLI help를 일관되게 정렬한다.

## Roadmap position
- Execution task for Part 4.

## Non-goals
- 런타임 로직 변경
- Part 5 문서 구조 분리/패키징

## Allowed files
- `docs/tasks/142b-readme-cli-help-ux-alignment-doctor.md`
- `README.md`
- `src/maia/cli_parser.py`

## Required changes
1) README:
   - first-run UX를 `doctor -> setup -> agent new -> agent setup -> agent start` 중심으로 간결하게 표현
   - `doctor`를 infra-only 판단/다음 단계 안내 surface로 명확히 표현
   - portable-state/visibility는 support surface로 유지(bootstrap 주 흐름과 분리)
2) CLI help constants/examples:
   - top-level/help epilog에서 primary UX 흐름과 `doctor` 역할을 명시
   - `doctor --help`가 infra-only 범위를 분명히 드러내도록 wording 정렬
   - `inspect`/visibility surfaces가 primary bootstrap으로 오인되지 않게 유지

## Acceptance criteria
- README와 `maia --help`/`maia doctor --help`가 같은 Part 4 UX contract를 설명한다.
- `doctor` 역할이 명확하고 과장되지 않는다.
- 문구가 validated scope를 넘어서지 않는다.

## Validation
- `python3 -m maia --help`
- `python3 -m maia doctor --help`
- `python3 -m maia setup --help`
- `python3 -m maia agent --help`
- `python3 -m pytest -q tests/test_cli.py`
