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


def test_top_level_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia" in captured.out
    assert "agent" in captured.out


def test_agent_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia agent" in captured.out
    assert "export" in captured.out
    assert "import" in captured.out
    assert "new" in captured.out
    assert "purge" in captured.out


def test_agent_new_placeholder(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["agent", "new", "demo"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Not implemented yet: agent new"


def test_agent_purge_placeholder_contract(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["agent", "purge", "demo1234"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Not implemented yet: agent purge"


def test_agent_export_placeholder_contract(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    export_path = tmp_path / "registry.json"

    assert main(["agent", "export", str(export_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Not implemented yet: agent export"


def test_agent_import_placeholder_contract(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    import_path = tmp_path / "registry.json"

    assert main(["agent", "import", str(import_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Not implemented yet: agent import"


def test_agent_tune_placeholder_contract_with_persona_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    persona_path = tmp_path / "persona.txt"

    assert main(["agent", "tune", "demo1234", "--persona-file", str(persona_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Not implemented yet: agent tune"


def test_agent_tune_parser_rejects_both_persona_sources(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    persona_path = tmp_path / "persona.txt"

    with pytest.raises(SystemExit) as exc_info:
        main(
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


def test_agent_tune_parser_rejects_missing_persona_source(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "tune", "demo1234"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "--persona" in captured.err
    assert "--persona-file" in captured.err
    assert "required" in captured.err


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
