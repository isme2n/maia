from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_invariants.py"


def _run_check(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_contract_check_passes_for_repo() -> None:
    result = _run_check("contracts")

    assert result.returncode == 0, result.stderr
    assert "Maia contract check passed." in result.stdout


def test_policy_scan_reports_legacy_like_findings_without_failing_by_default(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def load_state():\n"
        "    legacy shadow path\n"
        "    return 'fallback'\n",
        encoding="utf-8",
    )

    result = _run_check("scan", str(tmp_path))

    assert result.returncode == 0
    assert "[legacy-shadow-path]" in result.stdout
    assert "[silent-fallback]" in result.stdout


def test_policy_scan_can_fail_on_findings(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("transitional-json-cache\n", encoding="utf-8")

    result = _run_check("scan", str(tmp_path), "--fail-on-findings")

    assert result.returncode == 1
    assert "[dual-write]" in result.stdout



def test_current_collaboration_surface_avoids_legacy_model_imports() -> None:
    active_surface_files = [
        REPO_ROOT / "src" / "maia" / "agent_context.py",
        REPO_ROOT / "src" / "maia" / "hermes_runtime_worker.py",
        REPO_ROOT / "src" / "maia" / "cli_parser.py",
    ]

    joined = "\n".join(path.read_text(encoding="utf-8") for path in active_surface_files)

    assert "from maia.message_model import" not in joined
    assert "from maia.handoff_model import" not in joined



def test_architecture_doc_does_not_reference_removed_legacy_models() -> None:
    architecture = (REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "src/maia/message_model.py" not in architecture
    assert "src/maia/handoff_model.py" not in architecture
