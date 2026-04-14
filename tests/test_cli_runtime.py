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
    if tokens and tokens[0] in {"created", "updated"}:
        tokens = tokens[1:]
    return dict(token.split("=", 1) for token in tokens)


def create_agent(home: Path, name: str = "demo") -> str:
    result = run_module(home, "agent", "new", name)

    assert result.returncode == 0
    assert result.stderr == ""
    return parse_fields(result.stdout.strip())["agent_id"]


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


def test_agent_tune_updates_persona_for_existing_agent(tmp_path: Path) -> None:
    created = run_module(tmp_path, "agent", "new", "demo")
    agent_id = parse_fields(created.stdout.strip())["agent_id"]

    result = run_module(tmp_path, "agent", "tune", agent_id, "--persona", "analyst")
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.strip() == f"updated agent_id={agent_id} persona=analyst"
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=stopped persona=analyst"
    )


def test_agent_tune_updates_persona_from_file_for_existing_agent(tmp_path: Path) -> None:
    created = run_module(tmp_path, "agent", "new", "demo")
    agent_id = parse_fields(created.stdout.strip())["agent_id"]
    persona_path = tmp_path / "persona.txt"
    persona_path.write_text("research analyst", encoding="utf-8")

    result = run_module(
        tmp_path, "agent", "tune", agent_id, "--persona-file", str(persona_path)
    )
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert result.returncode == 0
    assert result.stderr == ""
    assert (
        result.stdout.strip()
        == f"updated agent_id={agent_id} persona=research analyst"
    )
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=stopped persona=research analyst"
    )


def test_agent_tune_persona_file_preserves_trailing_newline(tmp_path: Path) -> None:
    created = run_module(tmp_path, "agent", "new", "demo")
    agent_id = parse_fields(created.stdout.strip())["agent_id"]
    persona_path = tmp_path / "persona.txt"
    persona_path.write_text("night-shift\n", encoding="utf-8")

    result = run_module(
        tmp_path, "agent", "tune", agent_id, "--persona-file", str(persona_path)
    )
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == f"updated agent_id={agent_id} persona=night-shift\n\n"
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout
        == f"agent_id={agent_id} name=demo status=stopped persona=night-shift\n\n"
    )

    registry_path = tmp_path / ".maia" / "registry.json"
    assert json.loads(registry_path.read_text(encoding="utf-8")) == {
        "agents": [
            {
                "agent_id": agent_id,
                "name": "demo",
                "status": "stopped",
                "persona": "night-shift\n",
            }
        ]
    }


def test_agent_tune_preserves_name_and_status(tmp_path: Path) -> None:
    created = run_module(tmp_path, "agent", "new", "demo")
    agent_id = parse_fields(created.stdout.strip())["agent_id"]

    tuned = run_module(tmp_path, "agent", "tune", agent_id, "--persona", "operator")

    assert tuned.returncode == 0

    registry_path = tmp_path / ".maia" / "registry.json"
    assert json.loads(registry_path.read_text(encoding="utf-8")) == {
        "agents": [
            {
                "agent_id": agent_id,
                "name": "demo",
                "status": "stopped",
                "persona": "operator",
            }
        ]
    }

    listed = run_module(tmp_path, "agent", "list")
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip() == f"agent_id={agent_id} name=demo status=stopped"


def test_agent_tune_missing_agent_error(tmp_path: Path) -> None:
    result = run_module(tmp_path, "agent", "tune", "missing", "--persona", "analyst")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: Agent with id 'missing' not found"


def test_agent_tune_missing_persona_file_error(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)
    persona_path = tmp_path / "missing.txt"

    result = run_module(
        tmp_path, "agent", "tune", agent_id, "--persona-file", str(persona_path)
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        result.stderr.strip()
        == f"error: Persona file {str(persona_path)!r} not found"
    )


def test_agent_tune_empty_persona_clears_value(tmp_path: Path) -> None:
    created = run_module(tmp_path, "agent", "new", "demo")
    agent_id = parse_fields(created.stdout.strip())["agent_id"]

    first_tune = run_module(tmp_path, "agent", "tune", agent_id, "--persona", "analyst")
    second_tune = run_module(tmp_path, "agent", "tune", agent_id, "--persona", "")
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert first_tune.returncode == 0
    assert second_tune.returncode == 0
    assert second_tune.stderr == ""
    assert second_tune.stdout.strip() == f"updated agent_id={agent_id} persona="
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=stopped persona="
    )


def test_agent_start_sets_running(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    started = run_module(tmp_path, "agent", "start", agent_id)
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert started.returncode == 0
    assert started.stderr == ""
    assert started.stdout.strip() == f"updated agent_id={agent_id} status=running"
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=running persona="
    )


def test_agent_stop_sets_stopped_after_start(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    started = run_module(tmp_path, "agent", "start", agent_id)
    stopped = run_module(tmp_path, "agent", "stop", agent_id)
    listed = run_module(tmp_path, "agent", "list")

    assert started.returncode == 0
    assert stopped.returncode == 0
    assert stopped.stderr == ""
    assert stopped.stdout.strip() == f"updated agent_id={agent_id} status=stopped"
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip() == f"agent_id={agent_id} name=demo status=stopped"


def test_agent_archive_sets_archived(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    archived = run_module(tmp_path, "agent", "archive", agent_id)
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert archived.returncode == 0
    assert archived.stderr == ""
    assert archived.stdout.strip() == f"updated agent_id={agent_id} status=archived"
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=archived persona="
    )


def test_agent_purge_archived_agent_succeeds(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    archived = run_module(tmp_path, "agent", "archive", agent_id)
    purged = run_module(tmp_path, "agent", "purge", agent_id)
    listed = run_module(tmp_path, "agent", "list")
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert archived.returncode == 0
    assert purged.returncode == 0
    assert purged.stderr == ""
    assert purged.stdout.strip() == f"purged agent_id={agent_id}"
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip() == ""
    assert status.returncode == 1
    assert status.stdout == ""
    assert status.stderr.strip() == f"error: Agent with id {agent_id!r} not found"

    registry_path = tmp_path / ".maia" / "registry.json"
    assert json.loads(registry_path.read_text(encoding="utf-8")) == {"agents": []}


def test_agent_purge_running_agent_rejected(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    started = run_module(tmp_path, "agent", "start", agent_id)
    purged = run_module(tmp_path, "agent", "purge", agent_id)
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert started.returncode == 0
    assert purged.returncode == 1
    assert purged.stdout == ""
    assert (
        purged.stderr.strip()
        == f"error: Agent with id {agent_id!r} is not archived (status=running)"
    )
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=running persona="
    )


def test_agent_purge_stopped_agent_rejected(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    purged = run_module(tmp_path, "agent", "purge", agent_id)
    listed = run_module(tmp_path, "agent", "list")

    assert purged.returncode == 1
    assert purged.stdout == ""
    assert (
        purged.stderr.strip()
        == f"error: Agent with id {agent_id!r} is not archived (status=stopped)"
    )
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip() == f"agent_id={agent_id} name=demo status=stopped"


def test_agent_purge_missing_agent_error(tmp_path: Path) -> None:
    result = run_module(tmp_path, "agent", "purge", "missing")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: Agent with id 'missing' not found"


def test_agent_purge_preserves_remaining_list_order(tmp_path: Path) -> None:
    alpha_id = create_agent(tmp_path, "alpha")
    beta_id = create_agent(tmp_path, "beta")
    gamma_id = create_agent(tmp_path, "gamma")

    archived = run_module(tmp_path, "agent", "archive", beta_id)
    purged = run_module(tmp_path, "agent", "purge", beta_id)
    listed = run_module(tmp_path, "agent", "list")

    assert archived.returncode == 0
    assert purged.returncode == 0
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip().splitlines() == [
        f"agent_id={alpha_id} name=alpha status=stopped",
        f"agent_id={gamma_id} name=gamma status=stopped",
    ]


def test_agent_restore_sets_stopped_after_archive(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path)

    archived = run_module(tmp_path, "agent", "archive", agent_id)
    restored = run_module(tmp_path, "agent", "restore", agent_id)
    status = run_module(tmp_path, "agent", "status", agent_id)

    assert archived.returncode == 0
    assert restored.returncode == 0
    assert restored.stderr == ""
    assert restored.stdout.strip() == f"updated agent_id={agent_id} status=stopped"
    assert status.returncode == 0
    assert status.stderr == ""
    assert (
        status.stdout.strip()
        == f"agent_id={agent_id} name=demo status=stopped persona="
    )


def test_agent_start_missing_agent_error(tmp_path: Path) -> None:
    result = run_module(tmp_path, "agent", "start", "missing")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "error: Agent with id 'missing' not found"
