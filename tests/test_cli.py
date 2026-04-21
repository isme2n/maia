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
    get_agent_hermes_home,
    get_runtime_state_path,
    get_state_db_path,
)
from maia.cli import main
from maia import cli as cli_module
from maia.cli_parser import (
    AGENT_SETUP_EXAMPLES,
    AGENT_TUNE_EXAMPLES,
    DIRECT_AGENT_DELEGATION_CONTRACT,
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
    PART2_CONVERSATION_CONTRACT,
    PART2_VISIBILITY_FLOW,
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
from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxSessionRecord,
    KeryxSessionStatus,
)
from maia.keryx_service import KeryxService
from maia.keryx_skill import get_agent_keryx_skill_path, render_keryx_skill_content
from maia.runtime_adapter import RuntimeStartResult, RuntimeState, RuntimeStatus
from maia.runtime_state_storage import RuntimeStateStorage
from maia.storage import JsonRegistryStorage

README_PATH = REPO_ROOT / "README.md"
PRD_PATH = REPO_ROOT / "docs/prd/maia-core-product.md"
ROADMAP_PATH = REPO_ROOT / "docs/plans/maia-product-roadmap-5-parts.md"
PHASE10_PLAN_PATH = REPO_ROOT / "docs/plans/phase10-release-hardening-and-v1-closeout.md"
PHASE12_PLAN_PATH = REPO_ROOT / "docs/plans/phase12-live-runtime-readiness-and-host-validation.md"
PHASE15_PLAN_PATH = REPO_ROOT / "docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md"
PHASE16_PLAN_PATH = REPO_ROOT / "docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md"


def _parse_fields(line: str) -> dict[str, str]:
    tokens = line.split()
    if tokens and tokens[0] in {"added", "created", "message_id", "thread", "workspace"}:
        tokens = tokens[1:]
    return dict(token.split("=", 1) for token in tokens)


def _line_with_prefix(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"Missing line starting with {prefix!r}: {text!r}")

def _assert_contains_lines(text: str, lines: tuple[str, ...]) -> None:
    for line in lines:
        assert line in text


def _assert_contains_in_order(text: str, snippets: tuple[str, ...]) -> None:
    start = 0
    for snippet in snippets:
        index = text.find(snippet, start)
        assert index != -1, f"Missing snippet in order: {snippet!r}"
        start = index + len(snippet)


def _assert_not_contains_any(text: str, snippets: tuple[str, ...]) -> None:
    for snippet in snippets:
        assert snippet not in text


def _markdown_numbered_lines(section: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in section.splitlines()
        if ". " in line.strip() and line.strip().split(". ", 1)[0].isdigit()
    )


def _section_after_heading(text: str, heading: str, end_headings: tuple[str, ...]) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != heading:
            continue
        section_lines: list[str] = []
        for next_line in lines[index + 1 :]:
            if next_line.strip() in end_headings:
                break
            section_lines.append(next_line)
        return "\n".join(section_lines)
    raise AssertionError(f"Missing section heading {heading!r}")


def _assert_locked_collaboration_contract(section: str) -> None:
    assert "User-facing collaboration entry is `/keryx <instruction>`." in section
    assert "Keryx message delivery intent uses `delivery_mode`:" in section
    assert "`agent_only`" in section
    assert "`user_direct`" in section
    assert "`failed`" in section
    active_section = "\n".join(
        line
        for line in section.splitlines()
        if "Legacy `/call` and `/agent-call` are removed from the active collaboration contract." not in line
    )
    assert "`/call`" not in active_section
    assert "`/agent-call`" not in active_section


def _assert_locked_portable_state_contract(section: str) -> None:
    assert (
        "Primary Part 3 flow: `maia export` saves the full portable snapshot to "
        "`~/.maia/exports/maia-state.maia` by default."
    ) in section
    assert (
        "`maia export <path>` writes the same portable state to an explicit "
        "user/project snapshot path."
    ) in section
    assert (
        "`maia import <path>` restores safely: preview first, confirm before "
        "destructive apply, use `--yes` to skip confirmation."
    ) in section
    assert (
        "`maia inspect <path>` is an optional support command, not a required "
        "part of the normal save/restore flow."
    ) in section
    primary_section = "\n".join(
        line for line in section.splitlines() if "optional support command" not in line
    )
    assert "`maia inspect <path>`" not in primary_section


def test_readme_locks_part1_public_flow() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    first_run = _section_after_heading(text, "## First run", ("## Part 1 operator flow",))

    assert "## First run" in text
    assert "Install Maia, then follow the Part 1 bootstrap path in this order" in text
    assert "maia doctor" in text
    assert "maia setup" in text
    assert "maia agent new" in text
    assert "maia agent setup planner" in text
    assert "maia agent start planner" in text
    assert "maia agent stop planner" in text
    assert "shared infra" in text.lower()
    assert "hermes setup" in text
    assert "interactively create an agent identity" in text.lower()
    assert "`maia doctor` is the infra-only gate for this flow." in first_run
    assert "Portable state and Keryx visibility stay available as support surfaces outside this first-run path." in first_run
    assert _markdown_numbered_lines(first_run) == (
        "1. `maia doctor`",
        "2. `maia setup`",
        "3. `maia agent new`",
        "4. `maia agent setup <name>`",
        "5. `maia agent start <name>`",
    )
    _assert_not_contains_any(
        first_run,
        (
            "`maia export`",
            "`maia import`",
            "`maia inspect`",
            "`maia thread`",
            "`maia handoff`",
            "`maia workspace`",
        ),
    )
    assert "overall launch-readiness state as `not-configured`, `ready`, or `running`" in text
    assert "recorded setup state (`not-started|complete|incomplete`) and current runtime state" in text
    assert "interactive `hermes setup` session only in the CLI" in text
    assert "interactive CLI-only passthrough to `hermes setup`" in text
    assert "agent setup is recorded separately from the runtime launch state" in text
    assert "new agents carry the shared Hermes worker defaults needed for first start" in text
    assert "Part 2 Keryx collaboration" in text
    assert "Keryx is Maia's canonical collaboration root for live multi-agent work." in text
    assert "`thread` / `thread_id` are Maia's public names for the Keryx collaboration object." in text
    assert "a Maia thread is not a Hermes session" in text
    assert "operator manually relays every message in a CLI messenger" in text
    assert "Users talk directly to a specific agent" in text
    assert "active conversation agent stays the user-facing anchor" in text
    assert "central dispatcher or front desk" in text
    assert "user -> economist -> tech -> economist -> user" in text
    assert "thread`, `handoff`, and `workspace`" in text
    assert "## Part 2 visibility flow" in text
    assert "Keryx-backed operator views" in text
    assert "still lands in the next task" not in text
    assert "bootstraps the shared Maia network, Keryx HTTP API container, and SQLite state DB" in text
    assert "fail cleanly for now" not in text
    assert "send/reply/inbox/thread" not in text
    assert "Secondary surfaces" in text
    _assert_locked_collaboration_contract(
        _section_after_heading(
            text,
            "## Part 2 Keryx collaboration",
            ("## Direct-agent delegation contract",),
        )
    )
    _assert_contains_lines(text, PART2_VISIBILITY_FLOW)


def test_readme_locks_direct_agent_anchor_story() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    assert "## Direct-agent delegation contract" in text
    assert "user talks to one named agent" in text
    assert "front-desk chatbot" in text
    assert "The active conversation agent remains the user-facing anchor" in text
    assert "Concrete public example: `user -> economist -> tech -> economist -> user`" in text
    assert "Economist -> User: final answer in the original conversation" in text


def test_prd_locks_part1_operator_story() -> None:
    text = PRD_PATH.read_text(encoding="utf-8")

    assert "doctor → setup → agent new → agent setup → agent start" in text
    assert "identity" in text.lower()
    assert "hermes setup" in text
    assert "interactive CLI-only" in text
    assert "Part 2 direction" in text
    assert "Keryx를 canonical collaboration root로 삼아 running agents가 multi-turn으로 협업" in text
    assert "Keryx collaboration object를 `thread` / `thread_id`로 부르고" in text
    assert "thread list -> thread show -> handoff show -> workspace show -> agent status -> agent logs" in text
    assert "## Part 2 completion criteria" in text
    assert "pending thread" in text
    assert "closeout story" in text
    assert "public golden flow" in text


def test_phase15_task102_matches_part1_contract() -> None:
    text = PHASE15_PLAN_PATH.read_text(encoding="utf-8")

    assert "doctor → setup → agent new → agent setup → agent start" in text
    assert "Only infra readiness; no Hermes login/API key/provider checks." in text
    assert "No team defaults, no model policy wizard." in text
    assert "agent setup" in text


def test_phase15_task108_closeout_is_recorded() -> None:
    text = PHASE15_PLAN_PATH.read_text(encoding="utf-8")

    assert "Task 108 — docs/help/tests closeout and scope cleanup" in text
    assert "README first-run section must read like" in text
    assert "Ensure examples do not imply Maia is a CLI messenger." in text
    assert "Status:" in text


def test_phase16_plan_locks_part2_contract() -> None:
    text = PHASE16_PLAN_PATH.read_text(encoding="utf-8")

    assert "# Phase 16 Real Agent Conversation and Broker Message Plane Plan" in text
    assert "running agents talk to each other over the broker/message plane" in text
    assert "The product story is not“" not in text
    assert "사람이 CLI로 직접 모든 메시지를 relay하는 제품" in text
    assert "Task 109 — Part 2 contract and public surface lock" in text
    assert "Task 114 — Part 2 docs/help/tests closeout" in text
    assert "## Part 2 closeout status" in text
    assert "Status: complete" in text
    assert "public docs/help/tests tell the same operator story" in text


def test_roadmap_points_part2_to_phase16_plan() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8")

    assert "## Part 2 — Real Agent Conversation" in text
    assert "docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md" in text
    assert "`thread`, `handoff`, `workspace`, `agent status`, `agent logs`" in text
    assert "최근 handoff와 participant runtime 상태" in text
    assert "[x] Part 2 complete" in text


def test_sqlite_control_plane_path_defaults_under_maia_home(tmp_path: Path) -> None:
    assert get_state_db_path({"HOME": str(tmp_path)}) == tmp_path / ".maia" / "maia.db"
    assert get_agent_hermes_home("planner1234", {"HOME": str(tmp_path)}) == (
        tmp_path / ".maia" / "agents" / "planner1234" / "hermes"
    )


def test_top_level_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    part1_section = _section_after_heading(captured.out, "Part 1 operator flow:", ("Doctor role:",))
    assert "usage: maia" in captured.out
    assert "agent" in captured.out
    assert "team" in captured.out
    assert "doctor" in captured.out
    assert "setup" in captured.out
    assert "thread" in captured.out
    assert "handoff" in captured.out
    assert "workspace" in captured.out
    assert "artifact" not in captured.out
    assert "Export Maia portable state" in captured.out
    assert "Import Maia portable state safely" in captured.out
    assert "Inspect an importable Maia snapshot" in captured.out
    assert "Check shared infra readiness" in captured.out
    assert "Bootstrap shared Maia infra" in captured.out
    assert "Part 1 operator flow:" in captured.out
    assert "Doctor role:" in captured.out
    assert "Support surfaces:" in captured.out
    assert "Known limitations:" in captured.out
    assert "Keryx collaboration contract:" in captured.out
    assert "Direct-agent delegation contract:" in captured.out
    assert "Keryx operator visibility flow:" in captured.out
    assert "Quickstart (local state only):" not in captured.out
    assert "V1 smoke checklist:" not in captured.out
    assert "send <" not in captured.out
    assert "reply <" not in captured.out
    assert "maia thread show <thread_id>" in captured.out
    assert "maia handoff show <handoff_id>" in captured.out
    _assert_locked_collaboration_contract(
        _section_after_heading(
            captured.out,
            "Keryx collaboration contract:",
            ("Direct-agent delegation contract:",),
        )
    )
    _assert_contains_lines(captured.out, PART1_OPERATOR_FLOW)
    _assert_contains_in_order(
        captured.out,
        (
            "maia doctor",
            "maia setup",
            "maia agent new",
            "maia agent setup planner",
            "maia agent start planner",
        ),
    )
    assert "`maia doctor` is the first bootstrap gate for Maia shared infra." in captured.out
    assert "It checks Docker, Keryx HTTP API, and SQLite state DB readiness only, then points you to the next step." in captured.out
    assert "RabbitMQ" not in captured.out
    assert "If `doctor` passes, continue to `maia setup`; if it fails, fix shared infra and rerun `maia doctor`." in captured.out
    assert "Portable state (`export`, `import`, `inspect`) stays public as operator support, not the first-run bootstrap path." in captured.out
    assert "Keryx visibility (`thread`, `handoff`, `workspace`) stays public as operator support, not the Part 1 bootstrap flow." in captured.out
    _assert_contains_lines(captured.out, KNOWN_LIMITATIONS)
    _assert_contains_lines(captured.out, PART2_CONVERSATION_CONTRACT)
    _assert_contains_lines(captured.out, DIRECT_AGENT_DELEGATION_CONTRACT)
    _assert_contains_lines(captured.out, PART2_VISIBILITY_FLOW)
    _assert_contains_in_order(
        part1_section,
        (
            "maia doctor",
            "maia setup",
            "maia agent new",
            "maia agent setup planner",
            "maia agent start planner",
        ),
    )
    _assert_not_contains_any(
        part1_section,
        (
            "maia export",
            "maia import",
            "maia inspect",
            "maia thread",
            "maia handoff",
            "maia workspace",
        ),
    )
    _assert_locked_portable_state_contract(
        _section_after_heading(
            captured.out,
            "Portable state flow:",
            ("Known limitations:",),
        )
    )


def test_agent_new_help_describes_identity_only_flow(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "new", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Interactively create an agent identity" in captured.out
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
    assert "in the CLI" in captured.out
    assert "provider" not in captured.out
    assert "runtime image" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, AGENT_SETUP_EXAMPLES)


def test_agent_runtime_help_uses_operator_wording(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Start an agent runtime" in captured.out
    assert "Stop a running agent runtime" in captured.out
    assert "Show agent runtime status" in captured.out
    assert "Show agent runtime logs" in captured.out
    assert "start agent" not in captured.out
    assert "stop agent" not in captured.out
    assert "status agent" not in captured.out
    assert "logs agent" not in captured.out


def test_agent_start_help_describes_part1_prerequisites(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "start", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert (
        "Start an agent runtime after shared infra, agent setup, and gateway/home-channel readiness are complete."
        in captured.out
    )
    assert "name" in captured.out


def test_team_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["team", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia team" in captured.out
    assert "show" in captured.out
    assert "update" in captured.out
    assert "agent" not in captured.out

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
    assert "Keryx-backed collaboration threads" in captured.out
    assert "participant runtime summaries" in captured.out
    assert "public name for this Keryx collaboration object" in captured.out
    assert "distinct from a Hermes session" in captured.out
    assert "Examples:" in captured.out
    _assert_locked_collaboration_contract(
        _section_after_heading(
            captured.out,
            "Keryx collaboration contract:",
            ("Examples:",),
        )
    )
    _assert_contains_lines(captured.out, THREAD_EXAMPLES)


def test_collaboration_help_centers_keryx_visibility_surface(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["thread", "--help"])
    thread_out = capsys.readouterr().out
    assert "Keryx-backed collaboration threads" in thread_out
    assert "participant runtime summaries" in thread_out
    assert "send" not in thread_out
    assert "reply" not in thread_out
    assert "inbox" not in thread_out


def test_workspace_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["workspace", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: maia workspace" in captured.out
    assert "Keryx-backed operator workspace context" in captured.out
    assert "runtime/workspace context" in captured.out
    assert "stored agent runtime spec" not in captured.out
    assert "show" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, WORKSPACE_EXAMPLES)


def test_agent_setup_gateway_help_uses_recovery_wording(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "setup-gateway", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Recover skipped gateway/home-channel setup for an agent in the CLI" in captured.out
    assert "messaging/home-channel setup was skipped during the normal agent setup flow" in captured.out
    assert "primary bootstrap" not in captured.out


def test_agent_start_help_mentions_gateway_readiness(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "start", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "gateway/home-channel readiness" in captured.out


def test_agent_help_includes_archive_all_and_purge_all(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["agent", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "archive-all" in captured.out
    assert "purge-all" in captured.out


def test_build_parser_agent_bulk_lifecycle_shapes() -> None:
    archive_args = build_parser().parse_args(["agent", "archive-all"])
    purge_args = build_parser().parse_args(["agent", "purge-all", "--yes"])

    assert archive_args.resource == "agent"
    assert archive_args.agent_command == "archive-all"
    assert not hasattr(archive_args, "agent_id")
    assert purge_args.resource == "agent"
    assert purge_args.agent_command == "purge-all"
    assert purge_args.yes is True


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
    assert "Check shared infra readiness for Docker, Keryx HTTP API, and SQLite state DB access only." in captured.out
    assert "Docker" in captured.out
    assert "RabbitMQ" not in captured.out
    assert "Keryx HTTP API" in captured.out
    assert "SQLite" in captured.out
    assert "Role:" in captured.out
    assert "maia setup" in captured.out
    assert "provider" not in captured.out
    assert "hermes setup" not in captured.out
    assert "login" not in captured.out
    assert "wizard" not in captured.out
    assert "Examples:" in captured.out
    assert "`maia doctor` is the first bootstrap gate for Maia shared infra." in captured.out
    assert "It checks Docker, Keryx HTTP API, and SQLite state DB readiness only, then points you to the next step." in captured.out
    assert "RabbitMQ" not in captured.out
    assert "If `doctor` passes, continue to `maia setup`; if it fails, fix shared infra and rerun `maia doctor`." in captured.out
    _assert_contains_lines(captured.out, DOCTOR_EXAMPLES)
    assert "doctor" in captured.out


def test_setup_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["setup", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Bootstrap shared Maia infra" in captured.out
    assert "Docker" in captured.out
    assert "RabbitMQ" not in captured.out
    assert "Keryx HTTP API" in captured.out
    assert "SQLite" in captured.out
    assert "team defaults" not in captured.out
    assert "model defaults" not in captured.out
    assert "wizard" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, SETUP_EXAMPLES)


def test_setup_command_prints_bootstrap_summary_from_infra_runtime(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli_module.infra_runtime,
        "bootstrap_shared_infra",
        lambda state_path: [
            {"step": "network", "status": "created", "detail": "maia"},
            {"step": "keryx", "status": "started", "detail": "http://maia-keryx:8765"},
            {"step": "db", "status": "ready", "detail": str(state_path)},
        ],
    )

    assert main(["setup"]) == 0
    captured = capsys.readouterr()
    assert "Created Maia network maia." in captured.out
    assert "Started Keryx HTTP API http://maia-keryx:8765." in captured.out
    assert "SQLite State DB is ready at" in captured.out
    assert "Shared infra is ready." in captured.out
    assert "Next: run maia agent new" in captured.out
    assert captured.err == ""


def test_agent_new_prompts_for_identity_fields_and_points_to_agent_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    answers = iter(["econ", "Ash", "Calm macro researcher"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    assert main(["agent", "new"]) == 0
    captured = capsys.readouterr()
    assert "How should this agent address you" in captured.out
    assert "Persona" in captured.out
    assert "created agent_id=" in captured.out
    assert "name=econ" in captured.out
    assert "call_sign=Ash" in captured.out
    assert "Next: run maia agent setup econ" in captured.out

    registry = JsonRegistryStorage().load(get_state_db_path({"HOME": str(tmp_path)}))
    record = registry.list()[0]
    assert record.name == "econ"
    assert record.call_sign == "Ash"
    assert record.persona == "Calm macro researcher"
    skill_path = get_agent_keryx_skill_path(record.agent_id, {"HOME": str(tmp_path)})
    assert skill_path.exists()
    assert "name: keryx" in skill_path.read_text(encoding="utf-8")
    assert "/keryx 경제에게 지난번 조사했던 거 있으면 그거 좀 달라 그래" in skill_path.read_text(encoding="utf-8")


def test_builtin_keryx_skill_locks_grounded_http_workflow() -> None:
    content = render_keryx_skill_content()

    assert "`/keryx <instruction>`" in content
    assert "실제 Keryx HTTP API" in content
    assert "실제로 Keryx 리소스를 만들거나 읽지 않았고" in content
    assert "협업을 수행한 척하지 말고" in content
    assert "실제 HTTP 호출/응답 확인 없이 다른 agent가 이미 답했다고 꾸며내지 않는다." in content
    assert "`GET /agents`" in content
    assert "`GET /sessions`" in content
    assert "`POST /sessions`" in content
    assert "`POST /sessions/{session_id}/messages`" in content
    assert "`GET /sessions/{session_id}/messages`" in content
    assert "`POST /sessions/{session_id}/handoffs`" in content
    assert "기본값은 새 session 생성이다." in content
    assert "thread_id=<session_id>" in content


def test_agent_new_installs_keryx_skill_with_grounded_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    answers = iter(["econ", "Ash", "Calm macro researcher"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    assert main(["agent", "new"]) == 0
    capsys.readouterr()

    registry = JsonRegistryStorage().load(get_state_db_path({"HOME": str(tmp_path)}))
    record = registry.list()[0]
    content = get_agent_keryx_skill_path(record.agent_id, {"HOME": str(tmp_path)}).read_text(encoding="utf-8")

    assert "`GET /agents`" in content
    assert "`POST /sessions`" in content
    assert "`POST /sessions/{session_id}/messages`" in content
    assert "`GET /sessions/{session_id}/messages`" in content
    assert "`POST /sessions/{session_id}/handoffs`" in content
    assert "실제로 Keryx 리소스를 만들거나 읽지 않았고" in content


def test_agent_setup_gateway_command_runs_gateway_section_and_records_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    agent_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    capsys.readouterr()
    hermes_home = get_agent_hermes_home(agent_id, {"HOME": str(tmp_path)})

    monkeypatch.setattr(
        cli_module.agent_setup_session,
        "run_agent_setup_session",
        lambda *, agent_id, agent_name, setup_target=None: cli_module.agent_setup_session.AgentSetupSessionResult(
            exit_code=0,
            hermes_home=hermes_home,
            setup_status="complete",
            gateway_setup_status="complete",
        ),
    )

    assert main(["agent", "setup-gateway", "planner"]) == 0
    captured = capsys.readouterr()
    assert "Gateway setup completed for 'planner'" in captured.out
    assert "maia agent start planner" in captured.out

    runtime_state = RuntimeStateStorage().load(get_state_db_path({"HOME": str(tmp_path)}))
    assert runtime_state[agent_id].to_dict() == {
        "agent_id": agent_id,
        "runtime_status": "stopped",
        "gateway_setup_status": "complete",
    }


def test_agent_setup_command_runs_hermes_setup_and_records_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    agent_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    capsys.readouterr()

    hermes_home = get_agent_hermes_home(agent_id, {"HOME": str(tmp_path)})

    monkeypatch.setattr(
        cli_module.agent_setup_session,
        "run_agent_setup_session",
        lambda *, agent_id, agent_name: cli_module.agent_setup_session.AgentSetupSessionResult(
            exit_code=0,
            hermes_home=hermes_home,
            setup_status="complete",
            gateway_setup_status="incomplete",
        ),
    )

    assert main(["agent", "setup", "planner"]) == 0
    captured = capsys.readouterr()
    assert "Agent setup completed for 'planner'" in captured.out
    assert str(hermes_home) in captured.out
    assert "run maia agent start planner" in captured.out
    assert "maia agent start planner" in captured.out
    assert captured.err == ""

    runtime_state = RuntimeStateStorage().load(get_state_db_path({"HOME": str(tmp_path)}))
    assert runtime_state[agent_id].to_dict() == {
        "agent_id": agent_id,
        "runtime_status": "stopped",
        "setup_status": "complete",
        "gateway_setup_status": "incomplete",
    }


def test_agent_setup_command_records_incomplete_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    agent_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    capsys.readouterr()

    hermes_home = get_agent_hermes_home(agent_id, {"HOME": str(tmp_path)})

    monkeypatch.setattr(
        cli_module.agent_setup_session,
        "run_agent_setup_session",
        lambda *, agent_id, agent_name: cli_module.agent_setup_session.AgentSetupSessionResult(
            exit_code=7,
            hermes_home=hermes_home,
            setup_status="incomplete",
            gateway_setup_status="incomplete",
        ),
    )

    assert main(["agent", "setup", "planner"]) == 7
    captured = capsys.readouterr()
    assert "Agent setup failed for 'planner'" in captured.err
    assert "maia agent setup planner" in captured.err
    assert captured.out == ""

    runtime_state = RuntimeStateStorage().load(get_state_db_path({"HOME": str(tmp_path)}))
    assert runtime_state[agent_id].to_dict() == {
        "agent_id": agent_id,
        "runtime_status": "stopped",
        "setup_status": "incomplete",
        "gateway_setup_status": "incomplete",
    }


def test_agent_setup_session_normalizes_signal_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module.agent_setup_session.shutil, "which", lambda name: "/tmp/fake-hermes")
    monkeypatch.setattr(
        cli_module.agent_setup_session.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], -2),
    )

    result = cli_module.agent_setup_session.run_agent_setup_session(
        agent_id="planner1234",
        agent_name="planner",
    )

    assert result.exit_code == 130
    assert result.setup_status == "incomplete"
    assert result.hermes_home == get_agent_hermes_home("planner1234", {"HOME": str(tmp_path)})


def test_agent_setup_session_restores_builtin_keryx_skill_after_setup_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_module.agent_setup_session.shutil, "which", lambda name: "/tmp/fake-hermes")

    def _run(command: list[str], *, env: dict[str, str], check: bool) -> subprocess.CompletedProcess[list[str]]:
        assert command == ["/tmp/fake-hermes", "setup"]
        skill_path = get_agent_keryx_skill_path("planner1234", {"HOME": str(tmp_path)})
        assert skill_path.exists()
        skill_path.unlink()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli_module.agent_setup_session.subprocess, "run", _run)

    result = cli_module.agent_setup_session.run_agent_setup_session(
        agent_id="planner1234",
        agent_name="planner",
    )

    skill_path = get_agent_keryx_skill_path("planner1234", {"HOME": str(tmp_path)})
    assert result.exit_code == 0
    assert skill_path.exists()
    assert "/keryx" in skill_path.read_text(encoding="utf-8")


def test_agent_setup_command_records_incomplete_when_hermes_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    agent_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    capsys.readouterr()
    monkeypatch.setattr(
        cli_module.agent_setup_session.shutil,
        "which",
        lambda name: None,
    )

    assert main(["agent", "setup", "planner"]) == 1
    captured = capsys.readouterr()
    assert "Agent setup failed for 'planner'" in captured.err
    assert "Hermes CLI was not found in PATH" in captured.err

    runtime_state = RuntimeStateStorage().load(get_state_db_path({"HOME": str(tmp_path)}))
    assert runtime_state[agent_id].to_dict() == {
        "agent_id": agent_id,
        "runtime_status": "stopped",
        "setup_status": "incomplete",
        "gateway_setup_status": "incomplete",
    }


def test_agent_start_backfills_missing_builtin_keryx_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    agent_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    capsys.readouterr()
    skill_path = get_agent_keryx_skill_path(agent_id, {"HOME": str(tmp_path)})
    skill_path.unlink()

    RuntimeStateStorage().save(
        get_state_db_path({"HOME": str(tmp_path)}),
        {
            agent_id: RuntimeState(
                agent_id=agent_id,
                runtime_status=RuntimeStatus.STOPPED,
                setup_status="complete",
                gateway_setup_status="complete",
            )
        },
    )
    monkeypatch.setattr(cli_module, "_require_shared_infra_ready", lambda agent_id: None)

    class _FakeRuntimeAdapter:
        def start(self, request: object) -> RuntimeStartResult:
            assert request.agent.agent_id == agent_id
            return RuntimeStartResult(
                runtime=RuntimeState(
                    agent_id=agent_id,
                    runtime_status=RuntimeStatus.RUNNING,
                    runtime_handle="container://planner",
                )
            )

    monkeypatch.setattr(cli_module, "_build_runtime_adapter", lambda: _FakeRuntimeAdapter())

    assert main(["agent", "start", "planner"]) == 0
    captured = capsys.readouterr()
    assert "updated agent_id=" in captured.out
    assert "runtime_status=running" in captured.out
    assert skill_path.exists()
    assert "/keryx" in skill_path.read_text(encoding="utf-8")


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
    assert "reset runtime/setup state" in captured.out
    assert "`maia import <path>` is the primary restore flow for Maia portable state." in captured.out
    assert (
        "Use `--preview` for a read-only diff, add `--verbose-preview` for full "
        "lists, and use `--yes` only when you want to skip overwrite confirmation."
    ) in captured.out
    assert "`maia inspect <path>`" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, IMPORT_EXAMPLES)


def test_inspect_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Read a .maia bundle, manifest.json" in captured.out
    assert "`maia inspect <path>` is optional support for looking at a snapshot before restore." in captured.out
    assert "The normal Part 3 flow is still `maia export` + safety-first `maia import <path>`." in captured.out
    assert "`maia inspect <path>` is the primary restore flow" not in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, INSPECT_EXAMPLES)


def test_export_help_includes_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["export", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Write a Maia bundle (.maia) or raw registry snapshot" in captured.out
    assert "path" in captured.out
    assert (
        "`maia export` writes the full Maia portable snapshot to "
        "`~/.maia/exports/maia-state.maia` by default."
    ) in captured.out
    assert (
        "Pass `[path]` to write the same snapshot to an explicit user/project "
        "bundle or raw registry path."
    ) in captured.out
    assert "`maia inspect <path>`" not in captured.out
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
    assert "Keryx-backed handoff pointers" in captured.out
    assert "workspace/runtime checks" in captured.out
    assert "add" in captured.out
    assert "list" in captured.out
    assert "show" in captured.out
    assert "Examples:" in captured.out
    _assert_contains_lines(captured.out, HANDOFF_EXAMPLES)
    assert "Phase 7" not in captured.out

def test_readme_examples_align_with_public_help() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "Hermes agents" not in readme
    assert "python -m maia" not in readme
    assert "Public examples use the installed `maia` entrypoint." in readme
    assert "## Part 1 operator flow" in readme
    assert "## What each command means" in readme
    assert "## Known limitations" in readme
    assert "## Secondary surfaces" in readme
    assert "## Part 2 visibility flow" in readme
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
    assert "Keryx is Maia's canonical collaboration root for live multi-agent work." in readme
    assert "Legacy broker-style `send`, `reply`, and `inbox` CLI entrypoints are removed from the active product contract." in readme
    assert "Keryx-backed operator views of open collaboration state" in readme
    assert "These remain public support workflows, but they are not the primary first-run bootstrap path." in readme
    assert "Portable state commands (`export`, `import`, `inspect`) remain available as operator support workflows." in readme
    assert "Keryx collaboration visibility commands (`thread`, `handoff`, `workspace`) remain available outside the Part 1 bootstrap story." in readme
    for line in PART2_VISIBILITY_FLOW:
        assert line in readme
    for line in RUNTIME_SUPPORT_BOUNDARY:
        assert line in readme
    for line in RUNTIME_RECOVERY_CHECKLIST:
        assert line in readme
    for line in V1_RELEASE_CHECKLIST:
        assert line in readme
    assert "Part 3 portable-state mental model: export all by default, export to an explicit path when you want a named user/project snapshot, then import safely with preview + confirm." in readme
    assert "`maia export` without an explicit path writes a Maia bundle archive to `~/.maia/exports/maia-state.maia`." in readme
    assert "`maia export [path] --label <label> --description <text>` lets the operator write a user/project snapshot to an explicit path while keeping the same bundle/import contract and overriding manifest metadata." in readme
    assert "`maia import <path>` always prints the preview/risk block first. When the current registry is non-empty or team-level portable metadata would be overwritten, it then performs a destructive-import preflight: warns about overwrite behavior and asks for confirmation." in readme
    assert "`maia import <path> --yes` skips the interactive confirmation but still prints the preview/risk summary and overwrite warning." in readme
    assert "`maia inspect <path>` is a secondary support command for pre-restore inspection; it is not required for the normal `maia export` + `maia import <path>` flow." in readme
    assert "Portable state: `maia export`, `maia inspect <path>`, `maia import <path>`" in readme
    assert "Primary Part 3 portable-state flow: `maia export`, `maia export <path>`, `maia import <path>`; use `maia inspect <path>` only as optional support when you want to inspect a snapshot before restore." in readme
    assert "Primary Part 3 portable-state flow: `maia export`, `maia inspect <path>`, `maia import <path>`" not in readme
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
    answers = iter([name, name, name])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert main(["agent", "new"]) == 0
    fields = _parse_fields(_line_with_prefix(capsys.readouterr().out, "created "))
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


def _keryx_service(home: Path) -> KeryxService:
    return KeryxService(get_state_db_path({"HOME": str(home)}))


def _seed_keryx_thread(
    home: Path,
    *,
    thread_id: str,
    topic: str,
    participants: list[str],
    created_by: str,
    status: KeryxSessionStatus = KeryxSessionStatus.ACTIVE,
    created_at: str,
    updated_at: str,
) -> KeryxSessionRecord:
    thread = KeryxSessionRecord(
        session_id=thread_id,
        topic=topic,
        participants=participants,
        created_by=created_by,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )
    return _keryx_service(home).create_session(thread)


def _seed_keryx_message(
    home: Path,
    *,
    message_id: str,
    thread_id: str,
    from_agent: str,
    to_agent: str,
    kind: str,
    body: str,
    created_at: str,
    reply_to_message_id: str | None = None,
) -> KeryxMessageRecord:
    message = KeryxMessageRecord(
        message_id=message_id,
        session_id=thread_id,
        from_agent=from_agent,
        to_agent=to_agent,
        kind=kind,
        body=body,
        created_at=created_at,
        reply_to_message_id=reply_to_message_id,
    )
    return _keryx_service(home).create_session_message(thread_id, message)


def _seed_keryx_handoff(
    home: Path,
    *,
    handoff_id: str,
    thread_id: str,
    from_agent: str,
    to_agent: str,
    kind: str,
    summary: str,
    location: str,
    created_at: str,
    updated_at: str | None = None,
    status: KeryxHandoffStatus = KeryxHandoffStatus.OPEN,
) -> KeryxHandoffRecord:
    handoff = KeryxHandoffRecord(
        handoff_id=handoff_id,
        session_id=thread_id,
        from_agent=from_agent,
        to_agent=to_agent,
        kind=kind,
        status=status,
        summary=summary,
        location=location,
        created_at=created_at,
        updated_at=created_at if updated_at is None else updated_at,
    )
    return _keryx_service(home).create_thread_handoff(thread_id, handoff)

def test_handoff_add_list_and_show_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

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
    thread_id = "sess-seeded"
    _seed_keryx_thread(
        tmp_path,
        thread_id=thread_id,
        topic="review handoff",
        participants=[planner_id, reviewer_id],
        created_by=planner_id,
        created_at="2026-04-15T12:00:00Z",
        updated_at="2026-04-15T12:00:00Z",
    )

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

    handoffs = _keryx_service(tmp_path).list_thread_handoffs(thread_id)
    assert len(handoffs) == 1
    assert handoffs[0].handoff_id == handoff_id
    assert handoffs[0].thread_id == thread_id

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

def test_handoff_add_rejects_non_participant_agents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    analyst_id = _create_agent(monkeypatch, capsys, tmp_path, "analyst")
    thread_id = "sess-seeded"
    _seed_keryx_thread(
        tmp_path,
        thread_id=thread_id,
        topic="review handoff",
        participants=[planner_id, reviewer_id],
        created_by=planner_id,
        created_at="2026-04-15T12:00:00Z",
        updated_at="2026-04-15T12:00:00Z",
    )

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

    service = _keryx_service(tmp_path)
    assert service.list_thread_handoffs(thread_id) == []
    assert service.get_thread(thread_id).participants == [planner_id, reviewer_id]


def test_handoff_list_rejects_unknown_thread_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert main(["handoff", "list", "--thread-id", "missing-thread"]) == 1
    captured = capsys.readouterr()
    assert "Keryx thread with id 'missing-thread' not found" in captured.err


def test_thread_list_and_show_surface_control_plane_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    state_db_path = get_state_db_path({"HOME": str(tmp_path)})
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-001",
        topic="review handoff",
        participants=["planner", "reviewer"],
        created_by="planner",
        created_at="2026-04-15T12:00:00Z",
        updated_at="2026-04-15T12:02:00Z",
    )
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-002",
        topic="retro wrap-up",
        participants=["planner", "analyst"],
        created_by="planner",
        status=KeryxSessionStatus.CLOSED,
        created_at="2026-04-15T10:30:00Z",
        updated_at="2026-04-15T11:00:00Z",
    )
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-003",
        topic="colon identity",
        participants=["agent:1"],
        created_by="agent:1",
        created_at="2026-04-15T09:00:00Z",
        updated_at="2026-04-15T09:00:00Z",
    )
    _seed_keryx_message(
        tmp_path,
        message_id="msg-002",
        thread_id="sess-001",
        from_agent="reviewer",
        to_agent="planner",
        kind="answer",
        body="latest update",
        created_at="2026-04-15T12:02:00Z",
        reply_to_message_id="msg-001",
    )
    _seed_keryx_message(
        tmp_path,
        message_id="msg-001",
        thread_id="sess-001",
        from_agent="planner",
        to_agent="reviewer",
        kind="request",
        body="first ask",
        created_at="2026-04-15T12:00:00Z",
    )
    _seed_keryx_message(
        tmp_path,
        message_id="msg-003",
        thread_id="sess-002",
        from_agent="planner",
        to_agent="analyst",
        kind="note",
        body="closed context",
        created_at="2026-04-15T11:00:00Z",
    )
    _seed_keryx_handoff(
        tmp_path,
        handoff_id="artifact-001",
        thread_id="sess-001",
        from_agent="planner",
        to_agent="reviewer",
        kind="report",
        location="reports/review.md",
        summary="Review notes ready",
        created_at="2026-04-15T12:01:00Z",
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
    assert open_fields["thread_id"] == "sess-001"
    assert open_fields["topic"] == "review␠handoff"
    assert open_fields["participants"] == "planner,reviewer"
    assert open_fields["participant_runtime"] == "planner:running,reviewer:stopped"
    assert open_fields["status"] == "open"
    assert open_fields["updated_at"] == "2026-04-15T12:02:00Z"
    assert open_fields["pending_on"] == "planner"
    assert open_fields["delegated_to"] == "reviewer"
    assert open_fields["delegation_status"] == "answered"
    assert open_fields["current_thread_id"] == "sess-001"
    assert open_fields["latest_internal_update"] == "reviewer␠answer:␠latest␠update"
    assert open_fields["handoffs"] == "1"
    assert open_fields["messages"] == "2"
    assert open_fields["recent_handoff_id"] == "artifact-001"
    assert open_fields["recent_handoff_to"] == "reviewer"
    assert open_fields["recent_handoff_type"] == "report"
    assert open_fields["recent_handoff_summary"] == "Review␠notes␠ready"
    closed_fields = _parse_fields(list_lines[1])
    assert closed_fields["thread_id"] == "sess-002"
    assert closed_fields["participant_runtime"] == "planner:running,analyst:failed"
    assert closed_fields["recent_handoff_id"] == "-"
    assert closed_fields["recent_handoff_to"] == "-"
    assert closed_fields["recent_handoff_type"] == "-"
    assert closed_fields["recent_handoff_summary"] == "-"
    colon_fields = _parse_fields(list_lines[2])
    assert colon_fields["thread_id"] == "sess-003"
    assert colon_fields["participant_runtime"] == "agent%3A1:stopped"
    assert colon_fields["pending_on"] == "-"
    assert colon_fields["delegated_to"] == "-"
    assert colon_fields["delegation_status"] == "-"
    assert colon_fields["recent_handoff_id"] == "-"

    assert main(["thread", "list", "--agent", "reviewer"]) == 0
    reviewer_lines = capsys.readouterr().out.strip().splitlines()
    assert len(reviewer_lines) == 1
    assert _parse_fields(reviewer_lines[0])["thread_id"] == "sess-001"

    assert main(["thread", "list", "--status", "closed"]) == 0
    closed_lines = capsys.readouterr().out.strip().splitlines()
    assert len(closed_lines) == 1
    assert _parse_fields(closed_lines[0])["thread_id"] == "sess-002"

    assert main(["thread", "show", "sess-001"]) == 0
    show_lines = capsys.readouterr().out.strip().splitlines()
    assert len(show_lines) == 3
    show_fields = _parse_fields(show_lines[0])
    assert show_fields["thread_id"] == "sess-001"
    assert show_fields["participant_runtime"] == "planner:running,reviewer:stopped"
    assert show_fields["pending_on"] == "planner"
    assert show_fields["delegated_to"] == "reviewer"
    assert show_fields["delegation_status"] == "answered"
    assert show_fields["current_thread_id"] == "sess-001"
    assert show_fields["latest_internal_update"] == "reviewer␠answer:␠latest␠update"
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

    with pytest.raises(SystemExit) as exc_info:
        main(["thread", "sess-001", "--limit", "1"])
    assert exc_info.value.code == 2


def test_thread_visibility_uses_sqlite_state_even_if_runtime_json_cache_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    state_db_path = get_state_db_path({"HOME": str(tmp_path)})
    runtime_state_path = get_runtime_state_path({"HOME": str(tmp_path)})
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-invalid-runtime",
        topic="runtime fallback",
        participants=["planner"],
        created_by="planner",
        created_at="2026-04-15T08:00:00Z",
        updated_at="2026-04-15T08:00:00Z",
    )
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_path.write_text("{bad json\n", encoding="utf-8")

    assert main(["thread", "list"]) == 0
    fields = _parse_fields(capsys.readouterr().out.strip())
    assert fields["thread_id"] == "sess-invalid-runtime"
    assert fields["participant_runtime"] == "planner:stopped"
    assert fields["pending_on"] == "-"
    assert fields["delegated_to"] == "-"
    assert fields["delegation_status"] == "-"


def test_thread_show_preserves_message_order_when_timestamps_tie(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    thread_id = "sess-tie"
    first_message_id = "msg-1"
    reply_message_id = "msg-2"
    _seed_keryx_thread(
        tmp_path,
        thread_id=thread_id,
        topic="review handoff",
        participants=[planner_id, reviewer_id],
        created_by=planner_id,
        created_at="2026-04-15T12:00:00Z",
        updated_at="2026-04-15T12:00:00Z",
    )
    _seed_keryx_message(
        tmp_path,
        message_id=first_message_id,
        thread_id=thread_id,
        from_agent=planner_id,
        to_agent=reviewer_id,
        kind="request",
        body="please review the latest patch",
        created_at="2026-04-15T12:00:00Z",
    )
    _seed_keryx_message(
        tmp_path,
        message_id=reply_message_id,
        thread_id=thread_id,
        from_agent=reviewer_id,
        to_agent=planner_id,
        kind="answer",
        body="review complete",
        created_at="2026-04-15T12:00:00Z",
        reply_to_message_id=first_message_id,
    )

    assert main(["thread", "show", thread_id]) == 0
    thread_lines = capsys.readouterr().out.strip().splitlines()
    thread_fields = _parse_fields(thread_lines[0])
    first_message_fields = _parse_fields(thread_lines[1])
    second_message_fields = _parse_fields(thread_lines[2])

    assert thread_fields["pending_on"] == planner_id
    assert thread_fields["delegated_to"] == reviewer_id
    assert thread_fields["delegation_status"] == "answered"
    assert thread_fields["current_thread_id"] == thread_id
    assert thread_fields["latest_internal_update"] == f"{reviewer_id}␠answer:␠review␠complete"
    assert first_message_fields["message_id"] == first_message_id
    assert second_message_fields["message_id"] == reply_message_id
    assert second_message_fields["reply_to_message_id"] == first_message_id

def test_thread_delegation_status_prefers_newer_message_over_older_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")

    state_db_path = get_state_db_path({"HOME": str(tmp_path)})
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-stale-handoff",
        topic="delegation freshness",
        participants=[planner_id, reviewer_id],
        created_by=planner_id,
        created_at="2026-04-17T12:00:00Z",
        updated_at="2026-04-17T12:04:00Z",
    )
    _seed_keryx_message(
        tmp_path,
        message_id="msg-new-request",
        thread_id="sess-stale-handoff",
        from_agent=planner_id,
        to_agent=reviewer_id,
        kind="request",
        body="Please continue with v2.",
        created_at="2026-04-17T12:04:00Z",
    )
    _seed_keryx_handoff(
        tmp_path,
        handoff_id="handoff-old",
        thread_id="sess-stale-handoff",
        from_agent=reviewer_id,
        to_agent=planner_id,
        kind="report",
        location="reports/v1.md",
        summary="V1 ready",
        created_at="2026-04-17T12:03:00Z",
    )

    assert main(["thread", "show", "sess-stale-handoff"]) == 0
    fields = _parse_fields(capsys.readouterr().out.strip().splitlines()[0])
    assert fields["delegated_to"] == reviewer_id
    assert fields["delegation_status"] == "pending"
    assert fields["latest_internal_update"] == f"{planner_id}␠request:␠Please␠continue␠with␠v2."


def test_thread_without_internal_events_does_not_fabricate_delegation_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    state_db_path = get_state_db_path({"HOME": str(tmp_path)})
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-no-events",
        topic="empty delegation",
        participants=["planner", "reviewer"],
        created_by="planner",
        created_at="2026-04-17T12:00:00Z",
        updated_at="2026-04-17T12:00:00Z",
    )

    assert main(["thread", "show", "sess-no-events"]) == 0
    fields = _parse_fields(capsys.readouterr().out.strip().splitlines()[0])
    assert fields["delegated_to"] == "-"
    assert fields["delegation_status"] == "-"
    assert fields["latest_internal_update"] == "-"


def test_latest_internal_update_truncates_long_internal_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    planner_id = _create_agent(monkeypatch, capsys, tmp_path, "planner")
    reviewer_id = _create_agent(monkeypatch, capsys, tmp_path, "reviewer")
    long_body = "This is a very long internal update that should be summarized before it reaches lightweight delegation status output."
    _seed_keryx_thread(
        tmp_path,
        thread_id="sess-long",
        topic="delegation truncation",
        participants=[planner_id, reviewer_id],
        created_by=planner_id,
        created_at="2026-04-15T12:00:00Z",
        updated_at="2026-04-15T12:00:00Z",
    )
    _seed_keryx_message(
        tmp_path,
        message_id="msg-long",
        thread_id="sess-long",
        from_agent=planner_id,
        to_agent=reviewer_id,
        kind="request",
        body=long_body,
        created_at="2026-04-15T12:00:00Z",
    )

    assert main(["thread", "show", "sess-long"]) == 0
    fields = _parse_fields(capsys.readouterr().out.strip().splitlines()[0])
    assert fields["delegation_status"] == "pending"
    assert fields["latest_internal_update"].startswith(f"{planner_id}␠request:␠This␠is␠a␠very␠long␠internal␠update")
    assert fields["latest_internal_update"].endswith("…")


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
