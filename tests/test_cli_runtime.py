from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.agent_model import AgentRecord
from maia import cli as cli_module
from maia.app_state import (
    get_agent_hermes_home,
    get_collaboration_path,
    get_default_export_path,
    get_registry_path,
    get_runtime_state_path,
    get_state_db_path,
    get_team_metadata_path,
)
from maia.collaboration_storage import CollaborationStorage
from maia.runtime_state_storage import RuntimeStateStorage
from maia.sqlite_state import SQLiteState
from maia.storage import JsonRegistryStorage
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
        "setup",
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
    registry = JsonRegistryStorage().load(get_state_db_path({"HOME": str(home)}))
    return {"agents": [record.to_dict() for record in registry.list()]}


def load_runtime_state(home: Path) -> dict[str, object]:
    states = RuntimeStateStorage().load(get_state_db_path({"HOME": str(home)}))
    return {"runtimes": [states[agent_id].to_dict() for agent_id in sorted(states)]}


def load_collaboration(home: Path) -> dict[str, object]:
    state = CollaborationStorage().load(get_state_db_path({"HOME": str(home)}))
    return {
        "threads": [thread.to_dict() for thread in state.threads],
        "messages": [message.to_dict() for message in state.messages],
        "handoffs": [handoff.to_dict() for handoff in state.handoffs],
    }


def write_runtime_state(home: Path, payload: dict[str, object]) -> None:
    states = {
        item["agent_id"]: cli_module.RuntimeState.from_dict(item)
        for item in payload.get("runtimes", [])
        if isinstance(item, dict)
    }
    RuntimeStateStorage().save(get_state_db_path({"HOME": str(home)}), states)


def mark_runtime_start_ready(home: Path, agent_id: str, *, setup_status: str = "complete") -> None:
    SQLiteState(get_state_db_path({"HOME": str(home)})).set_infra_status(
        "bootstrap",
        status="ready",
        detail="shared infra is ready",
    )
    write_runtime_state(
        home,
        {
            "runtimes": [
                {
                    "agent_id": agent_id,
                    "runtime_status": "stopped",
                    "setup_status": setup_status,
                }
            ]
        },
    )


def corrupt_sqlite_payload(db_path: Path, table: str, key_field: str, key_value: str, payload: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            f"UPDATE {table} SET payload = ? WHERE {key_field} = ?",
            (payload, key_value),
        )


def write_registry(path: Path, payload: dict[str, object]) -> None:
    storage = JsonRegistryStorage()
    registry_model = storage.load(path)
    for record in list(registry_model.list()):
        registry_model.remove(record.agent_id)
    for item in payload.get("agents", []):
        if not isinstance(item, dict):
            raise AssertionError("test payload agents must be dict objects")
        registry_model.add(AgentRecord.from_dict(item))
    storage.save(path, registry_model)


def read_bundle_archive(path: Path) -> dict[str, object]:
    with ZipFile(path) as archive:
        return {
            name: json.loads(archive.read(name).decode("utf-8"))
            for name in archive.namelist()
        }


def line_map(stdout: str) -> dict[str, str]:
    lines = [line for line in stdout.strip().splitlines() if line]
    return {line.split()[0]: line for line in lines}


def _write_fake_hermes(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import os, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:1] != ['setup']:\n"
        "    print('unsupported hermes command', file=sys.stderr)\n"
        "    raise SystemExit(2)\n"
        "hermes_home = os.environ.get('HERMES_HOME', '')\n"
        "if not hermes_home:\n"
        "    print('missing HERMES_HOME', file=sys.stderr)\n"
        "    raise SystemExit(3)\n"
        "target = Path(hermes_home)\n"
        "target.mkdir(parents=True, exist_ok=True)\n"
        "(target / 'setup-marker.txt').write_text('configured', encoding='utf-8')\n"
        "print(f'fake-hermes-setup hermes_home={hermes_home} agent_id={os.environ.get(\"MAIA_AGENT_ID\", \"\")} agent_name={os.environ.get(\"MAIA_AGENT_NAME\", \"\")}')\n"
        "if os.environ.get('MAIA_FAKE_HERMES_FAIL') == '1':\n"
        "    print('fake-hermes-setup failed', file=sys.stderr)\n"
        "    raise SystemExit(7)\n"
        "raise SystemExit(0)\n",
        encoding='utf-8',
    )
    path.chmod(0o755)


def _write_fake_docker(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import json, sys\n"
        "state_path = Path(__file__).with_name('fake-docker-state.json')\n"
        "if state_path.exists():\n"
        "    state = json.loads(state_path.read_text(encoding='utf-8'))\n"
        "else:\n"
        "    state = {'containers': {}, 'networks': [], 'volumes': [], 'counter': 0}\n"
        "args = sys.argv[1:]\n"
        "def save():\n"
        "    state_path.write_text(json.dumps(state), encoding='utf-8')\n"
        "if args == ['--version']:\n"
        "    print('Docker version 27.0.0')\n"
        "    raise SystemExit(0)\n"
        "if args == ['info']:\n"
        "    print('Server Version: 27.0.0')\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['network', 'inspect']:\n"
        "    name = args[2]\n"
        "    if name not in state['networks']:\n"
        "        print('missing network', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    print(name)\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['network', 'create']:\n"
        "    name = args[2]\n"
        "    if name not in state['networks']:\n"
        "        state['networks'].append(name)\n"
        "        save()\n"
        "    print(name)\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['volume', 'inspect']:\n"
        "    name = args[2]\n"
        "    if name not in state['volumes']:\n"
        "        print('missing volume', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    print(name)\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['volume', 'create']:\n"
        "    name = args[2]\n"
        "    if name not in state['volumes']:\n"
        "        state['volumes'].append(name)\n"
        "        save()\n"
        "    print(name)\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['run', '-d']:\n"
        "    if '--name' in args:\n"
        "        handle = args[args.index('--name') + 1]\n"
        "        logs = ['rabbitmq ready']\n"
        "    else:\n"
        "        state['counter'] += 1\n"
        "        handle = f\"runtime-{state['counter']:03d}\"\n"
        "        logs = ['line 1', 'line 2']\n"
        "    state['containers'][handle] = {'status': 'running', 'logs': logs}\n"
        "    save()\n"
        "    print(handle)\n"
        "    raise SystemExit(0)\n"
        "if args[:1] == ['start']:\n"
        "    handle = args[1]\n"
        "    if handle not in state['containers']:\n"
        "        print('missing container', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    state['containers'][handle]['status'] = 'running'\n"
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
    fake_hermes = fake_bin / "hermes"
    _write_fake_hermes(fake_hermes)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    setup = run_module(tmp_path, "setup")
    assert setup.returncode == 0
    assert setup.stderr == ""

    doctor = run_module(tmp_path, "doctor")
    assert doctor.returncode == 0
    assert doctor.stderr == ""

    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")
    planner_setup = run_module(tmp_path, "agent", "setup", planner_id)
    assert planner_setup.returncode == 0
    reviewer_setup = run_module(tmp_path, "agent", "setup", reviewer_id)
    assert reviewer_setup.returncode == 0

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

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[0]) == {
        'check': 'docker_cli',
        'status': 'missing',
        'detail': 'Docker␠is␠not␠installed␠or␠not␠on␠PATH',
        'remediation': 'Install␠Docker␠on␠this␠host␠to␠use␠runtime␠commands',
    }
    assert parse_fields(lines[2]) == {
        'check': 'queue',
        'status': 'blocked',
        'detail': 'Queue␠health␠needs␠a␠working␠Docker␠daemon',
        'remediation': 'Fix␠Docker␠first⸴␠then␠run␠maia␠doctor␠again',
    }
    assert parse_fields(lines[3])['check'] == 'state_db'
    assert parse_fields(lines[3])['status'] == 'ok'
    assert parse_fields(lines[-1]) == {
        'kind': 'summary',
        'status': 'fail',
        'failed': 'docker_cli,docker_daemon,queue',
        'next_step': 'install␠Docker⸴␠then␠run␠maia␠doctor␠again',
    }


def test_doctor_reports_queue_missing_before_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[0]) == {
        'check': 'docker_cli',
        'status': 'ok',
        'detail': str(fake_docker),
        'remediation': 'No␠action␠needed',
    }
    assert parse_fields(lines[1]) == {
        'check': 'docker_daemon',
        'status': 'ok',
        'detail': 'Docker␠is␠ready',
        'remediation': 'No␠action␠needed',
    }
    assert parse_fields(lines[2]) == {
        'check': 'queue',
        'status': 'missing',
        'detail': 'RabbitMQ␠container␠maia-rabbitmq␠is␠not␠running',
        'remediation': 'Run␠maia␠setup␠to␠bootstrap␠shared␠infra',
    }
    state_db_fields = parse_fields(lines[3])
    assert state_db_fields['check'] == 'state_db'
    assert state_db_fields['status'] == 'ok'
    assert state_db_fields['detail'] == str(get_state_db_path({'HOME': str(tmp_path)}))
    assert parse_fields(lines[4]) == {
        'kind': 'summary',
        'status': 'fail',
        'failed': 'queue',
        'next_step': 'run␠maia␠setup␠to␠bootstrap␠shared␠infra',
    }


def test_doctor_accepts_reachable_external_queue_before_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setenv('MAIA_BROKER_URL', f'amqp://guest:guest@{host}:{port}/%2F')

    result = run_module(tmp_path, 'doctor')
    listener.close()

    assert result.returncode == 0
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[2]) == {
        'check': 'queue',
        'status': 'ok',
        'detail': f'RabbitMQ␠is␠reachable␠at␠{host}:{port}',
        'remediation': 'No␠action␠needed',
    }
    assert parse_fields(lines[-1]) == {
        'kind': 'summary',
        'status': 'ok',
        'failed': '-',
        'next_step': 'shared␠infra␠is␠ready',
    }


def test_doctor_points_to_external_queue_fix_when_broker_url_is_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv('MAIA_BROKER_URL', 'amqp://guest:guest@127.0.0.1:6553/%2F')

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[2])['check'] == 'queue'
    assert parse_fields(lines[2])['status'] == 'fail'
    assert parse_fields(lines[-1]) == {
        'kind': 'summary',
        'status': 'fail',
        'failed': 'queue',
        'next_step': 'fix␠MAIA_BROKER_URL␠or␠the␠external␠RabbitMQ␠service⸴␠then␠run␠maia␠doctor␠again',
    }


def test_doctor_and_setup_handle_corrupt_state_db_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    state_db_path = get_state_db_path({'HOME': str(tmp_path)})
    state_db_path.parent.mkdir(parents=True, exist_ok=True)
    state_db_path.write_text('not a sqlite database', encoding='utf-8')

    doctor = run_module(tmp_path, 'doctor')
    assert doctor.returncode == 1
    assert doctor.stderr == ''
    doctor_lines = doctor.stdout.strip().splitlines()
    state_db_fields = parse_fields(doctor_lines[3])
    assert state_db_fields['check'] == 'state_db'
    assert state_db_fields['status'] == 'fail'
    assert state_db_fields['detail'].startswith('Maia␠state␠DB␠at␠')
    assert state_db_fields['detail'].endswith('␠is␠unreadable')
    assert state_db_fields['remediation'] == (
        'Repair␠or␠replace␠the␠local␠Maia␠state␠DB⸴␠then␠run␠maia␠doctor␠again'
    )

    setup = run_module(tmp_path, 'setup')
    assert setup.returncode == 1
    assert setup.stdout == ''
    assert 'error: Maia state DB at' in setup.stderr
    assert 'is unreadable' in setup.stderr
    assert 'Traceback' not in setup.stderr


def test_setup_bootstraps_shared_infra_and_makes_doctor_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    _write_fake_docker(fake_docker)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    setup = run_module(tmp_path, 'setup')

    assert setup.returncode == 0
    setup_lines = setup.stdout.strip().splitlines()
    assert setup_lines[0] == 'Created Maia network maia.'
    assert setup_lines[1] == 'Created Maia volume maia-rabbitmq-data.'
    assert setup_lines[2] == 'Started shared queue maia-rabbitmq.'
    assert setup_lines[3] == f'SQLite state is ready at {get_state_db_path({"HOME": str(tmp_path)})}.'
    assert setup_lines[4] == 'Shared infra is ready. Next: run maia agent new <name>.'
    assert setup.stderr == ''

    doctor = run_module(tmp_path, 'doctor')
    assert doctor.returncode == 0
    doctor_lines = doctor.stdout.strip().splitlines()
    assert parse_fields(doctor_lines[2]) == {
        'check': 'queue',
        'status': 'ok',
        'detail': 'RabbitMQ␠container␠maia-rabbitmq␠is␠running',
        'remediation': 'No␠action␠needed',
    }
    assert parse_fields(doctor_lines[3]) == {
        'check': 'state_db',
        'status': 'ok',
        'detail': str(get_state_db_path({'HOME': str(tmp_path)})),
        'remediation': 'No␠action␠needed',
    }
    assert parse_fields(doctor_lines[4]) == {
        'kind': 'summary',
        'status': 'ok',
        'failed': '-',
        'next_step': 'shared␠infra␠is␠ready',
    }


def test_doctor_reports_docker_permission_problem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    fake_docker = fake_bin / 'docker'
    fake_docker.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 'Docker version 27.0.0'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"compose\" ] && [ \"$2\" = \"version\" ]; then\n"
        "  echo 'Docker Compose version v2.29.0'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"info\" ]; then\n"
        "  echo 'permission denied while trying to connect to the Docker daemon socket' >&2\n"
        "  exit 1\n"
        "fi\n"
        "echo 'unsupported command' >&2\n"
        "exit 1\n",
        encoding='utf-8',
    )
    fake_docker.chmod(0o755)
    monkeypatch.setenv('PATH', f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    result = run_module(tmp_path, 'doctor')

    assert result.returncode == 1
    lines = result.stdout.strip().splitlines()
    assert parse_fields(lines[1]) == {
        'check': 'docker_daemon',
        'status': 'fail',
        'detail': 'Docker␠is␠installed⸴␠but␠this␠user␠cannot␠talk␠to␠the␠Docker␠daemon',
        'remediation': 'Start␠Docker␠and␠make␠sure␠your␠user␠has␠permission␠to␠use␠it',
    }
    assert parse_fields(lines[-1]) == {
        'kind': 'summary',
        'status': 'fail',
        'failed': 'docker_daemon,queue',
        'next_step': 'fix␠Docker␠permissions␠for␠this␠user⸴␠then␠run␠maia␠doctor␠again',
    }


def test_agent_new_list_status_and_tune_profile_metadata(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")

    listed = run_module(tmp_path, "agent", "list")
    assert listed.returncode == 0
    assert listed.stderr == ""
    assert listed.stdout.strip() == (
        f"agent_id={agent_id} name=demo call_sign=demo status=not-configured"
    )

    before = run_module(tmp_path, "agent", "status", agent_id)
    assert before.returncode == 0
    assert before.stderr == ""
    assert parse_fields(before.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "call_sign": "demo",
        "status": "not-configured",
        "setup": "not-started",
        "runtime": "stopped",
        "persona": "∅",
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
        "call_sign": "demo",
        "status": "not-configured",
        "setup": "not-started",
        "runtime": "stopped",
        "persona": "nightwatch",
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
                "setup_status": "configured",
                "runtime_spec": {
                    "image": "maia-local/hermes-worker:latest",
                    "workspace": "/opt/maia",
                    "command": [],
                    "env": {},
                },
            }
        ]
    }


def test_agent_status_reports_ready_after_runtime_configuration(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)
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

    listed = run_module(tmp_path, "agent", "list")
    assert listed.returncode == 0
    assert listed.stdout.strip() == (
        f"agent_id={agent_id} name=demo call_sign=demo status=ready"
    )

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "call_sign": "demo",
        "status": "ready",
        "setup": "complete",
        "runtime": "stopped",
        "persona": "∅",
    }


def test_agent_status_reports_running_after_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)
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

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "call_sign": "demo",
        "status": "running",
        "setup": "complete",
        "runtime": "running",
        "persona": "∅",
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
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "alpha",
        "call_sign": "alpha",
        "status": "not-configured",
        "setup": "not-started",
        "runtime": "stopped",
        "persona": "∅",
    }

    registry = load_registry(tmp_path)
    assert registry["agents"] == [
        {
            "agent_id": agent_id,
            "name": "alpha",
            "status": "stopped",
            "persona": "",
            "setup_status": "configured",
            "runtime_spec": {
                "image": "maia-local/hermes-worker:latest",
                "workspace": "/opt/maia",
                "command": [],
                "env": {},
            },
        }
    ]



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
        "call_sign": "demo",
        "status": "not-configured",
        "setup": "not-started",
        "runtime": "stopped",
        "persona": "research␠analyst↵",
    }


def test_agent_setup_passthrough_records_complete_setup_state(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_hermes = fake_bin / "hermes"
    _write_fake_hermes(fake_hermes)
    agent_id = create_agent(tmp_path, "planner")

    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["PYTHONPATH"] = str(SRC_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "maia", "agent", "setup", "planner"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    hermes_home = get_agent_hermes_home(agent_id, {"HOME": str(tmp_path)})
    assert f"hermes_home={hermes_home}" in result.stdout
    assert f"agent_id={agent_id}" in result.stdout
    assert "Agent setup completed for 'planner'" in result.stdout
    assert "run maia agent start planner" in result.stdout
    assert "maia agent start planner" in result.stdout
    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "planner",
        "call_sign": "planner",
        "status": "ready",
        "setup": "complete",
        "runtime": "stopped",
        "persona": "∅",
    }
    assert (hermes_home / "setup-marker.txt").read_text(encoding="utf-8") == "configured"
    assert load_runtime_state(tmp_path) == {
        "runtimes": [
            {
                "agent_id": agent_id,
                "runtime_status": "stopped",
                "setup_status": "complete",
            }
        ]
    }


def test_agent_setup_passthrough_records_incomplete_setup_state_on_failure(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_hermes = fake_bin / "hermes"
    _write_fake_hermes(fake_hermes)
    agent_id = create_agent(tmp_path, "planner")

    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["PYTHONPATH"] = str(SRC_ROOT)
    env["MAIA_FAKE_HERMES_FAIL"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "maia", "agent", "setup", "planner"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 7
    assert "fake-hermes-setup failed" in result.stderr
    assert "Agent setup failed for 'planner'" in result.stderr
    assert "maia agent setup planner" in result.stderr
    assert load_runtime_state(tmp_path) == {
        "runtimes": [
            {
                "agent_id": agent_id,
                "runtime_status": "stopped",
                "setup_status": "incomplete",
            }
        ]
    }


def test_agent_status_shows_setup_and_runtime_state_after_successful_setup(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_hermes = fake_bin / "hermes"
    _write_fake_hermes(fake_hermes)
    agent_id = create_agent(tmp_path, "planner")

    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["PYTHONPATH"] = str(SRC_ROOT)
    setup = subprocess.run(
        [sys.executable, "-m", "maia", "agent", "setup", "planner"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert setup.returncode == 0

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "planner",
        "call_sign": "planner",
        "status": "ready",
        "setup": "complete",
        "runtime": "stopped",
        "persona": "∅",
    }


def test_agent_logs_distinguish_setup_not_done_from_runtime_not_running(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "planner")
    no_setup_logs = run_module(tmp_path, "agent", "logs", agent_id)
    assert no_setup_logs.returncode == 1
    assert no_setup_logs.stderr.strip() == (
        f"error: Can't show logs for agent {agent_id!r} yet because agent setup is not complete"
    )

    write_runtime_state(
        tmp_path,
        {
            "runtimes": [
                {
                    "agent_id": agent_id,
                    "runtime_status": "stopped",
                    "setup_status": "complete",
                }
            ]
        },
    )
    runtime_not_running = run_module(tmp_path, "agent", "logs", agent_id)
    assert runtime_not_running.returncode == 1
    assert runtime_not_running.stderr.strip() == (
        f"error: Agent {agent_id!r} is not running right now"
    )


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
    cleared = run_module(tmp_path, "agent", "tune", agent_id, "--clear-runtime")
    assert cleared.returncode == 0

    shown = run_module(tmp_path, "workspace", "show", agent_id)

    assert shown.returncode == 1
    assert shown.stderr.strip() == (
        f"error: Can't show the workspace for agent {agent_id!r} yet because runtime setup is missing"
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
    write_registry(get_state_db_path({"HOME": str(tmp_path)}), registry)

    shown = run_module(tmp_path, "workspace", "show", agent_id)

    assert shown.returncode == 1
    assert shown.stderr.strip() == (
        f"error: Can't show the workspace for agent {agent_id!r} yet because the workspace path is missing"
    )


def test_agent_start_rejects_agent_without_runtime_spec(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")
    cleared = run_module(tmp_path, "agent", "tune", agent_id, "--clear-runtime")
    assert cleared.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)

    assert started.returncode == 1
    assert started.stderr.strip() == (
        f"error: Can't run agent {agent_id!r} yet because runtime setup is missing"
    )


def test_agent_start_rejects_agent_when_shared_infra_is_not_ready(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")
    SQLiteState(get_state_db_path({"HOME": str(tmp_path)})).set_infra_status(
        "bootstrap",
        status="failed",
        detail="shared infra bootstrap failed",
    )
    setup_state = load_runtime_state(tmp_path)
    setup_state["runtimes"] = [
        {
            "agent_id": agent_id,
            "runtime_status": "stopped",
            "setup_status": "complete",
        }
    ]
    write_runtime_state(tmp_path, setup_state)
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
        "--runtime-env",
        "MAIA_ENV=test",
    )
    assert tuned.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)

    assert started.returncode == 1
    assert started.stderr.strip() == (
        f"error: Can't run agent {agent_id!r} yet because shared infra setup is not complete"
    )


def test_agent_start_rejects_agent_when_agent_setup_is_not_complete(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")
    SQLiteState(get_state_db_path({"HOME": str(tmp_path)})).set_infra_status(
        "bootstrap",
        status="ready",
        detail="shared infra is ready",
    )
    setup_state = load_runtime_state(tmp_path)
    setup_state["runtimes"] = [
        {
            "agent_id": agent_id,
            "runtime_status": "stopped",
            "setup_status": "incomplete",
        }
    ]
    write_runtime_state(tmp_path, setup_state)
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
        "--runtime-env",
        "MAIA_ENV=test",
    )
    assert tuned.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)

    assert started.returncode == 1
    assert started.stderr.strip() == (
        f"error: Can't run agent {agent_id!r} yet because agent setup is incomplete"
    )


def test_agent_start_rejects_agent_with_missing_runtime_workspace(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "runtime-demo")
    registry = load_registry(tmp_path)
    registry["agents"][0]["runtime_spec"] = {
        "image": "ghcr.io/example/reviewer:latest",
        "workspace": "",
        "command": ["python", "-m", "reviewer"],
        "env": {"MAIA_ENV": "test"},
    }
    write_registry(get_state_db_path({"HOME": str(tmp_path)}), registry)

    started = run_module(tmp_path, "agent", "start", agent_id)

    assert started.returncode == 1
    assert started.stderr.strip() == (
        f"error: Can't run agent {agent_id!r} yet because the workspace path is missing"
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
    mark_runtime_start_ready(tmp_path, agent_id)
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
    assert started_again.stderr.strip() == (
        f"error: Agent '{agent_id}' is already running. Check its status or stop it first"
    )

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "call_sign": "demo",
        "status": "running",
        "setup": "complete",
        "runtime": "running",
        "persona": "∅",
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
    assert stopped_again.stderr.strip() == f"error: Agent '{agent_id}' is not running right now"

    logs_after_stop = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs_after_stop.returncode == 1
    assert logs_after_stop.stderr.strip() == f"error: Agent '{agent_id}' is not running right now"


def test_runtime_operator_smoke_flow_is_independent_from_collaboration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv("MAIA_BROKER_URL", raising=False)

    setup = run_module(tmp_path, "setup")
    assert setup.returncode == 0

    doctor = run_module(tmp_path, "doctor")
    assert doctor.returncode == 0

    agent_id = create_agent(tmp_path, "planner")
    mark_runtime_start_ready(tmp_path, agent_id)
    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
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
    assert tuned.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)
    assert started.returncode == 0
    status_running = run_module(tmp_path, "agent", "status", agent_id)
    assert status_running.returncode == 0
    assert parse_fields(status_running.stdout.strip())["status"] == "running"

    logs = run_module(tmp_path, "agent", "logs", agent_id, "--tail-lines", "2")
    assert logs.returncode == 0
    log_lines = logs.stdout.strip().splitlines()
    assert parse_fields(log_lines[0])["lines"] == "2"

    stopped = run_module(tmp_path, "agent", "stop", agent_id)
    assert stopped.returncode == 0
    status_stopped = run_module(tmp_path, "agent", "status", agent_id)
    assert status_stopped.returncode == 0
    assert parse_fields(status_stopped.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "planner",
        "call_sign": "planner",
        "status": "stopped",
        "setup": "complete",
        "runtime": "stopped",
        "persona": "∅",
    }


def test_live_host_runtime_checklist_flow_is_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv("MAIA_BROKER_URL", raising=False)

    setup = run_module(tmp_path, "setup")
    assert setup.returncode == 0

    doctor = run_module(tmp_path, "doctor")
    assert doctor.returncode == 0

    agent_id = create_agent(tmp_path, "smoke")
    mark_runtime_start_ready(tmp_path, agent_id)
    tuned = run_module(
        tmp_path,
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        "ghcr.io/example/smoke:latest",
        "--runtime-workspace",
        "/workspace/smoke",
        "--runtime-command",
        "python",
        "--runtime-command=-m",
        "--runtime-command",
        "smoke",
        "--runtime-env",
        "MAIA_ENV=test",
    )
    assert tuned.returncode == 0

    started = run_module(tmp_path, "agent", "start", agent_id)
    assert started.returncode == 0
    assert parse_fields(started.stdout.strip())["status"] == "running"

    status_running = run_module(tmp_path, "agent", "status", agent_id)
    assert status_running.returncode == 0
    assert parse_fields(status_running.stdout.strip())["status"] == "running"

    logs = run_module(tmp_path, "agent", "logs", agent_id, "--tail-lines", "1")
    assert logs.returncode == 0
    assert parse_fields(logs.stdout.strip().splitlines()[0])["runtime_status"] == "running"

    stopped = run_module(tmp_path, "agent", "stop", agent_id)
    assert stopped.returncode == 0
    assert parse_fields(stopped.stdout.strip())["status"] == "stopped"

    status_after_stop = run_module(tmp_path, "agent", "status", agent_id)
    assert status_after_stop.returncode == 0
    assert parse_fields(status_after_stop.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "smoke",
        "call_sign": "smoke",
        "status": "stopped",
        "setup": "complete",
        "runtime": "stopped",
        "persona": "∅",
    }


def test_agent_lifecycle_archive_restore_and_purge(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")
    cleared = run_module(tmp_path, "agent", "tune", agent_id, "--clear-runtime")
    assert cleared.returncode == 0

    start_without_runtime = run_module(tmp_path, "agent", "start", agent_id)
    assert start_without_runtime.returncode == 1
    assert start_without_runtime.stderr.strip() == (
        f"error: Can't run agent {agent_id!r} yet because runtime setup is missing"
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
    mark_runtime_start_ready(tmp_path, agent_id)
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
        "call_sign": "demo",
        "status": "running",
        "setup": "complete",
        "runtime": "running",
        "persona": "∅",
    }


def test_agent_status_syncs_registry_to_stopped_when_container_has_exited(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)
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

    fake_state_path = tmp_path / "bin" / "fake-docker-state.json"
    fake_state = json.loads(fake_state_path.read_text(encoding="utf-8"))
    fake_state["containers"]["runtime-001"]["status"] = "exited"
    fake_state_path.write_text(json.dumps(fake_state), encoding="utf-8")

    status = run_module(tmp_path, "agent", "status", agent_id)

    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": "demo",
        "call_sign": "demo",
        "status": "stopped",
        "setup": "complete",
        "runtime": "stopped",
        "persona": "∅",
    }
    assert load_registry(tmp_path)["agents"][0]["status"] == "stopped"


def test_agent_logs_syncs_registry_to_stopped_when_container_has_exited(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)
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

    fake_state_path = tmp_path / "bin" / "fake-docker-state.json"
    fake_state = json.loads(fake_state_path.read_text(encoding="utf-8"))
    fake_state["containers"]["runtime-001"]["status"] = "exited"
    fake_state_path.write_text(json.dumps(fake_state), encoding="utf-8")

    logs = run_module(tmp_path, "agent", "logs", agent_id, "--tail-lines", "1")

    assert logs.returncode == 0
    log_lines = logs.stdout.strip().splitlines()
    assert parse_fields(log_lines[0]) == {
        "agent_id": agent_id,
        "runtime_status": "stopped",
        "runtime_handle": "runtime-001",
        "lines": "1",
    }
    assert parse_fields(log_lines[1]) == {"line": "line␠2"}
    assert load_registry(tmp_path)["agents"][0]["status"] == "stopped"


def test_agent_start_recovers_when_registry_says_running_but_runtime_is_stopped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)
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

    runtime_state = load_runtime_state(tmp_path)
    runtime_state["runtimes"][0]["runtime_status"] = "stopped"
    write_runtime_state(tmp_path, runtime_state)

    registry = load_registry(tmp_path)
    registry["agents"][0]["status"] = "running"
    write_registry(get_state_db_path({"HOME": str(tmp_path)}), registry)

    restarted = run_module(tmp_path, "agent", "start", agent_id)

    assert restarted.returncode == 0
    assert parse_fields(restarted.stdout.strip()) == {
        "agent_id": agent_id,
        "status": "running",
        "runtime_status": "running",
        "runtime_handle": "runtime-002",
    }
    assert load_registry(tmp_path)["agents"][0]["status"] == "running"


def test_runtime_commands_require_active_runtime_state(tmp_path: Path) -> None:
    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)

    stopped = run_module(tmp_path, "agent", "stop", agent_id)
    assert stopped.returncode == 1
    assert stopped.stderr.strip() == f"error: Agent '{agent_id}' is not running right now"

    logs = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs.returncode == 1
    assert logs.stderr.strip() == f"error: Agent '{agent_id}' is not running right now"



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
    mark_runtime_start_ready(tmp_path, agent_id)
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
        f"error: Maia found an old saved runtime record for agent '{agent_id}', but the container is gone. The saved record was cleared. Start the agent again if you still need it"
    )
    assert load_runtime_state(tmp_path) == {
        "runtimes": [
            {
                "agent_id": agent_id,
                "runtime_status": "stopped",
                "setup_status": "complete",
            }
        ]
    }

    status_after = run_module(tmp_path, "agent", "status", agent_id)
    assert status_after.returncode == 0
    assert parse_fields(status_after.stdout.strip())["status"] == "stopped"

    started_again = run_module(tmp_path, "agent", "start", agent_id)
    assert started_again.returncode == 0
    (tmp_path / "bin" / "fake-docker-state.json").unlink()

    logs = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs.returncode == 1
    assert logs.stderr.strip() == (
        f"error: Maia found an old saved runtime record for agent '{agent_id}', but the container is gone. The saved record was cleared. Start the agent again if you still need it"
    )
    assert load_runtime_state(tmp_path) == {
        "runtimes": [
            {
                "agent_id": agent_id,
                "runtime_status": "stopped",
                "setup_status": "complete",
            }
        ]
    }


def test_runtime_commands_reject_running_agent_with_missing_runtime_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    agent_id = create_agent(tmp_path, "demo")
    mark_runtime_start_ready(tmp_path, agent_id)
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
    write_runtime_state(tmp_path, {"runtimes": []})

    expected_error = (
        f"error: Maia can't find its saved runtime record for agent {agent_id!r}. Check Docker manually, then start the agent again if needed"
    )

    status = run_module(tmp_path, "agent", "status", agent_id)
    assert status.returncode == 1
    assert status.stderr.strip() == expected_error

    stop = run_module(tmp_path, "agent", "stop", agent_id)
    assert stop.returncode == 1
    assert stop.stderr.strip() == expected_error

    logs = run_module(tmp_path, "agent", "logs", agent_id)
    assert logs.returncode == 1
    assert logs.stderr.strip() == expected_error

    started_again = run_module(tmp_path, "agent", "start", agent_id)
    assert started_again.returncode == 1
    assert started_again.stderr.strip() == expected_error


def test_recovery_message_points_operator_back_to_doctor_when_start_cannot_run(
    tmp_path: Path,
) -> None:
    agent_id = create_agent(tmp_path, "demo")

    started = run_module(tmp_path, "agent", "start", agent_id)

    assert started.returncode == 1
    assert started.stderr.strip() == (
        f"error: Can't run agent {agent_id!r} yet because shared infra setup is not complete"
    )


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
    mark_runtime_start_ready(tmp_path, agent_id)
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
    mark_runtime_start_ready(dest_home, dest_agent)
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



def test_import_clears_runtime_state_even_for_surviving_agent_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    home = tmp_path / "same-id"
    agent_id = create_agent(home, "planner")

    tuned = run_module(
        home,
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
    mark_runtime_start_ready(home, agent_id)
    started = run_module(home, "agent", "start", agent_id)
    assert started.returncode == 0
    assert load_runtime_state(home)["runtimes"]

    incoming_registry_path = home / "incoming.json"
    incoming_registry_path.write_text(
        json.dumps(
            {
                "agents": [
                    {
                        "agent_id": agent_id,
                        "name": "planner",
                        "status": "stopped",
                        "persona": "",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    imported = run_module(home, "import", str(incoming_registry_path), "--yes")
    assert imported.returncode == 0
    assert load_runtime_state(home) == {"runtimes": []}



def test_send_inbox_thread_and_reply_flow(tmp_path: Path) -> None:
    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")

    sent = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please review the latest patch",
        "--topic",
        "review handoff",
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
    assert inbox_message["body"] == "please␠review␠the␠latest␠patch"
    assert inbox_message["reply_to_message_id"] == "-"

    thread_created_at = load_collaboration(tmp_path)["threads"][0]["created_at"]
    thread = run_module(tmp_path, "thread", thread_id)
    assert thread.returncode == 0
    thread_lines = thread.stdout.strip().splitlines()
    assert parse_fields(thread_lines[0]) == {
        "thread_id": thread_id,
        "topic": "review␠handoff",
        "participants": f"{planner_id},{reviewer_id}",
        "participant_runtime": f"{planner_id}:stopped,{reviewer_id}:stopped",
        "created_by": planner_id,
        "status": "open",
        "updated_at": thread_created_at,
        "pending_on": reviewer_id,
        "delegated_to": reviewer_id,
        "delegation_status": "pending",
        "current_thread_id": thread_id,
        "latest_internal_update": f"{planner_id}␠request:␠please␠review␠the␠latest␠patch",
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


def test_running_agent_multi_turn_conversation_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    fake_hermes = fake_bin / "hermes"
    _write_fake_hermes(fake_hermes)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    assert run_module(tmp_path, "setup").returncode == 0
    assert run_module(tmp_path, "doctor").returncode == 0

    planner_id = create_agent(tmp_path, "planner")
    reviewer_id = create_agent(tmp_path, "reviewer")
    assert run_module(tmp_path, "agent", "setup", planner_id).returncode == 0
    assert run_module(tmp_path, "agent", "setup", reviewer_id).returncode == 0

    assert run_module(
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
    ).returncode == 0
    assert run_module(
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
    ).returncode == 0

    assert run_module(tmp_path, "agent", "start", planner_id).returncode == 0
    assert run_module(tmp_path, "agent", "start", reviewer_id).returncode == 0

    sent = run_module(
        tmp_path,
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please review the latest patch",
        "--topic",
        "review handoff",
        "--kind",
        "request",
    )
    assert sent.returncode == 0
    sent_fields = parse_fields(sent.stdout.strip())
    thread_id = sent_fields["thread_id"]
    first_message_id = sent_fields["message_id"]
    sent_created_at = load_collaboration(tmp_path)["messages"][0]["created_at"]

    reviewer_inbox = run_module(tmp_path, "inbox", reviewer_id)
    assert reviewer_inbox.returncode == 0
    reviewer_lines = reviewer_inbox.stdout.strip().splitlines()
    assert parse_fields(reviewer_lines[0]) == {
        "agent_id": reviewer_id,
        "messages": "1",
    }
    assert parse_fields(reviewer_lines[1]) == {
        "message_id": first_message_id,
        "thread_id": thread_id,
        "from_agent": planner_id,
        "to_agent": reviewer_id,
        "kind": "request",
        "body": "please␠review␠the␠latest␠patch",
        "created_at": sent_created_at,
        "reply_to_message_id": "-",
    }

    replied = run_module(
        tmp_path,
        "reply",
        first_message_id,
        "--from-agent",
        reviewer_id,
        "--body",
        "review complete",
        "--kind",
        "answer",
    )
    assert replied.returncode == 0
    reply_fields = parse_fields(replied.stdout.strip())
    assert reply_fields["kind"] == "answer"
    reply_message_id = reply_fields["message_id"]
    collaboration = load_collaboration(tmp_path)
    sent_created_at = collaboration["messages"][0]["created_at"]
    reply_created_at = collaboration["messages"][1]["created_at"]

    planner_inbox = run_module(tmp_path, "inbox", planner_id)
    assert planner_inbox.returncode == 0
    planner_lines = planner_inbox.stdout.strip().splitlines()
    assert parse_fields(planner_lines[0]) == {
        "agent_id": planner_id,
        "messages": "1",
    }
    assert parse_fields(planner_lines[1]) == {
        "message_id": reply_message_id,
        "thread_id": thread_id,
        "from_agent": reviewer_id,
        "to_agent": planner_id,
        "kind": "answer",
        "body": "review␠complete",
        "created_at": reply_created_at,
        "reply_to_message_id": first_message_id,
    }

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
    added_fields = parse_fields(added.stdout.strip())
    handoff_id = added_fields["handoff_id"]

    thread_show = run_module(tmp_path, "thread", "show", thread_id)
    assert thread_show.returncode == 0
    thread_lines = thread_show.stdout.strip().splitlines()
    assert parse_fields(thread_lines[0]) == {
        "thread_id": thread_id,
        "topic": "review␠handoff",
        "participants": f"{planner_id},{reviewer_id}",
        "participant_runtime": f"{planner_id}:running,{reviewer_id}:running",
        "status": "open",
        "updated_at": reply_created_at,
        "pending_on": planner_id,
        "delegated_to": reviewer_id,
        "delegation_status": "handoff_ready",
        "current_thread_id": thread_id,
        "latest_internal_update": f"{reviewer_id}␠report:␠Review␠notes␠ready",
        "handoffs": "1",
        "messages": "2",
        "created_by": planner_id,
        "created_at": sent_created_at,
        "recent_handoff_id": handoff_id,
        "recent_handoff_from": reviewer_id,
        "recent_handoff_to": planner_id,
        "recent_handoff_type": "report",
        "recent_handoff_location": "reports/review.md",
        "recent_handoff_summary": "Review␠notes␠ready",
        "recent_handoff_created_at": added_fields["created_at"],
    }

    planner_status = run_module(tmp_path, "agent", "status", planner_id)
    reviewer_status = run_module(tmp_path, "agent", "status", reviewer_id)
    assert planner_status.returncode == 0
    assert reviewer_status.returncode == 0
    assert parse_fields(planner_status.stdout.strip())["runtime"] == "running"
    assert parse_fields(reviewer_status.stdout.strip())["runtime"] == "running"

    planner_logs = run_module(tmp_path, "agent", "logs", planner_id, "--tail-lines", "2")
    reviewer_logs = run_module(tmp_path, "agent", "logs", reviewer_id, "--tail-lines", "2")
    assert planner_logs.returncode == 0
    assert reviewer_logs.returncode == 0
    assert parse_fields(planner_logs.stdout.strip().splitlines()[0]) == {
        "agent_id": planner_id,
        "runtime_status": "running",
        "runtime_handle": "runtime-001",
        "lines": "2",
    }
    assert parse_fields(reviewer_logs.stdout.strip().splitlines()[0]) == {
        "agent_id": reviewer_id,
        "runtime_status": "running",
        "runtime_handle": "runtime-002",
        "lines": "2",
    }


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
        "delegated_to": reviewer_id,
        "delegation_status": "handoff_ready",
        "current_thread_id": thread_id,
        "latest_internal_update": f"{reviewer_id}␠report:␠Review␠notes␠ready",
        "handoffs": "1",
        "messages": "2",
        "recent_handoff_id": flow["handoff_id"],
        "recent_handoff_to": planner_id,
        "recent_handoff_type": "report",
        "recent_handoff_summary": "Review␠notes␠ready",
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
        "delegated_to": reviewer_id,
        "delegation_status": "handoff_ready",
        "current_thread_id": thread_id,
        "latest_internal_update": f"{reviewer_id}␠report:␠Review␠notes␠ready",
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
        "workspace": "/opt/maia",
        "runtime_image": "maia-local/hermes-worker:latest",
        "runtime_command": "-",
        "runtime_env_keys": "-",
    }
    assert parse_fields(handoff_lines[2]) == {
        "handoff_role": "target",
        "agent_id": planner_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/opt/maia",
        "runtime_image": "maia-local/hermes-worker:latest",
        "runtime_command": "-",
        "runtime_env_keys": "-",
    }

    workspace = run_module(tmp_path, "workspace", "show", planner_id)
    assert workspace.returncode == 0
    assert parse_fields(workspace.stdout.strip()) == {
        "agent_id": planner_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/opt/maia",
        "runtime_image": "maia-local/hermes-worker:latest",
        "runtime_command": "-",
        "runtime_env_keys": "-",
    }

    status = run_module(tmp_path, "agent", "status", planner_id)
    assert status.returncode == 0
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": planner_id,
        "name": "planner",
        "call_sign": "planner",
        "status": "running",
        "setup": "complete",
        "runtime": "running",
        "persona": "∅",
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


def test_live_runtime_delegation_loop_stays_on_anchor_thread_in_current_maia_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_fake_docker(fake_docker)
    fake_hermes = fake_bin / "hermes"
    _write_fake_hermes(fake_hermes)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    assert run_module(tmp_path, "setup").returncode == 0
    assert run_module(tmp_path, "doctor").returncode == 0

    anchor_id = create_agent(tmp_path, "economist")
    delegate_id = create_agent(tmp_path, "tech")
    assert run_module(tmp_path, "agent", "setup", anchor_id).returncode == 0
    assert run_module(tmp_path, "agent", "setup", delegate_id).returncode == 0
    assert run_module(tmp_path, "agent", "start", anchor_id).returncode == 0
    assert run_module(tmp_path, "agent", "start", delegate_id).returncode == 0

    delegated_request = run_module(
        tmp_path,
        "send",
        anchor_id,
        delegate_id,
        "--body",
        "Please build the crawler and tell me what input format you still need.",
        "--topic",
        "crawler delegation",
    )
    assert delegated_request.returncode == 0
    delegated_request_fields = parse_fields(delegated_request.stdout.strip())
    thread_id = delegated_request_fields["thread_id"]
    delegated_request_id = delegated_request_fields["message_id"]

    delegate_question = run_module(
        tmp_path,
        "send",
        delegate_id,
        anchor_id,
        "--body",
        "Which site should I target and what output schema do you want?",
        "--thread-id",
        thread_id,
        "--kind",
        "question",
    )
    assert delegate_question.returncode == 0
    delegate_question_fields = parse_fields(delegate_question.stdout.strip())
    delegate_question_id = delegate_question_fields["message_id"]

    thread_after_question = run_module(tmp_path, "thread", "show", thread_id)
    assert thread_after_question.returncode == 0
    question_lines = thread_after_question.stdout.strip().splitlines()
    assert parse_fields(question_lines[0])["created_by"] == anchor_id
    assert parse_fields(question_lines[0])["current_thread_id"] == thread_id
    assert parse_fields(question_lines[0])["delegated_to"] == delegate_id
    assert parse_fields(question_lines[0])["delegation_status"] == "needs_user_input"
    assert parse_fields(question_lines[0])["latest_internal_update"] == (
        f"{delegate_id}␠question:␠Which␠site␠should␠I␠target␠and␠what␠output␠sche…"
    )
    assert parse_fields(question_lines[2]) == {
        "message_id": delegate_question_id,
        "thread_id": thread_id,
        "from_agent": delegate_id,
        "to_agent": anchor_id,
        "kind": "question",
        "body": "Which␠site␠should␠I␠target␠and␠what␠output␠schema␠do␠you␠want?",
        "created_at": parse_fields(question_lines[2])["created_at"],
        "reply_to_message_id": "-",
    }

    anchor_answer = run_module(
        tmp_path,
        "reply",
        delegate_question_id,
        "--from-agent",
        anchor_id,
        "--body",
        "Target example.com and emit JSONL with title,url,summary.",
    )
    assert anchor_answer.returncode == 0
    anchor_answer_fields = parse_fields(anchor_answer.stdout.strip())
    anchor_answer_id = anchor_answer_fields["message_id"]
    assert anchor_answer_fields["thread_id"] == thread_id
    assert anchor_answer_fields["reply_to_message_id"] == delegate_question_id
    assert anchor_answer_fields["delegation_status"] == "answered"
    assert anchor_answer_fields["current_thread_id"] == thread_id

    delegate_report = run_module(
        tmp_path,
        "reply",
        anchor_answer_id,
        "--from-agent",
        delegate_id,
        "--body",
        "Crawler is running; initial scrape looks clean.",
        "--kind",
        "report",
    )
    assert delegate_report.returncode == 0
    delegate_report_fields = parse_fields(delegate_report.stdout.strip())
    delegate_report_id = delegate_report_fields["message_id"]
    assert delegate_report_fields["thread_id"] == thread_id
    assert delegate_report_fields["reply_to_message_id"] == anchor_answer_id
    assert delegate_report_fields["delegation_status"] == "answered"
    assert delegate_report_fields["current_thread_id"] == thread_id

    final_handoff = run_module(
        tmp_path,
        "handoff",
        "add",
        "--thread-id",
        thread_id,
        "--from-agent",
        delegate_id,
        "--to-agent",
        anchor_id,
        "--type",
        "report",
        "--location",
        "artifacts/crawler.jsonl",
        "--summary",
        "Crawler output ready for the anchor reply",
    )
    assert final_handoff.returncode == 0
    final_handoff_fields = parse_fields(final_handoff.stdout.strip())

    collaboration = load_collaboration(tmp_path)
    message_created_at = {
        message["message_id"]: message["created_at"]
        for message in collaboration["messages"]
    }

    thread_show = run_module(tmp_path, "thread", "show", thread_id)
    assert thread_show.returncode == 0
    thread_lines = thread_show.stdout.strip().splitlines()
    assert parse_fields(thread_lines[0]) == {
        "thread_id": thread_id,
        "topic": "crawler␠delegation",
        "participants": f"{anchor_id},{delegate_id}",
        "participant_runtime": f"{anchor_id}:running,{delegate_id}:running",
        "status": "open",
        "updated_at": message_created_at[delegate_report_id],
        "pending_on": anchor_id,
        "delegated_to": delegate_id,
        "delegation_status": "handoff_ready",
        "current_thread_id": thread_id,
        "latest_internal_update": f"{delegate_id}␠report:␠Crawler␠output␠ready␠for␠the␠anchor␠reply",
        "handoffs": "1",
        "messages": "4",
        "created_by": anchor_id,
        "created_at": message_created_at[delegated_request_id],
        "recent_handoff_id": final_handoff_fields["handoff_id"],
        "recent_handoff_from": delegate_id,
        "recent_handoff_to": anchor_id,
        "recent_handoff_type": "report",
        "recent_handoff_location": "artifacts/crawler.jsonl",
        "recent_handoff_summary": "Crawler␠output␠ready␠for␠the␠anchor␠reply",
        "recent_handoff_created_at": final_handoff_fields["created_at"],
    }
    assert parse_fields(thread_lines[1]) == {
        "message_id": delegated_request_id,
        "thread_id": thread_id,
        "from_agent": anchor_id,
        "to_agent": delegate_id,
        "kind": "request",
        "body": "Please␠build␠the␠crawler␠and␠tell␠me␠what␠input␠format␠you␠still␠need.",
        "created_at": message_created_at[delegated_request_id],
        "reply_to_message_id": "-",
    }
    assert parse_fields(thread_lines[2]) == {
        "message_id": delegate_question_id,
        "thread_id": thread_id,
        "from_agent": delegate_id,
        "to_agent": anchor_id,
        "kind": "question",
        "body": "Which␠site␠should␠I␠target␠and␠what␠output␠schema␠do␠you␠want?",
        "created_at": message_created_at[delegate_question_id],
        "reply_to_message_id": "-",
    }
    assert parse_fields(thread_lines[3]) == {
        "message_id": anchor_answer_id,
        "thread_id": thread_id,
        "from_agent": anchor_id,
        "to_agent": delegate_id,
        "kind": "answer",
        "body": "Target␠example.com␠and␠emit␠JSONL␠with␠title⸴url⸴summary.",
        "created_at": message_created_at[anchor_answer_id],
        "reply_to_message_id": delegate_question_id,
    }
    assert parse_fields(thread_lines[4]) == {
        "message_id": delegate_report_id,
        "thread_id": thread_id,
        "from_agent": delegate_id,
        "to_agent": anchor_id,
        "kind": "report",
        "body": "Crawler␠is␠running;␠initial␠scrape␠looks␠clean.",
        "created_at": message_created_at[delegate_report_id],
        "reply_to_message_id": anchor_answer_id,
    }

    handoff_show = run_module(tmp_path, "handoff", "show", final_handoff_fields["handoff_id"])
    assert handoff_show.returncode == 0
    handoff_lines = handoff_show.stdout.strip().splitlines()
    assert parse_fields(handoff_lines[0]) == {
        "handoff_id": final_handoff_fields["handoff_id"],
        "thread_id": thread_id,
        "from_agent": delegate_id,
        "to_agent": anchor_id,
        "type": "report",
        "location": "artifacts/crawler.jsonl",
        "summary": "Crawler␠output␠ready␠for␠the␠anchor␠reply",
        "created_at": final_handoff_fields["created_at"],
    }


def test_v1_golden_flow_visibility_path_closes_part2_operator_story(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)

    commands = [
        ("thread", "list", "--status", "open"),
        ("thread", "show", flow["thread_id"]),
        ("handoff", "show", flow["handoff_id"]),
        ("workspace", "show", flow["planner_id"]),
        ("agent", "status", flow["planner_id"]),
        ("agent", "logs", flow["planner_id"], "--tail-lines", "2"),
    ]
    outputs = [run_module(tmp_path, *command) for command in commands]

    assert [result.returncode for result in outputs] == [0, 0, 0, 0, 0, 0]
    assert outputs[0].stdout.startswith("thread ")
    assert outputs[1].stdout.startswith("thread ")
    assert outputs[2].stdout.startswith("handoff_id=")
    assert outputs[3].stdout.startswith("workspace ")
    assert outputs[4].stdout.startswith("agent_id=")
    assert outputs[5].stdout.startswith("logs ")


def test_v1_golden_flow_reports_malformed_runtime_state_at_status_and_logs_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)
    runtime_state_path = get_state_db_path({"HOME": str(tmp_path)})
    corrupt_sqlite_payload(
        runtime_state_path,
        "runtime_states",
        "agent_id",
        flow["planner_id"],
        "{bad json\n",
    )
    expected_error = (
        f"error: Invalid runtime state SQLite in {runtime_state_path}: "
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
        f"error: Maia found an old saved runtime record for agent '{flow['planner_id']}', "
        "but the container is gone. The saved record was cleared. Start the agent again if you still need it"
    )
    remaining_after_status = load_runtime_state(tmp_path)
    assert {
        runtime["agent_id"] for runtime in remaining_after_status["runtimes"]
    } == {flow["planner_id"], flow["reviewer_id"]}

    logs = run_module(tmp_path, "agent", "logs", flow["reviewer_id"])
    assert logs.returncode == 1
    assert logs.stderr.strip() == (
        f"error: Maia found an old saved runtime record for agent '{flow['reviewer_id']}', "
        "but the container is gone. The saved record was cleared. Start the agent again if you still need it"
    )
    assert {
        (
            runtime["agent_id"],
            runtime["runtime_status"],
            runtime["setup_status"],
        )
        for runtime in load_runtime_state(tmp_path)["runtimes"]
    } == {
        (flow["planner_id"], "stopped", "complete"),
        (flow["reviewer_id"], "stopped", "complete"),
    }


def test_v1_golden_flow_reports_malformed_collaboration_state_at_thread_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow = _setup_v1_golden_flow(tmp_path, monkeypatch)
    collaboration_path = get_state_db_path({"HOME": str(tmp_path)})
    corrupt_sqlite_payload(
        collaboration_path,
        "collaboration_threads",
        "thread_id",
        flow["thread_id"],
        "{bad json\n",
    )
    expected_error = (
        f"error: Invalid collaboration SQLite in {collaboration_path}: "
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
        "review handoff",
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
        get_state_db_path({"HOME": str(dest_home)}),
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
        "call_sign": "demo",
        "status": "not-configured",
        "setup": "not-started",
        "runtime": "stopped",
        "persona": "analyst",
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
        get_state_db_path({"HOME": str(dest_home)}),
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
    assert parse_fields(status.stdout.strip()) == {
        "agent_id": agent_id,
        "name": f"legacy-{scope_version}",
        "call_sign": f"legacy-{scope_version}",
        "status": "not-configured",
        "setup": "not-started",
        "runtime": "stopped",
        "persona": "∅",
    }

    registry = load_registry(dest_home)
    assert registry["agents"] == [
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
