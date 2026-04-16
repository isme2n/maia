from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from maia.app_state import (
    get_collaboration_path,
    get_runtime_state_path,
    get_state_db_path,
)
from maia.broker import BrokerAckResult, BrokerDeliveryStatus, BrokerMessageEnvelope, BrokerPullResult, BrokerPublishResult
from maia.cli import main
from maia import cli as cli_module
from maia.cli_parser import (
    AGENT_SETUP_EXAMPLES,
    AGENT_TUNE_EXAMPLES,
    DOCTOR_EXAMPLES,
    EXPORT_EXAMPLES,
    GOLDEN_FLOW_SMOKE_CONTRACT,
    HANDOFF_EXAMPLES,
    HOST_VALIDATION_CHECKLIST,
    HOST_VALIDATION_REPORT_TEMPLATE,
    IMPORT_EXAMPLES,
    INSPECT_EXAMPLES,
    KNOWN_LIMITATIONS,
    PART1_OPERATOR_FLOW,
    QUICKSTART_EXAMPLES,
    RUNTIME_PREREQ_EXAMPLES,
    RUNTIME_RECOVERY_CHECKLIST,
    RUNTIME_SUPPORT_BOUNDARY,
    SETUP_EXAMPLES,
    TEAM_SHOW_EXAMPLES,
    TEAM_UPDATE_EXAMPLES,
    THREAD_EXAMPLES,
    V1_RELEASE_CHECKLIST,
    WORKSPACE_EXAMPLES,
    build_parser,
)
from maia.collaboration_storage import CollaborationStorage
from maia.handoff_model import HandoffKind, HandoffRecord
from maia.message_model import MessageKind, MessageRecord, ThreadRecord
from maia.runtime_state_storage import RuntimeStateStorage

README_PATH = REPO_ROOT / "README.md"
PRD_PATH = REPO_ROOT / "docs/prd/maia-core-product.md"
PHASE10_PLAN_PATH = REPO_ROOT / "docs/plans/phase10-release-hardening-and-v1-closeout.md"
PHASE12_PLAN_PATH = REPO_ROOT / "docs/plans/phase12-live-runtime-readiness-and-host-validation.md"
PHASE15_PLAN_PATH = REPO_ROOT / "docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md"


def _parse_fields(line: str) -> dict[str, str]:
    tokens = line.split()
    if tokens and tokens[0] in {"added", "created", "sent", "replied", "inbox", "message_id", "thread", "workspace"}:
        tokens = tokens[1:]
    return dict(token.split("=", 1) for token in tokens)


class FakeMessageBroker:
    def __init__(self) -> None:
        self.published: list[MessageRecord] = []
        self.pull_result = BrokerPullResult(status=BrokerDeliveryStatus.EMPTY)
        self.publish_error: Exception | None = None
        self.acked: list[BrokerMessageEnvelope] = []
        self.ack_error: Exception | None = None
        self.closed = False

    def publish(self, message: MessageRecord) -> BrokerPublishResult:
        if self.publish_error is not None:
            raise self.publish_error
        self.published.append(message)
        return BrokerPublishResult(
            status=BrokerDeliveryStatus.QUEUED,
            message_id=message.message_id,
        )

    def pull(self, *, agent_id: str, limit: int = 1) -> BrokerPullResult:
        assert isinstance(agent_id, str)
        assert isinstance(limit, int)
        return self.pull_result

    def ack(self, envelope: BrokerMessageEnvelope) -> BrokerAckResult:
        if self.ack_error is not None:
            raise self.ack_error
        self.acked.append(envelope)
        return BrokerAckResult(
            status=BrokerDeliveryStatus.ACKNOWLEDGED,
            message_id=envelope.message.message_id,
            receipt_handle=envelope.receipt_handle,
        )

    def close(self) -> None:
        self.closed = True


def _assert_contains_lines(text: str, lines: tuple[str, ...]) -> None:
    for line in lines:
        assert line in text


def test_readme_locks_part1_public_flow() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    assert "maia doctor" in text
    assert "maia setup" in text
    assert "maia agent new planner" in text
    assert "maia agent setup planner" in text
    assert "maia agent start planner" in text
    assert "maia agent stop planner" in text
    assert "shared infra" in text.lower()
    assert "hermes setup" in text
    assert "send/reply/inbox/thread" not in text
    assert "CLI messenger" not in text


def test_prd_locks_part1_operator_story() -> None:
    text = PRD_PATH.read_text(encoding="utf-8")

    assert "doctor → setup → agent new → agent setup → agent start" in text
    assert "identity" in text.lower()
    assert "hermes setup" in text
    assert "send/reply" not in text


def test_phase15_task102_matches_part1_contract() -> None:
    text = PHASE15_PLAN_PATH.read_text(encoding="utf-8")

    assert "doctor → setup → agent new → agent setup → agent start" in text
    assert "Only infra readiness; no Hermes login/API key/provider checks." in text
    assert "No team defaults, no model policy wizard." in text
    assert "agent setup" in text
def test_sqlite_control_plane_path_defaults_under_maia_home(tmp_path: Path) -> None:
    assert get_state_db_path({"HOME": str(tmp_path)}) == tmp_path / ".maia" / "state.db"


def test_top_level_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia" in captured.out
    assert "agent" in captured.out
    assert "team" in captured.out
    assert "doctor" in captured.out
    assert "setup" in captured.out
    assert "send" in captured.out
    assert "inbox" in captured.out
    assert "thread" in captured.out
    assert "reply" in captured.out
    assert "handoff" in captured.out
    assert "workspace" in captured.out
    assert "artifact" not in captured.out
    assert "Export Maia portable state" in captured.out
    assert "Import Maia portable state safely" in captured.out
    assert "Inspect an importable Maia snapshot" in captured.out
    assert "Check shared infra readiness" in captured.out
    assert "Bootstrap shared Maia infra" in captured.out
    assert "Part 1 operator flow:" in captured.out
    assert "Known limitations:" in captured.out
    assert "Quickstart (local state only):" not in captured.out
    assert "V1 smoke checklist:" not in captured.out
    assert "send <" not in captured.out
    assert "reply <" not in captured.out
    assert "thread show" not in captured.out
    _assert_contains_lines(captured.out, PART1_OPERATOR_FLOW)
    _assert_contains_lines(captured.out, KNOWN_LIMITATIONS)


def test_agent_new_help_describes_identity_only_flow(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "new", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Create an agent identity" in captured.out
    assert "Agent name" in captured.out
    assert "provider" not in captured.out
    assert "model" not in captured.out
    assert "runtime image" not in captured.out
    assert "login" not in captured.out


def test_agent_setup_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "setup", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Open hermes setup for an agent" in captured.out
    assert "hermes setup" in captured.out
    assert "provider" not in captured.out
    assert "runtime image" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, AGENT_SETUP_EXAMPLES)


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
        ["send", "planner", "reviewer", "--body", "hello", "--topic", "review handoff"]
    )

    assert args.resource == "send"
    assert args.from_agent == "planner"
    assert args.to_agent == "reviewer"
    assert args.body == "hello"
    assert args.topic == "review handoff"
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


def test_build_parser_thread_list_shape() -> None:
    args = build_parser().parse_args(["thread", "list", "--agent", "reviewer", "--status", "open"])

    assert args.resource == "thread"
    assert args.thread_command == "list"
    assert args.agent == "reviewer"
    assert args.status == "open"


def test_build_parser_thread_show_shape() -> None:
    args = build_parser().parse_args(["thread", "show", "thread1234", "--limit", "10"])

    assert args.resource == "thread"
    assert args.thread_command == "show"
    assert args.thread_id == "thread1234"
    assert args.limit == 10


def test_build_parser_workspace_show_shape() -> None:
    args = build_parser().parse_args(["workspace", "show", "reviewer1234"])

    assert args.resource == "workspace"
    assert args.workspace_command == "show"
    assert args.agent_id == "reviewer1234"


def test_build_parser_setup_shape() -> None:
    args = build_parser().parse_args(["setup"])

    assert args.resource == "setup"


def test_build_parser_agent_setup_shape() -> None:
    args = build_parser().parse_args(["agent", "setup", "planner"])

    assert args.resource == "agent"
    assert args.agent_command == "setup"
    assert args.agent_id == "planner"


def test_thread_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["thread", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia thread" in captured.out
    assert "recent handoff pointers" in captured.out
    assert "participant runtime summaries" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, THREAD_EXAMPLES)


def test_workspace_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["workspace", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia workspace" in captured.out
    assert "handoff participant" in captured.out
    assert "show" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, WORKSPACE_EXAMPLES)


def test_build_parser_handoff_add_shape() -> None:
    args = build_parser().parse_args(
        [
            "handoff",
            "add",
            "--thread-id",
            "thread1234",
            "--from-agent",
            "planner",
            "--to-agent",
            "reviewer",
            "--type",
            "report",
            "--location",
            "reports/review.md",
            "--summary",
            "Review notes ready",
        ]
    )

    assert args.resource == "handoff"
    assert args.handoff_command == "add"
    assert args.thread_id == "thread1234"
    assert args.from_agent == "planner"
    assert args.to_agent == "reviewer"
    assert args.type == "report"
    assert args.location == "reports/review.md"
    assert args.summary == "Review notes ready"


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
    assert "Check shared infra readiness" in captured.out
    assert "Docker" in captured.out
    assert "queue" in captured.out
    assert "DB" in captured.out
    assert "provider" not in captured.out
    assert "login" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, DOCTOR_EXAMPLES)
    assert "doctor" in captured.out


def test_setup_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["setup", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Bootstrap shared Maia infra" in captured.out
    assert "Docker" in captured.out
    assert "queue" in captured.out
    assert "DB" in captured.out
    assert "team defaults" not in captured.out
    assert "model defaults" not in captured.out
    assert "wizard" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, SETUP_EXAMPLES)


def test_setup_command_fails_cleanly_until_task104(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["setup"]) == 1
    captured = capsys.readouterr()
    assert "Shared infra bootstrap is not implemented yet" in captured.err
    assert "Task 104" in captured.err


def test_agent_setup_command_fails_cleanly_until_task106(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _create_agent(monkeypatch, capsys, tmp_path, "planner")
    capsys.readouterr()

    assert main(["agent", "setup", "planner"]) == 1
    captured = capsys.readouterr()
    assert "Agent setup for" in captured.err
    assert "is not implemented yet" in captured.err
    assert "Task 106" in captured.err


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
    _assert_contains_lines(captured.out, IMPORT_EXAMPLES)


def test_inspect_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Read a .maia bundle, manifest.json" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, INSPECT_EXAMPLES)


def test_export_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["export", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Write a Maia bundle (.maia) or raw registry snapshot" in captured.out
    assert "path" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, EXPORT_EXAMPLES)


def test_team_show_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["team", "show", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia team show" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, TEAM_SHOW_EXAMPLES)


def test_team_update_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["team", "update", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Set the team display name" in captured.out
    assert "Comma-separated team tags" in captured.out
    assert "Clear the stored default agent id" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, TEAM_UPDATE_EXAMPLES)


def test_handoff_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["handoff", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia handoff" in captured.out
    assert "thread-linked handoff pointers" in captured.out
    assert "workspace/runtime checks" in captured.out
    assert "add" in captured.out
    assert "list" in captured.out
    assert "show" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, HANDOFF_EXAMPLES)
    assert "Phase 7" not in captured.out


def test_legacy_artifact_alias_maps_to_hidden_handoff_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["artifact", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia handoff" in captured.out
    assert HANDOFF_EXAMPLES[0] in captured.out
    assert "Review notes ready" in captured.out
    assert "maia artifact" not in captured.out


def test_readme_examples_align_with_public_help() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "Hermes agents" not in readme
    assert "python -m maia" not in readme
    assert "Public examples use the installed `maia` entrypoint." in readme
    assert "## Part 1 operator flow" in readme
    assert "## What each command means" in readme
    assert "## Known limitations" in readme
    assert "## Runtime support boundary" in readme
    assert "## Live host runtime recovery" in readme
    assert "## V1 release checklist" in readme
    assert "v1 smoke checklist:" not in readme
    assert "Live host runtime checklist:" not in readme
    assert "Live host report format:" not in readme
    assert "Part 1 operator flow:" in readme
    for line in PART1_OPERATOR_FLOW:
        assert line in readme
    for line in KNOWN_LIMITATIONS:
        assert line in readme
    for line in RUNTIME_SUPPORT_BOUNDARY:
        assert line in readme
    for line in RUNTIME_RECOVERY_CHECKLIST:
        assert line in readme
    for line in V1_RELEASE_CHECKLIST:
        assert line in readme
    assert "Portable state: `maia export`, `maia inspect <path>`, `maia import <path>`" in readme
    assert "Team metadata: `maia team show`, `maia team update ...`" in readme
    assert "Collaboration visibility: `maia thread ...`, `maia handoff ...`, `maia workspace show ...`" in readme
    assert f"`{DOCTOR_EXAMPLES[0]}`" in readme
    assert f"`{SETUP_EXAMPLES[0]}`" in readme
    assert f"`{AGENT_SETUP_EXAMPLES[0]}`" in readme


def test_phase10_plan_locks_v1_release_and_smoke_checklists() -> None:
    plan = PHASE10_PLAN_PATH.read_text(encoding="utf-8")

    assert "## V1 release checklist" in plan
    assert "## V1 smoke checklist" in plan
    assert "`bash scripts/verify.sh`" in plan
    assert "reviewer approve" in plan
    assert "clean worktree" in plan


def test_phase12_plan_locks_runtime_boundary_and_host_checklist() -> None:
    plan = PHASE12_PLAN_PATH.read_text(encoding="utf-8")

    assert "## Scope" in plan
    assert "## Host validation runbook" in plan
    assert "`maia doctor`" in plan
    assert "`maia agent start <id>`" in plan
    assert "`maia agent stop <id>`" in plan


def test_phase13_plan_locks_recovery_and_report_contract() -> None:
    plan = (REPO_ROOT / "docs/plans/phase13-live-runtime-smoke-and-operator-recovery.md").read_text(encoding="utf-8")

    assert "## Runtime support boundary" in plan
    assert "## Live host runtime recovery" in plan
    assert "## Live host validation report template" in plan
    assert "`doctor=ok|fail`" in plan


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
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, AGENT_TUNE_EXAMPLES)
    assert "maia agent tune <planner_id> --role planner" in captured.out
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


def test_build_parser_logs_shape() -> None:
    args = build_parser().parse_args(["agent", "logs", "demo1234", "--tail-lines", "25"])

    assert args.agent_command == "logs"
    assert args.agent_id == "demo1234"
    assert args.tail_lines == 25


def _create_agent(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], home: Path, name: str) -> str:
    monkeypatch.setenv("HOME", str(home))
    assert main(["agent", "new", name]) == 0
    fields = _parse_fields(capsys.readouterr().out.strip())
    return fields["agent_id"]


def _configure_runtime_spec(
    capsys: pytest.CaptureFixture[str],
    agent_id: str,
    *,
    role_name: str,
    workspace_path: str,
) -> None:
    assert main([
        "agent",
        "tune",
        agent_id,
        "--runtime-image",
        f"ghcr.io/example/{role_name}:latest",
        "--runtime-workspace",
        workspace_path,
        "--runtime-command",
        "python",
        "--runtime-command=-m",
        "--runtime-command",
        role_name,
        "--runtime-env",
        "MAIA_ENV=test",
        "--runtime-env",
        f"MAIA_ROLE={role_name}",
    ]) == 0
    capsys.readouterr()


def test_send_and_reply_publish_to_broker_and_persist_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please review the latest patch",
        "--topic",
        "review handoff",
    ]) == 0
    sent_fields = _parse_fields(capsys.readouterr().out.strip())
    assert len(fake_broker.published) == 1
    assert fake_broker.published[0].from_agent == planner_id
    assert fake_broker.published[0].to_agent == reviewer_id
    assert fake_broker.closed is True

    first_message_id = sent_fields["message_id"]
    fake_broker.closed = False
    assert main([
        "reply",
        first_message_id,
        "--from-agent",
        reviewer_id,
        "--body",
        "looks good",
    ]) == 0
    reply_fields = _parse_fields(capsys.readouterr().out.strip())
    assert len(fake_broker.published) == 2
    assert fake_broker.published[1].from_agent == reviewer_id
    assert fake_broker.published[1].to_agent == planner_id
    assert reply_fields["reply_to_message_id"] == first_message_id
    assert fake_broker.closed is True

    payload = get_collaboration_path({"HOME": str(tmp_path)}).read_text(encoding="utf-8")
    assert "review handoff" in payload
    assert "please review the latest patch" in payload
    assert "looks good" in payload


def test_inbox_uses_broker_pull_when_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)

    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    fake_broker.pull_result = BrokerPullResult(
        status=BrokerDeliveryStatus.DELIVERED,
        messages=[
            BrokerMessageEnvelope(
                message=MessageRecord(
                    message_id="msg-001",
                    thread_id="thread-001",
                    from_agent="planner",
                    to_agent=reviewer_id,
                    kind=MessageKind.REQUEST,
                    body="broker delivery",
                    created_at="2026-04-15T12:00:00Z",
                ),
                receipt_handle="42",
                delivery_attempt=2,
            )
        ],
    )

    assert main(["inbox", reviewer_id]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert _parse_fields(lines[0]) == {
        "agent_id": reviewer_id,
        "messages": "1",
        "source": "broker",
        "ack": "after-print",
    }
    assert len(fake_broker.acked) == 1
    assert fake_broker.acked[0].receipt_handle == "42"
    message_fields = _parse_fields(lines[1])
    assert message_fields["message_id"] == "msg-001"
    assert message_fields["body"] == "broker␠delivery"
    assert message_fields["receipt_handle"] == "42"
    assert message_fields["delivery_attempt"] == "2"
    payload = get_collaboration_path({"HOME": str(tmp_path)}).read_text(encoding="utf-8")
    assert '"thread_id": "thread-001"' in payload
    assert '"message_id": "msg-001"' in payload
    assert fake_broker.closed is True


def test_inbox_surfaces_broker_ack_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    fake_broker.ack_error = ValueError("ack failed")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)

    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    fake_broker.pull_result = BrokerPullResult(
        status=BrokerDeliveryStatus.DELIVERED,
        messages=[
            BrokerMessageEnvelope(
                message=MessageRecord(
                    message_id="msg-001",
                    thread_id="thread-001",
                    from_agent="planner",
                    to_agent=reviewer_id,
                    kind=MessageKind.REQUEST,
                    body="broker delivery",
                    created_at="2026-04-15T12:00:00Z",
                ),
                receipt_handle="42",
                delivery_attempt=1,
            )
        ],
    )

    assert main(["inbox", reviewer_id]) == 1
    captured = capsys.readouterr()
    assert "ack failed" in captured.err


def test_broker_inbox_message_can_be_replied_to_after_local_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    fake_broker.pull_result = BrokerPullResult(
        status=BrokerDeliveryStatus.DELIVERED,
        messages=[
            BrokerMessageEnvelope(
                message=MessageRecord(
                    message_id="msg-001",
                    thread_id="thread-001",
                    from_agent=planner_id,
                    to_agent=reviewer_id,
                    kind=MessageKind.REQUEST,
                    body="broker delivery",
                    created_at="2026-04-15T12:00:00Z",
                ),
                receipt_handle="42",
                delivery_attempt=1,
            )
        ],
    )

    assert main(["inbox", reviewer_id]) == 0
    capsys.readouterr()
    fake_broker.pull_result = BrokerPullResult(status=BrokerDeliveryStatus.EMPTY)
    fake_broker.closed = False

    assert main([
        "reply",
        "msg-001",
        "--from-agent",
        reviewer_id,
        "--body",
        "copied and replied",
    ]) == 0
    reply_fields = _parse_fields(capsys.readouterr().out.strip())
    assert reply_fields["reply_to_message_id"] == "msg-001"
    assert len(fake_broker.published) == 1
    assert fake_broker.published[0].body == "copied and replied"
    assert fake_broker.closed is True


def test_broker_inbox_empty_pull_falls_back_to_local_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    fake_broker.pull_result = BrokerPullResult(
        status=BrokerDeliveryStatus.DELIVERED,
        messages=[
            BrokerMessageEnvelope(
                message=MessageRecord(
                    message_id="msg-001",
                    thread_id="thread-001",
                    from_agent=planner_id,
                    to_agent=reviewer_id,
                    kind=MessageKind.REQUEST,
                    body="broker delivery",
                    created_at="2026-04-15T12:00:00Z",
                ),
                receipt_handle="42",
                delivery_attempt=1,
            )
        ],
    )
    assert main(["inbox", reviewer_id]) == 0
    capsys.readouterr()

    fake_broker.pull_result = BrokerPullResult(status=BrokerDeliveryStatus.EMPTY)
    fake_broker.closed = False
    assert main(["inbox", reviewer_id]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert _parse_fields(lines[0]) == {
        "agent_id": reviewer_id,
        "messages": "0",
        "source": "broker",
        "ack": "complete",
    }
    assert len(lines) == 1
    assert fake_broker.closed is True


def test_merge_broker_inbox_messages_preserves_thread_topic(tmp_path: Path) -> None:
    storage = CollaborationStorage()
    collaboration_path = get_collaboration_path({"HOME": str(tmp_path)})
    collaboration = storage.load(collaboration_path)
    merged = cli_module._merge_broker_inbox_messages(
        storage,
        collaboration_path,
        collaboration,
        [
            (
                BrokerMessageEnvelope(
                    message=MessageRecord(
                        message_id="msg-001",
                        thread_id="thread-001",
                        from_agent="planner-id",
                        to_agent="reviewer-id",
                        kind=MessageKind.REQUEST,
                        body="broker delivery",
                        created_at="2026-04-15T12:00:00Z",
                    ),
                    receipt_handle="42",
                    delivery_attempt=1,
                ),
                {"thread_topic": "review handoff"},
            )
        ],
    )

    assert merged.threads[0].topic == "review handoff"


def test_send_does_not_persist_metadata_when_broker_publish_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    fake_broker.publish_error = ValueError("broker publish failed")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "should fail",
        "--topic",
        "review handoff",
    ]) == 1
    captured = capsys.readouterr()
    assert "broker publish failed" in captured.err
    assert not get_collaboration_path({"HOME": str(tmp_path)}).exists()
    assert fake_broker.closed is True


def test_broker_inbox_merge_adds_new_participant_to_existing_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_broker = FakeMessageBroker()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    analyst_id = _create_agent(monkeypatch, capsys, tmp_path, "analyst")

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "initial",
        "--topic",
        "review thread",
    ]) == 0
    sent_fields = _parse_fields(capsys.readouterr().out.strip())
    thread_id = sent_fields["thread_id"]

    monkeypatch.setenv("MAIA_BROKER_URL", "amqp://broker")
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: fake_broker)
    fake_broker.pull_result = BrokerPullResult(
        status=BrokerDeliveryStatus.DELIVERED,
        messages=[
            BrokerMessageEnvelope(
                message=MessageRecord(
                    message_id="msg-002",
                    thread_id=thread_id,
                    from_agent=planner_id,
                    to_agent=analyst_id,
                    kind=MessageKind.NOTE,
                    body="loop analyst in",
                    created_at="2026-04-15T12:01:00Z",
                ),
                receipt_handle="43",
                delivery_attempt=1,
            )
        ],
    )

    assert main(["inbox", analyst_id]) == 0
    capsys.readouterr()
    fake_broker.pull_result = BrokerPullResult(status=BrokerDeliveryStatus.EMPTY)
    fake_broker.closed = False

    assert main([
        "reply",
        "msg-002",
        "--from-agent",
        analyst_id,
        "--body",
        "joined",
    ]) == 0
    reply_fields = _parse_fields(capsys.readouterr().out.strip())
    assert reply_fields["reply_to_message_id"] == "msg-002"
    assert fake_broker.published[-1].from_agent == analyst_id
    assert fake_broker.closed is True


def test_handoff_add_list_and_show_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    _configure_runtime_spec(
        capsys,
        planner_id,
        role_name="planner",
        workspace_path="/workspace/planner",
    )
    _configure_runtime_spec(
        capsys,
        reviewer_id,
        role_name="reviewer",
        workspace_path="/workspace/reviewer",
    )

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "review package ready",
        "--topic",
        "review handoff",
    ]) == 0
    thread_id = _parse_fields(capsys.readouterr().out.strip())["thread_id"]

    assert main([
        "handoff",
        "add",
        "--thread-id",
        thread_id,
        "--from-agent",
        planner_id,
        "--to-agent",
        reviewer_id,
        "--type",
        "report",
        "--location",
        "reports/review.md",
        "--summary",
        "Review notes ready",
    ]) == 0
    add_fields = _parse_fields(capsys.readouterr().out.strip())
    handoff_id = add_fields["handoff_id"]
    assert add_fields["thread_id"] == thread_id
    assert add_fields["from_agent"] == planner_id
    assert add_fields["to_agent"] == reviewer_id
    assert add_fields["type"] == "report"
    assert add_fields["location"] == "reports/review.md"
    assert add_fields["summary"] == "Review␠notes␠ready"

    collaboration = CollaborationStorage().load(get_collaboration_path({"HOME": str(tmp_path)}))
    assert len(collaboration.handoffs) == 1
    assert collaboration.handoffs[0].handoff_id == handoff_id
    assert collaboration.handoffs[0].thread_id == thread_id

    assert main(["handoff", "list"]) == 0
    list_lines = capsys.readouterr().out.strip().splitlines()
    assert len(list_lines) == 1
    list_fields = _parse_fields(list_lines[0])
    assert list_fields["handoff_id"] == handoff_id
    assert list_fields["thread_id"] == thread_id

    assert main(["handoff", "list", "--thread-id", thread_id]) == 0
    filtered_lines = capsys.readouterr().out.strip().splitlines()
    assert len(filtered_lines) == 1
    filtered_fields = _parse_fields(filtered_lines[0])
    assert filtered_fields["handoff_id"] == handoff_id

    assert main(["handoff", "show", handoff_id]) == 0
    show_lines = capsys.readouterr().out.strip().splitlines()
    assert len(show_lines) == 3
    show_fields = _parse_fields(show_lines[0])
    assert show_fields["handoff_id"] == handoff_id
    assert show_fields["location"] == "reports/review.md"
    assert show_fields["summary"] == "Review␠notes␠ready"
    source_workspace_fields = _parse_fields(show_lines[1])
    assert source_workspace_fields == {
        "handoff_role": "source",
        "agent_id": planner_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/workspace/planner",
        "runtime_image": "ghcr.io/example/planner:latest",
        "runtime_command": "python,-m,planner",
        "runtime_env_keys": "MAIA_ENV,MAIA_ROLE",
    }
    target_workspace_fields = _parse_fields(show_lines[2])
    assert target_workspace_fields == {
        "handoff_role": "target",
        "agent_id": reviewer_id,
        "workspace_status": "configured",
        "workspace_basis": "runtime_spec.workspace",
        "workspace": "/workspace/reviewer",
        "runtime_image": "ghcr.io/example/reviewer:latest",
        "runtime_command": "python,-m,reviewer",
        "runtime_env_keys": "MAIA_ENV,MAIA_ROLE",
    }


def test_legacy_artifact_alias_still_adds_lists_and_shows_handoffs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "review package ready",
        "--topic",
        "review handoff",
    ]) == 0
    thread_id = _parse_fields(capsys.readouterr().out.strip())["thread_id"]

    assert main([
        "artifact",
        "add",
        "--thread-id",
        thread_id,
        "--from-agent",
        planner_id,
        "--to-agent",
        reviewer_id,
        "--type",
        "report",
        "--location",
        "reports/review.md",
        "--summary",
        "Review notes ready",
    ]) == 0
    add_fields = _parse_fields(capsys.readouterr().out.strip())
    handoff_id = add_fields["handoff_id"]

    assert main(["artifact", "show", handoff_id]) == 0
    show_lines = capsys.readouterr().out.strip().splitlines()
    assert len(show_lines) == 3
    show_fields = _parse_fields(show_lines[0])
    assert show_fields["handoff_id"] == handoff_id
    source_workspace_fields = _parse_fields(show_lines[1])
    assert source_workspace_fields["handoff_role"] == "source"
    assert source_workspace_fields["workspace_status"] == "runtime-spec-missing"
    assert source_workspace_fields["workspace_basis"] == "runtime_spec.workspace"
    assert source_workspace_fields["workspace"] == "-"
    target_workspace_fields = _parse_fields(show_lines[2])
    assert target_workspace_fields["handoff_role"] == "target"
    assert target_workspace_fields["workspace_status"] == "runtime-spec-missing"
    assert target_workspace_fields["workspace_basis"] == "runtime_spec.workspace"
    assert target_workspace_fields["workspace"] == "-"


def test_handoff_add_rejects_non_participant_agents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    analyst_id = _create_agent(monkeypatch, capsys, tmp_path, "analyst")

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "review package ready",
        "--topic",
        "review handoff",
    ]) == 0
    thread_id = _parse_fields(capsys.readouterr().out.strip())["thread_id"]

    assert main([
        "handoff",
        "add",
        "--thread-id",
        thread_id,
        "--from-agent",
        planner_id,
        "--to-agent",
        analyst_id,
        "--type",
        "report",
        "--location",
        "reports/review.md",
        "--summary",
        "Review notes ready",
    ]) == 1
    captured = capsys.readouterr()
    assert "Handoff recipient must be a participant in the thread" in captured.err

    collaboration = CollaborationStorage().load(get_collaboration_path({"HOME": str(tmp_path)}))
    assert collaboration.handoffs == []
    assert collaboration.threads[0].participants == [planner_id, reviewer_id]


def test_handoff_list_rejects_unknown_thread_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert main(["handoff", "list", "--thread-id", "missing-thread"]) == 1
    captured = capsys.readouterr()
    assert "Thread with id 'missing-thread' not found" in captured.err


def test_thread_list_and_show_surface_control_plane_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    state_db_path = get_state_db_path({"HOME": str(tmp_path)})
    CollaborationStorage().save(
        state_db_path,
        threads=[
            ThreadRecord(
                thread_id="thread-001",
                topic="review handoff",
                participants=["planner", "reviewer"],
                created_by="planner",
                status="open",
                created_at="2026-04-15T12:00:00Z",
                updated_at="2026-04-15T12:02:00Z",
            ),
            ThreadRecord(
                thread_id="thread-002",
                topic="retro wrap-up",
                participants=["planner", "analyst"],
                created_by="planner",
                status="closed",
                created_at="2026-04-15T10:30:00Z",
                updated_at="2026-04-15T11:00:00Z",
            ),
            ThreadRecord(
                thread_id="thread-003",
                topic="colon identity",
                participants=["agent:1"],
                created_by="agent:1",
                status="open",
                created_at="2026-04-15T09:00:00Z",
                updated_at="2026-04-15T09:00:00Z",
            ),
        ],
        messages=[
            MessageRecord(
                message_id="msg-002",
                thread_id="thread-001",
                from_agent="reviewer",
                to_agent="planner",
                kind=MessageKind.ANSWER,
                body="latest update",
                created_at="2026-04-15T12:02:00Z",
                reply_to_message_id="msg-001",
            ),
            MessageRecord(
                message_id="msg-001",
                thread_id="thread-001",
                from_agent="planner",
                to_agent="reviewer",
                kind=MessageKind.REQUEST,
                body="first ask",
                created_at="2026-04-15T12:00:00Z",
            ),
            MessageRecord(
                message_id="msg-003",
                thread_id="thread-002",
                from_agent="planner",
                to_agent="analyst",
                kind=MessageKind.NOTE,
                body="closed context",
                created_at="2026-04-15T11:00:00Z",
            ),
        ],
        handoffs=[
            HandoffRecord(
                handoff_id="artifact-001",
                thread_id="thread-001",
                from_agent="planner",
                to_agent="reviewer",
                kind=HandoffKind.REPORT,
                location="reports/review.md",
                summary="Review notes ready",
                created_at="2026-04-15T12:01:00Z",
            )
        ],
    )
    RuntimeStateStorage().save(
        state_db_path,
        {
            "planner": cli_module.RuntimeState(
                agent_id="planner",
                runtime_status=cli_module.RuntimeStatus.RUNNING,
                runtime_handle="runtime-001",
            ),
            "analyst": cli_module.RuntimeState(
                agent_id="analyst",
                runtime_status=cli_module.RuntimeStatus.FAILED,
                runtime_handle="runtime-009",
            ),
        },
    )

    assert main(["thread", "list"]) == 0
    list_lines = capsys.readouterr().out.strip().splitlines()
    assert len(list_lines) == 3
    open_fields = _parse_fields(list_lines[0])
    assert open_fields["thread_id"] == "thread-001"
    assert open_fields["topic"] == "review␠handoff"
    assert open_fields["participants"] == "planner,reviewer"
    assert open_fields["participant_runtime"] == "planner:running,reviewer:stopped"
    assert open_fields["status"] == "open"
    assert open_fields["updated_at"] == "2026-04-15T12:02:00Z"
    assert open_fields["pending_on"] == "planner"
    assert open_fields["handoffs"] == "1"
    assert open_fields["messages"] == "2"
    closed_fields = _parse_fields(list_lines[1])
    assert closed_fields["thread_id"] == "thread-002"
    assert closed_fields["participant_runtime"] == "planner:running,analyst:failed"
    colon_fields = _parse_fields(list_lines[2])
    assert colon_fields["thread_id"] == "thread-003"
    assert colon_fields["participant_runtime"] == "agent%3A1:stopped"
    assert colon_fields["pending_on"] == "-"

    assert main(["thread", "list", "--agent", "reviewer"]) == 0
    reviewer_lines = capsys.readouterr().out.strip().splitlines()
    assert len(reviewer_lines) == 1
    assert _parse_fields(reviewer_lines[0])["thread_id"] == "thread-001"

    assert main(["thread", "list", "--status", "closed"]) == 0
    closed_lines = capsys.readouterr().out.strip().splitlines()
    assert len(closed_lines) == 1
    assert _parse_fields(closed_lines[0])["thread_id"] == "thread-002"

    assert main(["thread", "show", "thread-001"]) == 0
    show_lines = capsys.readouterr().out.strip().splitlines()
    assert len(show_lines) == 3
    show_fields = _parse_fields(show_lines[0])
    assert show_fields["thread_id"] == "thread-001"
    assert show_fields["participant_runtime"] == "planner:running,reviewer:stopped"
    assert show_fields["pending_on"] == "planner"
    assert show_fields["handoffs"] == "1"
    assert show_fields["messages"] == "2"
    assert show_fields["created_by"] == "planner"
    assert show_fields["created_at"] == "2026-04-15T12:00:00Z"
    assert show_fields["recent_handoff_id"] == "artifact-001"
    assert show_fields["recent_handoff_from"] == "planner"
    assert show_fields["recent_handoff_to"] == "reviewer"
    assert show_fields["recent_handoff_type"] == "report"
    assert show_fields["recent_handoff_location"] == "reports/review.md"
    assert show_fields["recent_handoff_summary"] == "Review␠notes␠ready"
    assert show_fields["recent_handoff_created_at"] == "2026-04-15T12:01:00Z"
    first_message_fields = _parse_fields(show_lines[1])
    second_message_fields = _parse_fields(show_lines[2])
    assert first_message_fields["message_id"] == "msg-001"
    assert second_message_fields["message_id"] == "msg-002"

    assert main(["thread", "thread-001", "--limit", "1"]) == 0
    legacy_lines = capsys.readouterr().out.strip().splitlines()
    assert len(legacy_lines) == 2
    assert _parse_fields(legacy_lines[0])["thread_id"] == "thread-001"


def test_thread_visibility_uses_sqlite_state_even_if_runtime_json_cache_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    state_db_path = get_state_db_path({"HOME": str(tmp_path)})
    runtime_state_path = get_runtime_state_path({"HOME": str(tmp_path)})
    CollaborationStorage().save(
        state_db_path,
        threads=[
            ThreadRecord(
                thread_id="thread-invalid-runtime",
                topic="runtime fallback",
                participants=["planner"],
                created_by="planner",
                status="open",
                created_at="2026-04-15T08:00:00Z",
                updated_at="2026-04-15T08:00:00Z",
            )
        ],
        messages=[],
        handoffs=[],
    )
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text("{bad json\n", encoding="utf-8")

    assert main(["thread", "list"]) == 0
    fields = _parse_fields(capsys.readouterr().out.strip())
    assert fields["thread_id"] == "thread-invalid-runtime"
    assert fields["participant_runtime"] == "planner:stopped"
    assert fields["pending_on"] == "-"


def test_thread_show_preserves_message_order_when_timestamps_tie(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module, "_build_message_broker", lambda: None)

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    timestamps = iter(["2026-04-15T12:00:00Z", "2026-04-15T12:00:00Z"])
    monkeypatch.setattr(cli_module, "_timestamp_now", lambda: next(timestamps))

    assert main([
        "send",
        planner_id,
        reviewer_id,
        "--body",
        "please review the latest patch",
        "--topic",
        "review handoff",
    ]) == 0
    sent_fields = _parse_fields(capsys.readouterr().out.strip())

    assert main([
        "reply",
        sent_fields["message_id"],
        "--from-agent",
        reviewer_id,
        "--body",
        "review complete",
    ]) == 0
    reply_fields = _parse_fields(capsys.readouterr().out.strip())

    assert main(["thread", "show", sent_fields["thread_id"]]) == 0
    thread_lines = capsys.readouterr().out.strip().splitlines()
    thread_fields = _parse_fields(thread_lines[0])
    first_message_fields = _parse_fields(thread_lines[1])
    second_message_fields = _parse_fields(thread_lines[2])

    assert thread_fields["pending_on"] == planner_id
    assert first_message_fields["message_id"] == sent_fields["message_id"]
    assert second_message_fields["message_id"] == reply_fields["message_id"]
    assert second_message_fields["reply_to_message_id"] == sent_fields["message_id"]


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
