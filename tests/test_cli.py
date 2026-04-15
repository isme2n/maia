from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.cli import main
from maia.cli_parser import build_parser


def test_top_level_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia" in captured.out
    assert "agent" in captured.out
    assert "team" in captured.out
    assert "doctor" in captured.out
    assert "send" in captured.out
    assert "inbox" in captured.out
    assert "thread" in captured.out
    assert "reply" in captured.out
    assert "Export Maia portable state" in captured.out
    assert "Import Maia portable state safely" in captured.out
    assert "Inspect an importable Maia snapshot" in captured.out


def test_agent_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia agent" in captured.out
    assert "new" in captured.out
    assert "purge" in captured.out
    assert "export" not in captured.out
    assert "import" not in captured.out


def test_team_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["team", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia team" in captured.out
    assert "show" in captured.out
    assert "update" in captured.out
    assert "agent" not in captured.out


def test_build_parser_send_shape() -> None:
    args = build_parser().parse_args(
        ["send", "planner", "reviewer", "--body", "hello", "--topic", "phase-3"]
    )

    assert args.resource == "send"
    assert args.from_agent == "planner"
    assert args.to_agent == "reviewer"
    assert args.body == "hello"
    assert args.topic == "phase-3"
    assert args.thread_id is None
    assert args.kind == "request"


def test_build_parser_reply_shape() -> None:
    args = build_parser().parse_args(
        ["reply", "msg1234", "--from-agent", "reviewer", "--body", "done"]
    )

    assert args.resource == "reply"
    assert args.message_id == "msg1234"
    assert args.from_agent == "reviewer"
    assert args.body == "done"
    assert args.kind == "answer"


def test_build_parser_team_update_shape() -> None:
    args = build_parser().parse_args(
        ["team", "update", "--name", "research-lab", "--tags", "research,ops"]
    )

    assert args.resource == "team"
    assert args.team_command == "update"
    assert args.name == "research-lab"
    assert args.tags == "research,ops"
    assert args.default_agent is None


def test_doctor_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["doctor", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Check local Phase 4 runtime prerequisites" in captured.out
    assert "Examples:" in captured.out
    assert "maia doctor" in captured.out


def test_import_help_describes_safety_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["import", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Read a .maia bundle, manifest.json" in captured.out
    assert "raw registry" in captured.out
    assert "snapshot path" in captured.out
    assert "Show the import preview and risk summary" in captured.out
    assert "local Maia state" in captured.out
    assert "Show full added/removed/changed preview lists" in captured.out
    assert "without" in captured.out
    assert "truncation" in captured.out
    assert "Skip overwrite confirmation for destructive imports" in captured.out
    assert "Examples:" in captured.out
    assert "maia import backups/team.maia --preview" in captured.out
    assert "maia import backups/team.maia --preview --verbose-preview" in captured.out
    assert "maia import backups/team.maia --yes" in captured.out


def test_export_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["export", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Write a Maia bundle (.maia) or raw registry snapshot" in captured.out
    assert "path" in captured.out
    assert "Examples:" in captured.out
    assert "maia export" in captured.out
    assert "maia export backups/team.maia" in captured.out
    assert "maia export backups/team.maia --label prod --description 'Nightly snapshot'" in captured.out


def test_team_update_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["team", "update", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Set the team display name" in captured.out
    assert "Comma-separated team tags" in captured.out
    assert "Clear the stored default agent id" in captured.out
    assert "Examples:" in captured.out
    assert "maia team update --name research-lab --tags research,ops" in captured.out


def test_team_update_parser_rejects_conflicting_name_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["team", "update", "--name", "research-lab", "--clear-name"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--clear-name" in captured.err
    assert "not allowed" in captured.err


def test_agent_tune_help_includes_profile_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "tune", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--persona" in captured.out
    assert "--role" in captured.out
    assert "--model" in captured.out
    assert "--tags" in captured.out
    assert "--clear-role" in captured.out
    assert "--clear-model" in captured.out
    assert "--clear-tags" in captured.out
    assert "--runtime-image" in captured.out
    assert "--runtime-workspace" in captured.out
    assert "--runtime-command" in captured.out
    assert "--runtime-env" in captured.out
    assert "--clear-runtime" in captured.out


def test_agent_tune_parser_rejects_both_persona_sources(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    persona_path = tmp_path / "persona.txt"

    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(
            [
                "agent",
                "tune",
                "demo1234",
                "--persona",
                "analyst",
                "--persona-file",
                str(persona_path),
            ]
        )

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--persona" in captured.err
    assert "--persona-file" in captured.err
    assert "not allowed" in captured.err


def test_agent_tune_parser_rejects_conflicting_role_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["agent", "tune", "demo1234", "--role", "research", "--clear-role"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--clear-role" in captured.err
    assert "not allowed" in captured.err


def test_build_parser_runtime_tune_shape() -> None:
    args = build_parser().parse_args(
        [
            "agent",
            "tune",
            "demo1234",
            "--runtime-image",
            "ghcr.io/example/reviewer:latest",
            "--runtime-workspace",
            "/workspace/reviewer",
            "--runtime-command",
            "python",
            "--runtime-command=-m",
            "--runtime-command",
            "reviewer",
            "--runtime-env",
            "MAIA_ENV=test",
        ]
    )

    assert args.agent_command == "tune"
    assert args.runtime_image == "ghcr.io/example/reviewer:latest"
    assert args.runtime_workspace == "/workspace/reviewer"
    assert args.runtime_command == ["python", "-m", "reviewer"]
    assert args.runtime_env == ["MAIA_ENV=test"]
    assert args.clear_runtime is False


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--help"], "usage: maia"),
        (["agent", "--help"], "usage: maia agent"),
    ],
)
def test_module_entrypoint_help(argv: list[str], expected: str) -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_ROOT)
        if not existing_pythonpath
        else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    )

    result = subprocess.run(
        [sys.executable, "-m", "maia", *argv],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert expected in result.stdout
