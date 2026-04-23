from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCH_SCRIPT = REPO_ROOT / "scripts" / "codex-watch-patterns.sh"
PARSE_SCRIPT = REPO_ROOT / "scripts" / "codex-parse-review.py"
REVIEW_SCRIPT = REPO_ROOT / "scripts" / "codex-review.sh"


def run_command(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_worker_watch_patterns_are_role_specific() -> None:
    result = run_command("bash", str(WATCH_SCRIPT), "worker")

    assert result.returncode == 0
    assert result.stderr == ""

    patterns = result.stdout.strip().splitlines()
    assert patterns == [
        r"^Traceback \(most recent call last\):$",
        r"^FAILED .*$",
        r"^AssertionError(:|$)",
    ]
    assert not any("request_changes" in pattern for pattern in patterns)
    assert not any("blocking_issues" in pattern for pattern in patterns)


def test_reviewer_watch_patterns_only_watch_runtime_failures() -> None:
    result = run_command("bash", str(WATCH_SCRIPT), "reviewer")

    assert result.returncode == 0
    assert result.stderr == ""

    patterns = result.stdout.strip().splitlines()
    assert patterns == [
        r"^Traceback \(most recent call last\):$",
        r"^AssertionError(:|$)",
    ]
    assert not any("approve" in pattern for pattern in patterns)
    assert not any("request_changes" in pattern for pattern in patterns)


def test_watch_pattern_script_rejects_unknown_role() -> None:
    result = run_command("bash", str(WATCH_SCRIPT), "planner")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: unknown role 'planner' (expected worker or reviewer)"


def test_parse_review_extracts_approve_verdict(tmp_path: Path) -> None:
    review_output = tmp_path / "review-approve.txt"
    review_output.write_text(
        "intro\n"
        "REVIEW_RESULT_START\n"
        "verdict: approve\n"
        "blocking_issues:\n"
        "- none\n"
        "non_blocking_suggestions:\n"
        "- add one more test later\n"
        "touched_risks:\n"
        "- none\n"
        "summary: looks good\n"
        "REVIEW_RESULT_END\n",
        encoding="utf-8",
    )

    result = run_command("python3", str(PARSE_SCRIPT), str(review_output))

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"verdict": "approve"}


def test_parse_review_extracts_request_changes_verdict(tmp_path: Path) -> None:
    review_output = tmp_path / "review-request-changes.txt"
    review_output.write_text(
        "REVIEW_RESULT_START\n"
        "verdict: request_changes\n"
        "blocking_issues:\n"
        "- bug\n"
        "non_blocking_suggestions:\n"
        "- note\n"
        "touched_risks:\n"
        "- regression\n"
        "summary: fix needed\n"
        "REVIEW_RESULT_END\n",
        encoding="utf-8",
    )

    result = run_command("python3", str(PARSE_SCRIPT), str(review_output))

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"verdict": "request_changes"}


def test_parse_review_missing_markers_returns_error(tmp_path: Path) -> None:
    review_output = tmp_path / "review-missing-markers.txt"
    review_output.write_text("verdict: approve\n", encoding="utf-8")

    result = run_command("python3", str(PARSE_SCRIPT), str(review_output))

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: missing review result markers"


def test_parse_review_missing_verdict_returns_error(tmp_path: Path) -> None:
    review_output = tmp_path / "review-missing-verdict.txt"
    review_output.write_text(
        "REVIEW_RESULT_START\n"
        "blocking_issues:\n"
        "- none\n"
        "REVIEW_RESULT_END\n",
        encoding="utf-8",
    )

    result = run_command("python3", str(PARSE_SCRIPT), str(review_output))

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: missing review verdict"


def test_parse_review_prefers_last_valid_result_block(tmp_path: Path) -> None:
    review_output = tmp_path / "review-noisy-prefix.txt"
    review_output.write_text(
        "The instructions mentioned REVIEW_RESULT_END before the actual output.\n"
        "REVIEW_RESULT_START\n"
        "blocking_issues:\n"
        "- placeholder\n"
        "REVIEW_RESULT_END\n"
        "more commentary\n"
        "REVIEW_RESULT_START\n"
        "verdict: request_changes\n"
        "blocking_issues:\n"
        "- real issue\n"
        "non_blocking_suggestions:\n"
        "- none\n"
        "touched_risks:\n"
        "- parser drift\n"
        "summary: use this block\n"
        "REVIEW_RESULT_END\n",
        encoding="utf-8",
    )

    result = run_command("python3", str(PARSE_SCRIPT), str(review_output))

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"verdict": "request_changes"}


def test_codex_review_prompt_requires_result_markers() -> None:
    content = REVIEW_SCRIPT.read_text(encoding="utf-8")

    assert "REVIEW_RESULT_START" in content
    assert "REVIEW_RESULT_END" in content
    assert "Do not omit the markers." in content
