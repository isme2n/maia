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
    assert "new" in captured.out
    assert "purge" in captured.out


def test_agent_new_placeholder(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["agent", "new", "demo"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "Not implemented yet: agent new"


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
