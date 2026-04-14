from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


def run_module(home: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_ROOT)
        if not existing_pythonpath
        else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.run(
        [sys.executable, "-m", "maia", *argv],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def parse_fields(line: str) -> dict[str, str]:
    tokens = line.split()
    if tokens and tokens[0] == "created":
        tokens = tokens[1:]
    return dict(token.split("=", 1) for token in tokens)


def test_agent_new_persists_record(tmp_path: Path) -> None:
    result = run_module(tmp_path, "agent", "new", "demo")

    assert result.returncode == 0
    assert result.stderr == ""

    fields = parse_fields(result.stdout.strip())
    assert fields["name"] == "demo"
    assert fields["status"] == "stopped"

    registry_path = tmp_path / ".maia" / "registry.json"
    assert registry_path.exists()
    assert json.loads(registry_path.read_text(encoding="utf-8")) == {
        "agents": [
            {
                "agent_id": fields["agent_id"],
                "name": "demo",
                "status": "stopped",
                "persona": "",
            }
        ]
    }


def test_agent_new_duplicate_name_error(tmp_path: Path) -> None:
    first = run_module(tmp_path, "agent", "new", "demo")
    second = run_module(tmp_path, "agent", "new", "demo")

    assert first.returncode == 0
    assert second.returncode == 1
    assert second.stdout == ""
    assert second.stderr.strip() == "error: Agent with name 'demo' already exists"


def test_agent_list_preserves_storage_order(tmp_path: Path) -> None:
    first = run_module(tmp_path, "agent", "new", "alpha")
    second = run_module(tmp_path, "agent", "new", "beta")

    first_id = parse_fields(first.stdout.strip())["agent_id"]
    second_id = parse_fields(second.stdout.strip())["agent_id"]

    result = run_module(tmp_path, "agent", "list")

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.strip().splitlines() == [
        f"agent_id={first_id} name=alpha status=stopped",
        f"agent_id={second_id} name=beta status=stopped",
    ]


def test_agent_status_existing_agent(tmp_path: Path) -> None:
    created = run_module(tmp_path, "agent", "new", "demo")
    agent_id = parse_fields(created.stdout.strip())["agent_id"]

    result = run_module(tmp_path, "agent", "status", agent_id)

    assert result.returncode == 0
    assert result.stderr == ""
    assert (
        result.stdout.strip()
        == f"agent_id={agent_id} name=demo status=stopped persona="
    )


def test_agent_status_missing_agent_error(tmp_path: Path) -> None:
    result = run_module(tmp_path, "agent", "status", "missing")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: Agent with id 'missing' not found"
