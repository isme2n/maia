from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia import cli as cli_module
from maia.app_state import (
    get_collaboration_path,
    get_default_export_path,
    get_registry_path,
    get_runtime_state_path,
    get_team_metadata_path,
)
from maia.team_metadata import TeamMetadata, load_team_metadata, save_team_metadata


def run_module(
    home: Path,
    *argv: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
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
        input=input_text,
    )


def parse_fields(line: str) -> dict[str, str]:
    tokens = line.split()
    if tokens[:2] == ["restored", "bundle"]:
        tokens = tokens[2:]
    elif tokens and tokens[0] in {
        "created",
        "updated",
        "exported",
        "imported",
        "inspected",
        "sent",
        "inbox",
        "thread",
        "replied",
        "preview",
        "risk",
        "added",
        "removed",
        "changed",
        "confirm",
        "manifest",
        "bundle",
        "provenance",
        "portable",
        "runtime",
        "description",
        "team",
        "agents",
        "profiles",
        "purged",
        "doctor",
        "logs",
        "workspace",
    }:
        tokens = tokens[1:]
    if tokens and tokens[0] == "registry":
        tokens = tokens[1:]
    return dict(token.split("=", 1) for token in tokens)


def create_agent(home: Path, name: str = "demo") -> str:
    result = run_module(home, "agent", "new", name)
    assert result.returncode == 0
    assert result.stderr == ""
    return parse_fields(result.stdout.strip())["agent_id"]


def load_registry(home: Path) -> dict[str, object]:
    return json.loads(get_registry_path({"HOME": str(home)}).read_text(encoding="utf-8"))


def load_runtime_state(home: Path) -> dict[str, object]:
    return json.loads(get_runtime_state_path({"HOME": str(home)}).read_text(encoding="utf-8"))


def load_collaboration(home: Path) -> dict[str, object]:
    return json.loads(get_collaboration_path({"HOME": str(home)}).read_text(encoding="utf-8"))


def write_registry(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_bundle_archive(path: Path) -> dict[str, object]:
    with ZipFile(path) as archive:
        return {
            name: json.loads(archive.read(name).decode("utf-8"))
            for name in archive.namelist()
        }


def line_map(stdout: str) -> dict[str, str]:
    lines = [line for line in stdout.strip().splitlines() if line]
    return {line.split()[0]: line for line in lines}


def _write_fake_docker(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import json, sys\n"
        "state_path = Path(__file__).with_name('fake-docker-state.json')\n"
        "if state_path.exists():\n"
        "    state = json.loads(state_path.read_text(encoding='utf-8'))\n"
        "else:\n"
        "    state = {'containers': {}, 'counter': 0}\n"
        "args = sys.argv[1:]\n"
        "def save():\n"
        "    state_path.write_text(json.dumps(state), encoding='utf-8')\n"
        "if args == ['--version']:\n"
        "    print('Docker version 27.0.0')\n"
        "    raise SystemExit(0)\n"
        "if args == ['compose', 'version']:\n"
        "    print('Docker Compose version v2.29.0')\n"
        "    raise SystemExit(0)\n"
        "if args == ['info']:\n"
        "    print('Server Version: 27.0.0')\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['run', '-d']:\n"
        "    state['counter'] += 1\n"
        "    handle = f\"runtime-{state['counter']:03d}\"\n"
        "    state['containers'][handle] = {'status': 'running', 'logs': ['line 1', 'line 2']}\n"
        "    save()\n"
        "    print(handle)\n"
        "    raise SystemExit(0)\n"
        "if args[:1] == ['stop']:\n"
        "    handle = args[1]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    state['containers'][handle]['status'] = 'exited'\n"
        "    save()\n"
        "    print(handle)\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['inspect', '--format']:\n"
        "    handle = args[3]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    print(state['containers'][handle]['status'])\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['logs', '--tail']:\n"
        "    handle = args[3]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    tail = int(args[2])\n"
        "    for line in state['containers'][handle]['logs'][-tail:]:\n"
        "        print(line)\n"
        "    raise SystemExit(0)\n"
        "print('unsupported command', file=sys.stderr)\n"
        "raise SystemExit(1)\n",
        encoding='utf-8',
    )
    path.chmod(0o755)


def _setup_v1_golden_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")

    planner_tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        planner_id,
        "--role",
        "planner",
        "--runtime-image",
        "ghcr.io/example/planner:latest",
        "--runtime-workspace",
        "/workspace/planner",
        "--runtime-command",
        "python",
        "--runtime-command=-m",
        "--runtime-command",
        "planner",
        "--runtime-env",
        "MAIA_ENV=test",
        "--runtime-env",
        "MAIA_ROLE=planner",
    )
    assert planner_tuned.returncode == 0
    assert parse_fields(planner_tuned.stdout.strip()) == {
        "agent_id": planner_id,
        "role": "planner",
        "runtime_image": "ghcr.io/example/planner:latest",
        "runtime_workspace": "/workspace/planner",
        "runtime_command": "python,-m,planner",
        "runtime_env": "MAIA_ENV,MAIA_ROLE",
    }

    reviewer_tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        reviewer_id,
        "--role",
        "reviewer",
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
        "--runtime-env",
        "MAIA_ROLE=reviewer",
    )
    assert reviewer_tuned.returncode == 0
    assert parse_fields(reviewer_tuned.stdout.strip()) == {
        "agent_id": reviewer_id,
        "role": "reviewer",
        "runtime_image": "ghcr.io/example/reviewer:latest",
        "runtime_workspace": "/workspace/reviewer",
        "runtime_command": "python,-m,reviewer",
        "runtime_env": "MAIA_ENV,MAIA_ROLE",
    }

    planner_started = run_module(tmp_path, "agent", "start", planner_id)
    assert planner_started.returncode == 0
    assert parse_fields(planner_started.stdout.strip()) == {
        "agent_id": planner_id,
        "status": "running",
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
    }

    reviewer_started = run_module(tmp_path, "agent", "start", reviewer_id)
    assert reviewer_started.returncode == 0
    assert parse_fields(reviewer_started.stdout.strip()) == {
        "agent_id": reviewer_id,
        "status": "running",
        "runtime_status": "running",
        "runtime_handle": "runtime-002",
    }

    sent = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please review the latest patch",
        "--topic",
        "review handoff",
    )
    assert sent.returncode == 0
    sent_fields = parse_fields(sent.stdout.strip())
    assert sent_fields["from_agent"] == planner_id
    assert sent_fields["to_agent"] == reviewer_id
    assert sent_fields["kind"] == "request"
    thread_id = sent_fields["thread_id"]
    first_message_id = sent_fields["message_id"]

    replied = run_module(
        tmp_path,
        "reply",
        first_message_id,
        "--from-agent",
        reviewer_id,
        "--body",
        "review complete",
    )
    assert replied.returncode == 0
    reply_fields = parse_fields(replied.stdout.strip())
    assert reply_fields["thread_id"] == thread_id
    assert reply_fields["reply_to_message_id"] == first_message_id
    assert reply_fields["from_agent"] == reviewer_id
    assert reply_fields["to_agent"] == planner_id
    assert reply_fields["kind"] == "answer"

    added = run_module(
        tmp_path,
        "handoff",
        "add",
        "--thread-id",
        thread_id,
        "--from-agent",
        reviewer_id,
        "--to-agent",
        planner_id,
        "--type",
        "report",
        "--location",
        "reports/review.md",
        "--summary",
        "Review notes ready",
    )
    assert added.returncode == 0
    add_fields = parse_fields(added.stdout.strip())
    assert add_fields["thread_id"] == thread_id
    assert add_fields["from_agent"] == reviewer_id
    assert add_fields["to_agent"] == planner_id
    assert add_fields["type"] == "report"
    assert add_fields["location"] == "reports/review.md"
    assert add_fields["summary"] == "Review␠notes␠ready"

    collaboration = load_collaboration(tmp_path)
    return {
        "planner_id": planner_id,
        "reviewer_id": reviewer_id,
        "thread_id": thread_id,
        "first_message_id": first_message_id,
        "reply_message_id": reply_fields["message_id"],
        "handoff_id": add_fields["handoff_id"],
        "thread_created_at": collaboration["threads"][0]["created_at"],
        "thread_updated_at": collaboration["threads"][0]["updated_at"],
        "handoff_created_at": collaboration["handoffs"][0]["created_at"],
        "fake_docker_state_path": str(fake_bin / "fake-docker-state.json"),
    }


def test_doctor_reports_missing_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_bin = tmp_path / 'empty-bin'
    empty_bin.mkdir()
    monkeypatch.setenv('PATH', str(empty_bin))
    monkeypatch.delenv('MAIA_BROKER_URL', raising=False)

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[0]) == {
        'check': 'docker_cli',
        'status': 'missing',
        'detail': 'docker␠binary␠not␠found␠in␠PATH',
        'remediation': 'install␠docker␠cli␠or␠docker␠engine␠on␠this␠host',
    }
    assert parse_fields(lines[3]) == {
        'check': 'broker_url',
        'status': 'missing',
        'detail': 'MAIA_BROKER_URL␠is␠not␠set',
        'remediation': 'optional:␠set␠MAIA_BROKER_URL␠to␠enable␠broker␠readiness␠checks',
    }
    assert parse_fields(lines[-1]) == {
        'kind': 'summary',
        'status': 'fail',
        'failed': 'docker_cli,docker_compose,docker_daemon',
        'next_step': 'install␠docker␠then␠rerun␠maia␠doctor',
    }


def test_doctor_reports_healthy_docker_stack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    host, port = listener.getsockname()
    monkeypatch.setenv('MAIA_BROKER_URL', f'amqp://guest:secret@{host}:{port}/%2F')

    result = run_module(tmp_path, 'doctor')
    listener.close()

    assert result.returncode == 0
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[0]) == {
        'check': 'docker_cli',
        'status': 'ok',
        'detail': str(fake_docker),
        'remediation': 'no␠action␠needed',
    }
    assert parse_fields(lines[1]) == {
        'check': 'docker_compose',
        'status': 'ok',
        'detail': 'docker␠compose␠available',
        'remediation': 'no␠action␠needed',
    }
    assert parse_fields(lines[2]) == {
        'check': 'docker_daemon',
        'status': 'ok',
        'detail': 'docker␠daemon␠reachable',
        'remediation': 'no␠action␠needed',
    }
    assert parse_fields(lines[3])['check'] == 'broker_url'
    assert parse_fields(lines[3])['status'] == 'ok'
    assert parse_fields(lines[3])['detail'] == f'amqp://guest:***@{host}:{port}/%2F'
    assert parse_fields(lines[4]) == {
        'check': 'broker_tcp',
        'status': 'ok',
        'detail': f'tcp␠reachability␠confirmed␠for␠{host}:{port}',
        'remediation': 'no␠action␠needed',
    }
    assert parse_fields(lines[5]) == {
        'kind': 'summary',
        'status': 'ok',
        'failed': '-',
        'next_step': 'runtime␠prerequisites␠satisfied',
    }


def test_doctor_accepts_broker_url_without_explicit_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv('MAIA_BROKER_URL', 'amqp://guest:secret@127.0.0.1/%2F')

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[3]) == {
        'check': 'broker_url',
        'status': 'ok',
        'detail': 'amqp://guest:***@127.0.0.1/%2F',
        'remediation': 'no␠action␠needed',
    }
    assert parse_fields(lines[4])['check'] == 'broker_tcp'


def test_redact_broker_url_preserves_ipv6_brackets_and_hides_password() -> None:
    assert cli_module._redact_broker_url('amqp://guest:secret@[::1]:5672/%2F') == 'amqp://guest:***@[::1]:5672/%2F'


def test_doctor_reports_invalid_broker_url_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv('MAIA_BROKER_URL', 'amqp://guest:secret@127.0.0.1:notaport/%2F')

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[3]) == {
        'check': 'broker_url',
        'status': 'fail',
        'detail': 'MAIA_BROKER_URL␠must␠include␠a␠valid␠numeric␠port',
        'remediation': 'set␠MAIA_BROKER_URL␠to␠a␠full␠amqp␠URL␠like␠amqp://user:pass@host:5672/vhost',
    }
    assert parse_fields(lines[-1]) == {
        'kind': 'summary',
        'status': 'fail',
        'failed': 'broker_url',
        'next_step': 'set␠MAIA_BROKER_URL␠then␠rerun␠maia␠doctor',
    }


def test_agent_new_list_status_and_tune_profile_metadata(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")

    listed = run_module(tmp_path, "agent", "list")
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip() == f"agent_id={agent_id} name=demo status=stopped"

    before = run_module(tmp_path, "agent", "status", agent_id)
    assert before.returncode == 0
    assert before.stderr == ""
    assert parse_fields(before.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "status": "stopped",
        "persona": "∅",
        "role": "∅",
        "model": "∅",
        "tags": "-",
        "runtime_status": "stopped",
        "runtime_handle": "-",
    }

    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--persona",
        "nightwatch",
        "--role",
        "researcher",
        "--model",
        "gpt-5",
        "--tags",
        "runtime,focus,runtime",
    )
    assert tuned.returncode == 0
    assert tuned.stderr == ""
    assert parse_fields(tuned.stdout.strip()) == {
        "agent_id": agent_id,
        "persona": "nightwatch",
        "role": "researcher",
        "model": "gpt-5",
        "tags": "runtime,focus",
    }

    after = run_module(tmp_path, "agent", "status", agent_id)
    assert after.returncode == 0
    assert after.stderr == ""
    assert parse_fields(after.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "status": "stopped",
        "persona": "nightwatch",
        "role": "researcher",
        "model": "gpt-5",
        "tags": "runtime,focus",
        "runtime_status": "stopped",
        "runtime_handle": "-",
    }

    assert load_registry(tmp_path) == {
        "agents": [
            {
                "agent_id": agent_id,
                "name": "demo",
                "status": "stopped",
                "persona": "nightwatch",
                "role": "researcher",
                "model": "gpt-5",
                "tags": ["runtime", "focus"],
            }
        ]
    }


def test_agent_tune_validation_and_clear_flags(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "alpha")

    no_changes = run_module(tmp_path, "agent", "tune", agent_id)
    assert no_changes.returncode == 1
    assert no_changes.stdout == ""
    assert no_changes.stderr.strip() == "error: Agent tune requires at least one change flag"

    invalid_tags = run_module(tmp_path, "agent", "tune", agent_id, "--tags", "ok,,bad")
    assert invalid_tags.returncode == 1
    assert invalid_tags.stdout == ""
    assert invalid_tags.stderr.strip() == (
        "error: Agent tags must be a comma-separated list of non-empty values"
    )

    seeded = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--role",
        "reviewer",
        "--model",
        "claude",
        "--tags",
        "ops,nightly",
    )
    assert seeded.returncode == 0

    cleared = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--clear-role",
        "--clear-model",
        "--clear-tags",
    )
    assert cleared.returncode == 0
    assert cleared.stderr == ""
    assert parse_fields(cleared.stdout.strip()) == {
        "agent_id": agent_id,
        "role": "∅",
        "model": "∅",
        "tags": "-",
    }

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    fields = parse_fields(status.stdout.strip())
    assert fields["role"] == "∅"
    assert fields["model"] == "∅"
    assert fields["tags"] == "-"



def test_agent_tune_and_status_encode_persona_whitespace_and_newlines(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")
    persona_path = tmp_path / "persona.txt"
    persona_path.write_text("research analyst\n", encoding="utf-8")

    tuned = run_module(tmp_path, "agent", "tune", agent_id, "--persona-file", str(persona_path))
    assert tuned.returncode == 0
    assert tuned.stderr == ""
    assert parse_fields(tuned.stdout.strip()) == {
        "agent_id": agent_id,
        "persona": "research␠analyst↵",
    }

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert status.stderr == ""
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "status": "stopped",
        "persona": "research␠analyst↵",
        "role": "∅",
        "model": "∅",
        "tags": "-",
        "runtime_status": "stopped",
        "runtime_handle": "-",
    }


def test_agent_tune_runtime_spec_persists_and_can_clear(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")

    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
        "--runtime-env",
        "MAIA_ROLE=review",
    )
    assert tuned.returncode == 0
    assert tuned.stderr == ""
    assert parse_fields(tuned.stdout.strip()) == {
        "agent_id": agent_id,
        "runtime_image": "ghcr.io/example/reviewer:latest",
        "runtime_workspace": "/workspace/reviewer",
        "runtime_command": "python,-m,reviewer",
        "runtime_env": "MAIA_ENV,MAIA_ROLE",
    }

    registry = load_registry(tmp_path)
    assert registry["agents"][0]["runtime_spec"] == {
        "image": "ghcr.io/example/reviewer:latest",
        "workspace": "/workspace/reviewer",
        "command": ["python", "-m", "reviewer"],
        "env": {"MAIA_ENV": "test", "MAIA_ROLE": "review"},
    }

    cleared = run_module(tmp_path, "agent", "tune", agent_id, "--clear-runtime")
    assert cleared.returncode == 0
    assert cleared.stderr == ""
    assert parse_fields(cleared.stdout.strip()) == {
        "agent_id": agent_id,
        "runtime": "cleared",
    }
    assert "runtime_spec" not in load_registry(tmp_path)["agents"][0]


def test_workspace_show_surfaces_runtime_spec_context(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")

    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
        "MAIA_ROLE=review",
        "--runtime-env",
        "MAIA_ENV=test",
    )
    assert tuned.returncode == 0

    shown = run_module(tmp_path, "workspace", "show", agent_id)

    assert shown.returncode == 0
    assert shown.stderr == ""
    assert parse_fields(shown.stdout.strip()) == {
        "agent_id": agent_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/workspace/reviewer",
        "runtime_image": "ghcr.io/example/reviewer:latest",
        "runtime_command": "python,-m,reviewer",
        "runtime_env_keys": "MAIA_ENV,MAIA_ROLE",
    }


def test_workspace_show_rejects_agent_without_runtime_spec(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")

    shown = run_module(tmp_path, "workspace", "show", agent_id)

    assert shown.returncode == 1
    assert shown.stderr.strip() == (
        f"error: Workspace context unavailable for agent {agent_id!r}: runtime spec is not configured"
    )


def test_workspace_show_rejects_agent_with_missing_runtime_workspace(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")
    registry = load_registry(tmp_path)
    registry["agents"][0]["runtime_spec"] = {
        "image": "ghcr.io/example/reviewer:latest",
        "workspace": "",
        "command": ["python", "-m", "reviewer"],
        "env": {"MAIA_ENV": "test"},
    }
    write_registry(get_registry_path({"HOME": str(tmp_path)}), registry)

    shown = run_module(tmp_path, "workspace", "show", agent_id)

    assert shown.returncode == 1
    assert shown.stderr.strip() == (
        f"error: Workspace context unavailable for agent {agent_id!r}: runtime workspace is not configured"
    )


def test_agent_tune_runtime_spec_validation_errors(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")

    missing_workspace = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        "ghcr.io/example/reviewer:latest",
    )
    assert missing_workspace.returncode == 1
    assert missing_workspace.stderr.strip() == "error: Agent runtime spec requires --runtime-workspace"

    missing_command = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        "ghcr.io/example/reviewer:latest",
        "--runtime-workspace",
        "/workspace/reviewer",
        "--runtime-env",
        "MAIA_ENV=test",
    )
    assert missing_command.returncode == 1
    assert missing_command.stderr.strip() == "error: Agent runtime spec requires at least one --runtime-command"

    missing_env = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        "ghcr.io/example/reviewer:latest",
        "--runtime-workspace",
        "/workspace/reviewer",
        "--runtime-command",
        "python",
    )
    assert missing_env.returncode == 1
    assert missing_env.stderr.strip() == "error: Agent runtime spec requires at least one --runtime-env"

    bad_env = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        "ghcr.io/example/reviewer:latest",
        "--runtime-workspace",
        "/workspace/reviewer",
        "--runtime-command",
        "python",
        "--runtime-env",
        "BROKEN",
    )
    assert bad_env.returncode == 1
    assert bad_env.stderr.strip() == "error: Agent runtime env entries must use KEY=VALUE format"

    duplicate_env = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        "ghcr.io/example/reviewer:latest",
        "--runtime-workspace",
        "/workspace/reviewer",
        "--runtime-command",
        "python",
        "--runtime-env",
        "MAIA_ENV=test",
        "--runtime-env",
        "MAIA_ENV=prod",
    )
    assert duplicate_env.returncode == 1
    assert duplicate_env.stderr.strip() == "error: Duplicate agent runtime env key: 'MAIA_ENV'"

    clear_plus_set = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--clear-runtime",
        "--runtime-image",
        "ghcr.io/example/reviewer:latest",
    )
    assert clear_plus_set.returncode == 1
    assert clear_plus_set.stderr.strip() == (
        "error: Agent tune runtime clear cannot be combined with runtime set flags"
    )



def test_agent_runtime_start_status_logs_stop_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
    )
    assert tuned.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)
    assert started.returncode == 0
    assert parse_fields(started.stdout.strip()) == {
        "agent_id": agent_id,
        "status": "running",
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
    }

    started_again = run_module(tmp_path, "agent", "start", agent_id)
    assert started_again.returncode == 1
    assert started_again.stderr.strip() == f"error: Agent with id '{agent_id}' is already marked running"

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "status": "running",
        "persona": "∅",
        "role": "∅",
        "model": "∅",
        "tags": "-",
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
    }

    logs = run_module(tmp_path, "agent", "logs", agent_id, "--tail-lines", "1")
    assert logs.returncode == 0
    log_lines = logs.stdout.strip().splitlines()
    assert parse_fields(log_lines[0]) == {
        "agent_id": agent_id,
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
        "lines": "1",
    }
    assert parse_fields(log_lines[1]) == {"line": "line␠2"}

    stopped = run_module(tmp_path, "agent", "stop", agent_id)
    assert stopped.returncode == 0
    assert parse_fields(stopped.stdout.strip()) == {
        "agent_id": agent_id,
        "status": "stopped",
        "runtime_status": "stopped",
        "runtime_handle": "runtime-001",
    }

    stopped_again = run_module(tmp_path, "agent", "stop", agent_id)
    assert stopped_again.returncode == 1
    assert stopped_again.stderr.strip() == f"error: Agent runtime for id '{agent_id}' is not running"

    logs_after_stop = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs_after_stop.returncode == 1
    assert logs_after_stop.stderr.strip() == f"error: Agent runtime for id '{agent_id}' is not running"



def test_agent_lifecycle_archive_restore_and_purge(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")

    start_without_runtime = run_module(tmp_path, "agent", "start", agent_id)
    assert start_without_runtime.returncode == 1
    assert start_without_runtime.stderr.strip() == (
        "error: Invalid runtime start request agent runtime_spec: expected RuntimeSpec"
    )

    for command, expected_status in [
        ("archive", "archived"),
        ("restore", "stopped"),
        ("archive", "archived"),
    ]:
        result = run_module(tmp_path, "agent", command, agent_id)
        assert result.returncode == 0
        assert result.stderr == ""
        assert parse_fields(result.stdout.strip()) == {
            "agent_id": agent_id,
            "status": expected_status,
        }

    team_updated = run_module(
        tmp_path,
        "team",
        "update",
        "--name",
        "demo-team",
        "--default-agent",
        agent_id,
    )
    assert team_updated.returncode == 0

    purge = run_module(tmp_path, "agent", "purge", agent_id)
    assert purge.returncode == 0
    assert purge.stderr == ""
    assert parse_fields(purge.stdout.strip()) == {"agent_id": agent_id}

    listed = run_module(tmp_path, "agent", "list")
    assert listed.returncode == 0
    assert listed.stdout.strip() == ""
    assert load_registry(tmp_path) == {"agents": []}
    assert load_team_metadata(get_team_metadata_path({"HOME": str(tmp_path)})) == TeamMetadata(
        team_name="demo-team",
        team_description="",
        team_tags=[],
        default_agent_id="",
    )



def test_agent_status_uses_stored_runtime_state_after_runtime_spec_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
    )
    assert tuned.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)
    assert started.returncode == 0

    cleared = run_module(tmp_path, "agent", "tune", agent_id, "--clear-runtime")
    assert cleared.returncode == 0

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "status": "running",
        "persona": "∅",
        "role": "∅",
        "model": "∅",
        "tags": "-",
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
    }



def test_runtime_commands_require_active_runtime_state(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")

    stopped = run_module(tmp_path, "agent", "stop", agent_id)
    assert stopped.returncode == 1
    assert stopped.stderr.strip() == f"error: Agent runtime for id '{agent_id}' is not running"

    logs = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs.returncode == 1
    assert logs.stderr.strip() == f"error: Agent runtime for id '{agent_id}' is not running"



def test_stale_runtime_state_is_cleared_on_status_and_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
    )
    assert tuned.returncode == 0
    started = run_module(tmp_path, "agent", "start", agent_id)
    assert started.returncode == 0

    (tmp_path / "bin" / "fake-docker-state.json").unlink()

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 1
    assert status.stderr.strip() == (
        f"error: Stale runtime state detected for agent '{agent_id}'; cleared local runtime state"
    )
    assert load_runtime_state(tmp_path) == {"runtimes": []}

    status_after = run_module(tmp_path, "agent", "status", agent_id)
    assert status_after.returncode == 0
    assert parse_fields(status_after.stdout.strip())["status"] == "stopped"

    started_again = run_module(tmp_path, "agent", "start", agent_id)
    assert started_again.returncode == 0
    (tmp_path / "bin" / "fake-docker-state.json").unlink()

    logs = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs.returncode == 1
    assert logs.stderr.strip() == (
        f"error: Stale runtime state detected for agent '{agent_id}'; cleared local runtime state"
    )
    assert load_runtime_state(tmp_path) == {"runtimes": []}



def test_agent_purge_removes_runtime_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
    )
    assert tuned.returncode == 0
    started = run_module(tmp_path, "agent", "start", agent_id)
    assert started.returncode == 0

    archived = run_module(tmp_path, "agent", "archive", agent_id)
    assert archived.returncode == 0
    purged = run_module(tmp_path, "agent", "purge", agent_id)
    assert purged.returncode == 0

    assert load_runtime_state(tmp_path) == {"runtimes": []}



def test_import_prunes_dangling_runtime_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    source_home = tmp_path / "source"
    dest_home = tmp_path / "dest"
    source_agent = create_agent(source_home, "source-agent")
    dest_agent = create_agent(dest_home, "dest-agent")

    tuned = run_module(
        dest_home,
        "agent",
        "tune",
        dest_agent,
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
    )
    assert tuned.returncode == 0
    started = run_module(dest_home, "agent", "start", dest_agent)
    assert started.returncode == 0

    bundle_path = source_home / "snapshot.maia"
    exported = run_module(source_home, "export", str(bundle_path))
    assert exported.returncode == 0

    imported = run_module(dest_home, "import", str(bundle_path), "--yes")
    assert imported.returncode == 0

    assert load_registry(dest_home) == {
        "agents": [
            {
                "agent_id": source_agent,
                "name": "source-agent",
                "status": "stopped",
                "persona": "",
            }
        ]
    }
    assert load_runtime_state(dest_home) == {"runtimes": []}



def test_send_inbox_thread_and_reply_flow(tmp_path: Path) -> None:
    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")

    sent = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please review phase 3",
        "--topic",
        "phase 3 review",
        "--kind",
        "request",
    )
    assert sent.returncode == 0
    assert sent.stderr == ""
    sent_fields = parse_fields(sent.stdout.strip())
    assert sent_fields["from_agent"] == planner_id
    assert sent_fields["to_agent"] == reviewer_id
    assert sent_fields["kind"] == "request"
    thread_id = sent_fields["thread_id"]
    first_message_id = sent_fields["message_id"]

    inbox = run_module(tmp_path, "inbox", reviewer_id)
    assert inbox.returncode == 0
    lines = line_map(inbox.stdout)
    assert parse_fields(lines["inbox"]) == {
        "agent_id": reviewer_id,
        "messages": "1",
    }
    inbox_message = parse_fields(inbox.stdout.strip().splitlines()[1])
    assert inbox_message["thread_id"] == thread_id
    assert inbox_message["from_agent"] == planner_id
    assert inbox_message["to_agent"] == reviewer_id
    assert inbox_message["kind"] == "request"
    assert inbox_message["body"] == "please␠review␠phase␠3"
    assert inbox_message["reply_to_message_id"] == "-"

    thread_created_at = load_collaboration(tmp_path)["threads"][0]["created_at"]
    thread = run_module(tmp_path, "thread", thread_id)
    assert thread.returncode == 0
    thread_lines = thread.stdout.strip().splitlines()
    assert parse_fields(thread_lines[0]) == {
        "thread_id": thread_id,
        "topic": "phase␠3␠review",
        "participants": f"{planner_id},{reviewer_id}",
        "participant_runtime": f"{planner_id}:stopped,{reviewer_id}:stopped",
        "created_by": planner_id,
        "status": "open",
        "updated_at": thread_created_at,
        "pending_on": reviewer_id,
        "handoffs": "0",
        "messages": "1",
        "created_at": thread_created_at,
        "recent_handoff_id": "-",
        "recent_handoff_from": "-",
        "recent_handoff_to": "-",
        "recent_handoff_type": "-",
        "recent_handoff_location": "-",
        "recent_handoff_summary": "-",
        "recent_handoff_created_at": "-",
    }
    thread_message = parse_fields(thread_lines[1])
    assert thread_message["message_id"] == first_message_id

    replied = run_module(
        tmp_path,
        "reply",
        first_message_id,
        "--from-agent",
        reviewer_id,
        "--body",
        "looks good",
    )
    assert replied.returncode == 0
    reply_fields = parse_fields(replied.stdout.strip())
    assert reply_fields["thread_id"] == thread_id
    assert reply_fields["reply_to_message_id"] == first_message_id
    assert reply_fields["from_agent"] == reviewer_id
    assert reply_fields["to_agent"] == planner_id
    assert reply_fields["kind"] == "answer"

    planner_inbox = run_module(tmp_path, "inbox", planner_id)
    assert planner_inbox.returncode == 0
    planner_lines = planner_inbox.stdout.strip().splitlines()
    assert parse_fields(planner_lines[0]) == {
        "agent_id": planner_id,
        "messages": "1",
    }
    planner_message = parse_fields(planner_lines[1])
    assert planner_message["reply_to_message_id"] == first_message_id
    assert planner_message["body"] == "looks␠good"

    collaboration = load_collaboration(tmp_path)
    assert len(collaboration["threads"]) == 1
    assert len(collaboration["messages"]) == 2


def test_v1_golden_flow_smoke_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)
    planner_id = flow["planner_id"]
    reviewer_id = flow["reviewer_id"]
    thread_id = flow["thread_id"]
    first_message_id = flow["first_message_id"]

    thread_list = run_module(tmp_path, "thread", "list", "--status", "open")
    assert thread_list.returncode == 0
    assert parse_fields(thread_list.stdout.strip()) == {
        "thread_id": thread_id,
        "topic": "review␠handoff",
        "participants": f"{planner_id},{reviewer_id}",
        "participant_runtime": f"{planner_id}:running,{reviewer_id}:running",
        "status": "open",
        "updated_at": flow["thread_updated_at"],
        "pending_on": planner_id,
        "handoffs": "1",
        "messages": "2",
    }

    thread_show = run_module(tmp_path, "thread", "show", thread_id)
    assert thread_show.returncode == 0
    thread_lines = thread_show.stdout.strip().splitlines()
    assert parse_fields(thread_lines[0]) == {
        "thread_id": thread_id,
        "topic": "review␠handoff",
        "participants": f"{planner_id},{reviewer_id}",
        "participant_runtime": f"{planner_id}:running,{reviewer_id}:running",
        "status": "open",
        "updated_at": flow["thread_updated_at"],
        "pending_on": planner_id,
        "handoffs": "1",
        "messages": "2",
        "created_by": planner_id,
        "created_at": flow["thread_created_at"],
        "recent_handoff_id": flow["handoff_id"],
        "recent_handoff_from": reviewer_id,
        "recent_handoff_to": planner_id,
        "recent_handoff_type": "report",
        "recent_handoff_location": "reports/review.md",
        "recent_handoff_summary": "Review␠notes␠ready",
        "recent_handoff_created_at": flow["handoff_created_at"],
    }
    assert parse_fields(thread_lines[1]) == {
        "message_id": first_message_id,
        "thread_id": thread_id,
        "from_agent": planner_id,
        "to_agent": reviewer_id,
        "kind": "request",
        "body": "please␠review␠the␠latest␠patch",
        "created_at": flow["thread_created_at"],
        "reply_to_message_id": "-",
    }
    assert parse_fields(thread_lines[2]) == {
        "message_id": flow["reply_message_id"],
        "thread_id": thread_id,
        "from_agent": reviewer_id,
        "to_agent": planner_id,
        "kind": "answer",
        "body": "review␠complete",
        "created_at": flow["thread_updated_at"],
        "reply_to_message_id": first_message_id,
    }

    handoff_show = run_module(tmp_path, "handoff", "show", flow["handoff_id"])
    assert handoff_show.returncode == 0
    handoff_lines = handoff_show.stdout.strip().splitlines()
    assert parse_fields(handoff_lines[0]) == {
        "handoff_id": flow["handoff_id"],
        "thread_id": thread_id,
        "from_agent": reviewer_id,
        "to_agent": planner_id,
        "type": "report",
        "location": "reports/review.md",
        "summary": "Review␠notes␠ready",
        "created_at": flow["handoff_created_at"],
    }
    assert parse_fields(handoff_lines[1]) == {
        "handoff_role": "source",
        "agent_id": reviewer_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/workspace/reviewer",
        "runtime_image": "ghcr.io/example/reviewer:latest",
        "runtime_command": "python,-m,reviewer",
        "runtime_env_keys": "MAIA_ENV,MAIA_ROLE",
    }
    assert parse_fields(handoff_lines[2]) == {
        "handoff_role": "target",
        "agent_id": planner_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/workspace/planner",
        "runtime_image": "ghcr.io/example/planner:latest",
        "runtime_command": "python,-m,planner",
        "runtime_env_keys": "MAIA_ENV,MAIA_ROLE",
    }

    workspace = run_module(tmp_path, "workspace", "show", planner_id)
    assert workspace.returncode == 0
    assert parse_fields(workspace.stdout.strip()) == {
        "agent_id": planner_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/workspace/planner",
        "runtime_image": "ghcr.io/example/planner:latest",
        "runtime_command": "python,-m,planner",
        "runtime_env_keys": "MAIA_ENV,MAIA_ROLE",
    }

    status = run_module(tmp_path, "agent", "status", planner_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": planner_id,
        "name": "planner",
        "status": "running",
        "persona": "∅",
        "role": "planner",
        "model": "∅",
        "tags": "-",
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
    }

    logs = run_module(tmp_path, "agent", "logs", planner_id, "--tail-lines", "2")
    assert logs.returncode == 0
    log_lines = logs.stdout.strip().splitlines()
    assert parse_fields(log_lines[0]) == {
        "agent_id": planner_id,
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
        "lines": "2",
    }
    assert parse_fields(log_lines[1]) == {"line": "line␠1"}
    assert parse_fields(log_lines[2]) == {"line": "line␠2"}


def test_v1_golden_flow_reports_malformed_runtime_state_at_status_and_logs_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)
    runtime_state_path = get_runtime_state_path({"HOME": str(tmp_path)})
    runtime_state_path.write_text("{bad json\n", encoding="utf-8")
    expected_error = (
        f"error: Invalid runtime state JSON in {runtime_state_path}: "
        "Expecting property name enclosed in double quotes"
    )

    workspace = run_module(tmp_path, "workspace", "show", flow["planner_id"])
    assert workspace.returncode == 0

    status = run_module(tmp_path, "agent", "status", flow["planner_id"])
    assert status.returncode == 1
    assert status.stderr.strip() == expected_error

    logs = run_module(tmp_path, "agent", "logs", flow["planner_id"])
    assert logs.returncode == 1
    assert logs.stderr.strip() == expected_error


def test_v1_golden_flow_reports_stale_runtime_state_at_status_and_logs_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)
    Path(flow["fake_docker_state_path"]).unlink()

    status = run_module(tmp_path, "agent", "status", flow["planner_id"])
    assert status.returncode == 1
    assert status.stderr.strip() == (
        f"error: Stale runtime state detected for agent '{flow['planner_id']}'; "
        "cleared local runtime state"
    )
    remaining_after_status = load_runtime_state(tmp_path)
    assert {
        runtime["agent_id"] for runtime in remaining_after_status["runtimes"]
    } == {flow["reviewer_id"]}

    logs = run_module(tmp_path, "agent", "logs", flow["reviewer_id"])
    assert logs.returncode == 1
    assert logs.stderr.strip() == (
        f"error: Stale runtime state detected for agent '{flow['reviewer_id']}'; "
        "cleared local runtime state"
    )
    assert load_runtime_state(tmp_path) == {"runtimes": []}


def test_v1_golden_flow_reports_malformed_collaboration_state_at_thread_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)
    collaboration_path = get_collaboration_path({"HOME": str(tmp_path)})
    collaboration_path.write_text("{bad json\n", encoding="utf-8")
    expected_error = (
        f"error: Invalid collaboration JSON in {collaboration_path}: "
        "Expecting property name enclosed in double quotes"
    )

    thread_list = run_module(tmp_path, "thread", "list", "--status", "open")
    assert thread_list.returncode == 1
    assert thread_list.stderr.strip() == expected_error

    workspace = run_module(tmp_path, "workspace", "show", flow["planner_id"])
    assert workspace.returncode == 0

    status = run_module(tmp_path, "agent", "status", flow["planner_id"])
    assert status.returncode == 0


def test_send_to_existing_thread_and_validation(tmp_path: Path) -> None:
    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")
    analyst_id = create_agent(tmp_path, "analyst")

    first = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "first",
        "--topic",
        "phase 3",
    )
    thread_id = parse_fields(first.stdout.strip())["thread_id"]

    second = run_module(
        tmp_path,
        "send",
        reviewer_id,
        analyst_id,
        "--body",
        "loop analyst in",
        "--thread-id",
        thread_id,
        "--kind",
        "note",
    )
    assert second.returncode == 0

    thread = run_module(tmp_path, "thread", thread_id)
    assert thread.returncode == 0
    thread_fields = parse_fields(thread.stdout.strip().splitlines()[0])
    assert thread_fields["participants"] == f"{planner_id},{reviewer_id},{analyst_id}"
    assert thread_fields["messages"] == "2"

    missing_topic = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "oops",
    )
    assert missing_topic.returncode == 2

    bad_limit = run_module(tmp_path, "inbox", reviewer_id, "--limit", "0")
    assert bad_limit.returncode == 1
    assert "Inbox limit must be >= 1" in bad_limit.stderr


def test_reply_validation_errors(tmp_path: Path) -> None:
    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")
    outsider_id = create_agent(tmp_path, "outsider")

    sent = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please answer",
        "--topic",
        "reply validation",
    )
    message_id = parse_fields(sent.stdout.strip())["message_id"]

    outsider_reply = run_module(
        tmp_path,
        "reply",
        message_id,
        "--from-agent",
        outsider_id,
        "--body",
        "hi",
    )
    assert outsider_reply.returncode == 1
    assert "Reply sender must match the original message recipient" in outsider_reply.stderr

    missing_message = run_module(
        tmp_path,
        "reply",
        "missing123",
        "--from-agent",
        reviewer_id,
        "--body",
        "hi",
    )
    assert missing_message.returncode == 1
    assert "Message with id 'missing123' not found" in missing_message.stderr

    archived = run_module(tmp_path, "agent", "archive", planner_id)
    assert archived.returncode == 0
    purged = run_module(tmp_path, "agent", "purge", planner_id)
    assert purged.returncode == 0

    purged_target_reply = run_module(
        tmp_path,
        "reply",
        message_id,
        "--from-agent",
        reviewer_id,
        "--body",
        "cannot deliver",
    )
    assert purged_target_reply.returncode == 1
    assert f"Agent with id '{planner_id}' not found" in purged_target_reply.stderr


def test_team_show_update_export_and_inspect_scope_v3_bundle(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")

    shown = run_module(tmp_path, "team", "show")
    assert shown.returncode == 0
    assert shown.stderr == ""
    assert parse_fields(shown.stdout.strip()) == {
        "name": "∅",
        "description": "∅",
        "tags": "-",
        "default_agent_id": "∅",
    }

    updated = run_module(
        tmp_path,
        "team",
        "update",
        "--name",
        "research-lab",
        "--description",
        "Nightly migration team",
        "--tags",
        "research,ops,research",
        "--default-agent",
        agent_id,
    )
    assert updated.returncode == 0
    assert updated.stderr == ""
    assert parse_fields(updated.stdout.strip()) == {
        "name": "research-lab",
        "description": "Nightly␠migration␠team",
        "tags": "research,ops",
        "default_agent_id": agent_id,
    }
    assert load_team_metadata(get_team_metadata_path({"HOME": str(tmp_path)})) == TeamMetadata(
        team_name="research-lab",
        team_description="Nightly migration team",
        team_tags=["research", "ops"],
        default_agent_id=agent_id,
    )

    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--role",
        "lead",
        "--model",
        "gpt-5",
        "--tags",
        "prod,nightly",
    )
    assert tuned.returncode == 0

    export_path = get_default_export_path({"HOME": str(tmp_path)})
    exported = run_module(tmp_path, "export")
    assert exported.returncode == 0
    assert exported.stderr == ""
    assert parse_fields(exported.stdout.strip()) == {
        "path": str(export_path),
        "format": "maia-bundle",
        "agents": "1",
    }
    assert export_path.exists()

    bundle_data = read_bundle_archive(export_path)
    manifest = bundle_data["manifest.json"]
    assert manifest["scope_version"] == 3
    assert manifest["portable_state_kinds"] == [
        "registry",
        "team-metadata",
        "agent-profile-metadata",
    ]
    assert manifest["team_name"] == "research-lab"
    assert manifest["team_description"] == "Nightly migration team"
    assert manifest["team_tags"] == ["research", "ops"]
    assert manifest["default_agent_id"] == agent_id
    assert bundle_data["registry.json"]["agents"][0]["role"] == "lead"
    assert bundle_data["registry.json"]["agents"][0]["model"] == "gpt-5"
    assert bundle_data["registry.json"]["agents"][0]["tags"] == ["prod", "nightly"]

    inspected = run_module(tmp_path, "inspect", str(export_path))
    assert inspected.returncode == 0
    assert inspected.stderr == ""
    lines = line_map(inspected.stdout)
    assert parse_fields(lines["inspected"]) == {
        "path": str(export_path),
        "format": "maia-bundle",
        "registry": "registry.json",
        "agents": "1",
    }
    assert parse_fields(lines["manifest"])["scope_version"] == "3"
    assert parse_fields(lines["portable"])["state_kinds"] == (
        "registry,team-metadata,agent-profile-metadata"
    )
    assert parse_fields(lines["team"]) == {
        "name": "research-lab",
        "description": "Nightly␠migration␠team",
        "tags": "research,ops",
        "default_agent_id": agent_id,
    }
    assert parse_fields(lines["agents"]) == {
        "names": "demo",
        "statuses": "stopped:1",
    }
    assert parse_fields(lines["profiles"]) == {
        "entries": f"{agent_id}:role=lead+model=gpt-5+tags=prod,nightly"
    }


def test_export_and_inspect_encode_paths_and_metadata_with_spaces(tmp_path: Path) -> None:
    home = tmp_path / "home with spaces"
    agent_id = create_agent(home, "night shift")
    export_path = home / "exports dir" / "team bundle.maia"

    exported = run_module(
        home,
        "export",
        str(export_path),
        "--label",
        "prod team",
        "--description",
        "nightly snapshot",
    )
    assert exported.returncode == 0
    assert exported.stderr == ""
    assert parse_fields(exported.stdout.strip()) == {
        "path": str(export_path).replace(" ", "␠"),
        "format": "maia-bundle",
        "agents": "1",
    }

    inspected = run_module(home, "inspect", str(export_path))
    assert inspected.returncode == 0
    assert inspected.stderr == ""
    lines = line_map(inspected.stdout)
    assert parse_fields(lines["inspected"]) == {
        "path": str(export_path).replace(" ", "␠"),
        "format": "maia-bundle",
        "registry": "registry.json",
        "agents": "1",
    }
    assert parse_fields(lines["bundle"]) == {
        "label": "prod␠team",
        "created_by": "maia-cli",
        "maia_version": "0.1.0",
    }
    assert parse_fields(lines["description"]) == {"value": "nightly␠snapshot"}
    assert parse_fields(lines["agents"]) == {
        "names": "night␠shift",
        "statuses": "stopped:1",
    }
    assert parse_fields(lines["team"]) == {
        "name": "∅",
        "description": "∅",
        "tags": "-",
        "default_agent_id": "∅",
    }
    assert parse_fields(lines["profiles"]) == {
        "entries": f"{agent_id}:role=∅+model=∅+tags=-"
    }


def test_export_sanitizes_stale_team_default_agent_id(tmp_path: Path) -> None:
    home = tmp_path / "stale-team-home"
    create_agent(home, "demo")
    save_team_metadata(
        get_team_metadata_path({"HOME": str(home)}),
        TeamMetadata(
            team_name="ops-team",
            team_description="",
            team_tags=["ops"],
            default_agent_id="missing-agent",
        ),
    )
    export_path = home / "stale-default.maia"

    exported = run_module(home, "export", str(export_path))
    assert exported.returncode == 0
    bundle_data = read_bundle_archive(export_path)
    assert bundle_data["manifest.json"]["default_agent_id"] == ""

    inspected = run_module(home, "inspect", str(export_path))
    assert inspected.returncode == 0
    assert parse_fields(line_map(inspected.stdout)["team"]) == {
        "name": "ops-team",
        "description": "∅",
        "tags": "ops",
        "default_agent_id": "∅",
    }


def test_import_preview_reports_role_model_tags_diffs_and_imports(tmp_path: Path) -> None:
    source_home = tmp_path / "source"
    dest_home = tmp_path / "dest"

    agent_id = create_agent(source_home, "demo")
    tuned = run_module(
        source_home,
        "agent",
        "tune",
        agent_id,
        "--persona",
        "analyst",
        "--role",
        "reviewer",
        "--model",
        "gpt-5",
        "--tags",
        "qa,ops",
    )
    assert tuned.returncode == 0
    team_update = run_module(
        source_home,
        "team",
        "update",
        "--name",
        "import-team",
        "--default-agent",
        agent_id,
    )
    assert team_update.returncode == 0

    bundle_path = source_home / "snapshot.maia"
    exported = run_module(source_home, "export", str(bundle_path))
    assert exported.returncode == 0

    write_registry(
        get_registry_path({"HOME": str(dest_home)}),
        {
            "agents": [
                {
                    "agent_id": agent_id,
                    "name": "demo",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "legacy-model",
                    "tags": ["legacy"],
                }
            ]
        },
    )

    preview = run_module(dest_home, "import", str(bundle_path), "--preview", "--verbose-preview")
    assert preview.returncode == 0
    assert preview.stderr == ""
    lines = line_map(preview.stdout)
    assert parse_fields(lines["preview"]) == {
        "source": str(bundle_path),
        "registry": "registry.json",
        "current_agents": "1",
        "incoming_agents": "1",
        "added": "0",
        "removed": "0",
        "changed": "1",
        "unchanged": "0",
    }
    changed_line = lines["changed"]
    assert f"ids={agent_id}" in changed_line
    assert "persona:∅->analyst" in changed_line
    assert "role:∅->reviewer" in changed_line
    assert "model:legacy-model->gpt-5" in changed_line
    assert "tags:legacy->qa,ops" in changed_line

    imported = run_module(dest_home, "import", str(bundle_path), "--yes")
    assert imported.returncode == 0
    assert imported.stderr == ""
    import_lines = line_map(imported.stdout)
    assert parse_fields(import_lines["imported"]) == {
        "source": str(bundle_path),
        "registry": "registry.json",
        "agents": "1",
    }

    status = run_module(dest_home, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "status": "stopped",
        "persona": "analyst",
        "role": "reviewer",
        "model": "gpt-5",
        "tags": "qa,ops",
        "runtime_status": "stopped",
        "runtime_handle": "-",
    }
    assert load_team_metadata(get_team_metadata_path({"HOME": str(dest_home)})).default_agent_id == agent_id


def test_import_preview_encodes_agent_names_with_spaces(tmp_path: Path) -> None:
    source_home = tmp_path / "source spaces"
    dest_home = tmp_path / "dest spaces"
    create_agent(source_home, "alpha beta")
    bundle_path = source_home / "preview-names.maia"
    exported = run_module(source_home, "export", str(bundle_path))
    assert exported.returncode == 0

    preview = run_module(dest_home, "import", str(bundle_path), "--preview")
    assert preview.returncode == 0
    lines = line_map(preview.stdout)
    assert parse_fields(lines["added"]) ["names"] == "alpha␠beta"


def test_import_preview_reports_team_metadata_diffs(tmp_path: Path) -> None:
    source_home = tmp_path / "source-team"
    dest_home = tmp_path / "dest-team"

    agent_id = create_agent(source_home, "demo")
    updated = run_module(
        source_home,
        "team",
        "update",
        "--name",
        "source-team",
        "--description",
        "incoming description",
        "--tags",
        "ops,nightly",
        "--default-agent",
        agent_id,
    )
    assert updated.returncode == 0

    bundle_path = source_home / "team-only.maia"
    exported = run_module(source_home, "export", str(bundle_path))
    assert exported.returncode == 0

    write_registry(
        get_registry_path({"HOME": str(dest_home)}),
        {
            "agents": [
                {
                    "agent_id": agent_id,
                    "name": "demo",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "",
                    "tags": [],
                }
            ]
        },
    )
    save_team_metadata(
        get_team_metadata_path({"HOME": str(dest_home)}),
        TeamMetadata(
            team_name="dest-team",
            team_description="existing description",
            team_tags=["legacy"],
            default_agent_id="",
        ),
    )

    preview = run_module(dest_home, "import", str(bundle_path), "--preview", "--verbose-preview")
    assert preview.returncode == 0
    assert preview.stderr == ""
    lines = line_map(preview.stdout)
    assert parse_fields(lines["preview"]) == {
        "source": str(bundle_path),
        "registry": "registry.json",
        "current_agents": "1",
        "incoming_agents": "1",
        "added": "0",
        "removed": "0",
        "changed": "0",
        "unchanged": "1",
    }
    assert parse_fields(lines["risk"]) == {
        "level": "low-change",
        "reasons": "changed_team_metadata",
    }
    team_line = lines["team"]
    assert "name:dest-team->source-team" in team_line
    assert "description:existing␠description->incoming␠description" in team_line
    assert "tags:legacy->ops,nightly" in team_line
    assert f"default_agent_id:∅->{agent_id}" in team_line


def test_import_rejects_team_default_agent_missing_from_incoming_registry(tmp_path: Path) -> None:
    source_dir = tmp_path / "invalid-team"
    registry_path = source_dir / "registry.json"
    manifest_path = source_dir / "manifest.json"
    write_registry(
        registry_path,
        {
            "agents": [
                {
                    "agent_id": "agent-001",
                    "name": "demo",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "",
                    "tags": [],
                }
            ]
        },
    )
    manifest_path.write_text(
        json.dumps(
            {
                "kind": "maia-backup-manifest",
                "version": 1,
                "scope_version": 2,
                "created_at": "2026-04-14T22:24:00Z",
                "label": "invalid-team",
                "description": "invalid team metadata",
                "created_by": "maia-cli",
                "maia_version": "0.1.0",
                "source_host": "test-host",
                "source_platform": "linux",
                "source_registry_path": str(registry_path),
                "registry_file": "registry.json",
                "portable_paths": ["registry.json"],
                "portable_state_kinds": ["registry", "team-metadata"],
                "runtime_only_paths": ["runtime/"],
                "runtime_only_state_kinds": ["processes", "locks", "cache", "live-sessions"],
                "agents": 1,
                "team_name": "invalid-team",
                "team_description": "invalid team metadata",
                "team_tags": ["ops"],
                "default_agent_id": "missing-agent",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    imported = run_module(tmp_path / "dest-invalid", "import", str(manifest_path), "--yes")
    assert imported.returncode == 1
    assert "missing-agent" in imported.stderr


def test_raw_registry_import_preserves_existing_team_metadata(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw-source"
    dest_home = tmp_path / "raw-dest"
    registry_path = source_dir / "registry.json"
    write_registry(
        registry_path,
        {
            "agents": [
                {
                    "agent_id": "agent-001",
                    "name": "demo",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "",
                    "tags": [],
                }
            ]
        },
    )
    save_team_metadata(
        get_team_metadata_path({"HOME": str(dest_home)}),
        TeamMetadata(
            team_name="existing-team",
            team_description="keep me",
            team_tags=["ops"],
            default_agent_id="",
        ),
    )

    imported = run_module(dest_home, "import", str(registry_path), "--yes")
    assert imported.returncode == 0
    metadata = load_team_metadata(get_team_metadata_path({"HOME": str(dest_home)}))
    assert metadata == TeamMetadata(
        team_name="existing-team",
        team_description="keep me",
        team_tags=["ops"],
        default_agent_id="",
    )


def test_raw_registry_import_clears_dangling_default_agent_id(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw-dangling-source"
    dest_home = tmp_path / "raw-dangling-dest"
    registry_path = source_dir / "registry.json"
    write_registry(
        registry_path,
        {
            "agents": [
                {
                    "agent_id": "other-agent",
                    "name": "other",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "",
                    "tags": [],
                }
            ]
        },
    )
    save_team_metadata(
        get_team_metadata_path({"HOME": str(dest_home)}),
        TeamMetadata(
            team_name="existing-team",
            team_description="keep me",
            team_tags=["ops"],
            default_agent_id="missing-agent",
        ),
    )

    imported = run_module(dest_home, "import", str(registry_path), "--yes")
    assert imported.returncode == 0
    metadata = load_team_metadata(get_team_metadata_path({"HOME": str(dest_home)}))
    assert metadata == TeamMetadata(
        team_name="existing-team",
        team_description="keep me",
        team_tags=["ops"],
        default_agent_id="",
    )


def test_raw_registry_import_and_inspect_ignore_invalid_adjacent_manifest(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw-invalid-manifest"
    registry_path = source_dir / "registry.json"
    manifest_path = source_dir / "manifest.json"
    write_registry(
        registry_path,
        {
            "agents": [
                {
                    "agent_id": "agent-001",
                    "name": "demo",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "",
                    "tags": [],
                }
            ]
        },
    )
    manifest_path.write_text("not-json\n", encoding="utf-8")

    preview = run_module(tmp_path / "raw-invalid-dest", "import", str(registry_path), "--preview")
    assert preview.returncode == 0
    inspected = run_module(tmp_path / "raw-invalid-dest", "inspect", str(registry_path))
    assert inspected.returncode == 0
    assert "format=registry-json" in inspected.stdout


def test_inspect_rejects_team_default_agent_missing_from_manifest_registry(tmp_path: Path) -> None:
    source_dir = tmp_path / "inspect-invalid-team"
    registry_path = source_dir / "registry.json"
    manifest_path = source_dir / "manifest.json"
    write_registry(
        registry_path,
        {
            "agents": [
                {
                    "agent_id": "agent-001",
                    "name": "demo",
                    "status": "stopped",
                    "persona": "",
                    "role": "",
                    "model": "",
                    "tags": [],
                }
            ]
        },
    )
    manifest_path.write_text(
        json.dumps(
            {
                "kind": "maia-backup-manifest",
                "version": 1,
                "scope_version": 2,
                "created_at": "2026-04-14T22:24:00Z",
                "label": "inspect-invalid-team",
                "description": "invalid team metadata",
                "created_by": "maia-cli",
                "maia_version": "0.1.0",
                "source_host": "test-host",
                "source_platform": "linux",
                "source_registry_path": str(registry_path),
                "registry_file": "registry.json",
                "portable_paths": ["registry.json"],
                "portable_state_kinds": ["registry", "team-metadata"],
                "runtime_only_paths": ["runtime/"],
                "runtime_only_state_kinds": ["processes", "locks", "cache", "live-sessions"],
                "agents": 1,
                "team_name": "invalid-team",
                "team_description": "invalid team metadata",
                "team_tags": ["ops"],
                "default_agent_id": "missing-agent",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    inspected = run_module(tmp_path / "inspect-invalid-dest", "inspect", str(manifest_path))
    assert inspected.returncode == 1
    assert "missing-agent" in inspected.stderr


def test_import_without_yes_requires_confirmation_for_team_only_changes(tmp_path: Path) -> None:
    source_home = tmp_path / "team-only-source"
    dest_home = tmp_path / "team-only-dest"

    agent_id = create_agent(source_home, "demo")
    updated = run_module(
        source_home,
        "team",
        "update",
        "--name",
        "incoming-team",
        "--default-agent",
        agent_id,
    )
    assert updated.returncode == 0

    bundle_path = source_home / "team-only-confirm.maia"
    exported = run_module(source_home, "export", str(bundle_path))
    assert exported.returncode == 0

    save_team_metadata(
        get_team_metadata_path({"HOME": str(dest_home)}),
        TeamMetadata(
            team_name="existing-team",
            team_description="",
            team_tags=[],
            default_agent_id="",
        ),
    )

    imported = run_module(dest_home, "import", str(bundle_path))
    assert imported.returncode == 1
    assert "confirm prompt=Proceed with overwrite import? [y/N]" in imported.stdout
    assert "cancelled import" in imported.stdout


@pytest.mark.parametrize(
    ("scope_version", "portable_state_kinds", "team_name", "expect_team_metadata"),
    [
        (1, ["registry"], "", False),
        (2, ["registry", "team-metadata"], "legacy-team", True),
    ],
)
def test_import_accepts_scope_version_1_and_2_manifests(
    tmp_path: Path,
    scope_version: int,
    portable_state_kinds: list[str],
    team_name: str,
    expect_team_metadata: bool,
) -> None:
    source_dir = tmp_path / f"scope-{scope_version}"
    registry_path = source_dir / "registry.json"
    manifest_path = source_dir / "manifest.json"
    agent_id = f"legacy0{scope_version}"

    write_registry(
        registry_path,
        {
            "agents": [
                {
                    "agent_id": agent_id,
                    "name": f"legacy-{scope_version}",
                    "status": "stopped",
                    "persona": "",
                    "role": "legacy-role",
                    "model": "legacy-model",
                    "tags": ["legacy", f"v{scope_version}"],
                }
            ]
        },
    )
    manifest_payload = {
        "kind": "maia-backup-manifest",
        "version": 1,
        "scope_version": scope_version,
        "created_at": "2026-04-14T22:24:00Z",
        "label": f"scope-{scope_version}",
        "description": f"legacy scope {scope_version}",
        "created_by": "maia-cli",
        "maia_version": "0.1.0",
        "source_host": "test-host",
        "source_platform": "linux",
        "source_registry_path": str(registry_path),
        "registry_file": "registry.json",
        "portable_paths": ["registry.json"],
        "portable_state_kinds": portable_state_kinds,
        "runtime_only_paths": ["runtime/"],
        "runtime_only_state_kinds": ["processes", "locks", "cache", "live-sessions"],
        "agents": 1,
        "team_name": team_name,
        "team_description": "legacy description" if expect_team_metadata else "",
        "team_tags": ["legacy", "ops"] if expect_team_metadata else [],
        "default_agent_id": agent_id if expect_team_metadata else "",
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")

    dest_home = tmp_path / f"imported-{scope_version}"
    save_team_metadata(
        get_team_metadata_path({"HOME": str(dest_home)}),
        TeamMetadata(
            team_name="stale-team",
            team_description="stale description",
            team_tags=["stale"],
            default_agent_id="stale-agent",
        ),
    )
    imported = run_module(dest_home, "import", str(manifest_path), "--yes")
    assert imported.returncode == 0
    assert imported.stderr == ""

    status = run_module(dest_home, "agent", "status", agent_id)
    assert status.returncode == 0
    fields = parse_fields(status.stdout.strip())
    assert fields["role"] == "legacy-role"
    assert fields["model"] == "legacy-model"
    assert fields["tags"] == f"legacy,v{scope_version}"

    metadata = load_team_metadata(get_team_metadata_path({"HOME": str(dest_home)}))
    if expect_team_metadata:
        assert metadata == TeamMetadata(
            team_name=team_name,
            team_description="legacy description",
            team_tags=["legacy", "ops"],
            default_agent_id=agent_id,
        )
    else:
        assert metadata == TeamMetadata(
            team_name="stale-team",
            team_description="stale description",
            team_tags=["stale"],
            default_agent_id="",
        )
