from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

import sys
sys.path.insert(0, str(SRC_ROOT))

from maia.public_contract import MAIA_GIT_INSTALL_SPEC, MAIA_INSTALL_REF

INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"


def _run_install_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", str(INSTALL_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        env=merged_env,
        cwd=REPO_ROOT,
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_install_script_help_describes_contract() -> None:
    result = _run_install_script("--help")

    assert result.returncode == 0
    assert "Maia installer" in result.stdout
    assert "Usage: install.sh [--dry-run] [--help]" in result.stdout
    assert "ensure Hermes is available for `maia init`" in result.stdout
    assert "--dry-run" in result.stdout
    assert "MAIA_INSTALL_REPO_URL" in result.stdout
    assert f"MAIA_INSTALL_REF       Git ref to install (default: {MAIA_INSTALL_REF})" in result.stdout
    assert "HERMES_INSTALL_URL" in result.stdout


def test_install_script_dry_run_prints_primary_install_flow(tmp_path: Path) -> None:
    result = _run_install_script(
        "--dry-run",
        env={
            "HOME": str(tmp_path),
            "PATH": "/usr/bin:/bin",
            "MAIA_INSTALL_OS_OVERRIDE": "Linux",
        },
    )

    assert result.returncode == 0
    stdout = result.stdout
    assert "Detected Linux." in stdout
    assert "uv not found. Installing uv." in stdout
    assert "+ curl -LsSf https://astral.sh/uv/install.sh | bash" in stdout
    assert "Installing Maia from git+https://github.com/isme2n/maia.git@v0.1.0" in stdout
    assert "+ uv tool install --reinstall --from git+https://github.com/isme2n/maia.git@v0.1.0 maia" in stdout
    assert "Hermes not found. Installing Hermes." in stdout
    assert "+ curl -LsSf https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash" in stdout
    assert "Dry run only: skipped post-install command verification." in stdout
    assert "Next step:" in stdout
    assert "  maia init" in stdout
    assert "Maia keeps `maia init` as the canonical onboarding command after installation." in stdout


def test_install_script_runs_post_install_verification_and_docker_warning(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_executable(
        bin_dir / "uv",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "mkdir -p \"$HOME/.local/bin\"\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"install\" ] && [ \"${3:-}\" = \"--help\" ]; then\n"
        "  printf '  --from\\n'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"install\" ]; then\n"
        "  cat > \"$HOME/.local/bin/maia\" <<'EOF'\n"
        "#!/usr/bin/env bash\n"
        "echo stub maia\n"
        "EOF\n"
        "  chmod +x \"$HOME/.local/bin/maia\"\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"dir\" ] && [ \"${3:-}\" = \"--bin\" ]; then\n"
        "  printf '%s\\n' \"$HOME/.local/bin\"\n"
        "  exit 0\n"
        "fi\n"
        "echo \"unexpected uv args: $*\" >&2\n"
        "exit 1\n",
    )
    _write_executable(
        bin_dir / "curl",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "url=\"${@: -1}\"\n"
        "case \"$url\" in\n"
        "  *NousResearch/hermes-agent/main/scripts/install.sh)\n"
        "    cat <<'EOF'\n"
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "mkdir -p \"$HOME/.local/bin\"\n"
        "cat > \"$HOME/.local/bin/hermes\" <<'EOH'\n"
        "#!/usr/bin/env bash\n"
        "echo stub hermes\n"
        "EOH\n"
        "chmod +x \"$HOME/.local/bin/hermes\"\n"
        "EOF\n"
        "    ;;\n"
        "  *)\n"
        "    echo \"unexpected curl url: $url\" >&2\n"
        "    exit 1\n"
        "    ;;\n"
        "esac\n",
    )
    _write_executable(
        bin_dir / "docker",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [ \"${1:-}\" = \"info\" ]; then\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n",
    )

    result = _run_install_script(
        env={
            "HOME": str(tmp_path),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "MAIA_INSTALL_OS_OVERRIDE": "Linux",
        }
    )

    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    assert "Detected Linux." in stdout
    assert f"uv already available at {bin_dir / 'uv'}" in stdout
    assert f"Installing Maia from {MAIA_GIT_INSTALL_SPEC}" in stdout
    assert "Hermes not found. Installing Hermes." in stdout
    assert f"Hermes available at {tmp_path / '.local' / 'bin' / 'hermes'}" in stdout
    assert f"Maia command verified at {tmp_path / '.local' / 'bin' / 'maia'}" in stdout
    assert "WARNING: Docker CLI is installed, but the Docker daemon is not reachable right now." in stdout
    assert "Next step:" in stdout
    assert "  maia init" in stdout
    assert (tmp_path / ".local" / "bin" / "maia").exists()
    assert (tmp_path / ".local" / "bin" / "hermes").exists()


def test_install_script_requires_uv_with_tool_install_from_support(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_executable(
        bin_dir / "uv",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"install\" ] && [ \"${3:-}\" = \"--help\" ]; then\n"
        "  printf 'usage: uv tool install\\n'\n"
        "  exit 0\n"
        "fi\n"
        "echo \"unexpected uv args: $*\" >&2\n"
        "exit 1\n",
    )

    result = _run_install_script(
        env={
            "HOME": str(tmp_path),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "MAIA_INSTALL_OS_OVERRIDE": "Linux",
        }
    )

    assert result.returncode == 1
    assert "requires a uv build that supports 'uv tool install --from'" in result.stderr


def test_install_script_fails_when_installed_maia_command_is_broken(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_executable(
        bin_dir / "uv",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "mkdir -p \"$HOME/.local/bin\"\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"install\" ] && [ \"${3:-}\" = \"--help\" ]; then\n"
        "  printf '  --from\\n'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"install\" ]; then\n"
        "  cat > \"$HOME/.local/bin/maia\" <<'EOF'\n"
        "#!/usr/bin/env bash\n"
        "exit 1\n"
        "EOF\n"
        "  chmod +x \"$HOME/.local/bin/maia\"\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"tool\" ] && [ \"$2\" = \"dir\" ] && [ \"${3:-}\" = \"--bin\" ]; then\n"
        "  printf '%s\\n' \"$HOME/.local/bin\"\n"
        "  exit 0\n"
        "fi\n"
        "echo \"unexpected uv args: $*\" >&2\n"
        "exit 1\n",
    )
    _write_executable(
        bin_dir / "curl",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "cat <<'EOF'\n"
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "mkdir -p \"$HOME/.local/bin\"\n"
        "cat > \"$HOME/.local/bin/hermes\" <<'EOH'\n"
        "#!/usr/bin/env bash\n"
        "echo stub hermes\n"
        "EOH\n"
        "chmod +x \"$HOME/.local/bin/hermes\"\n"
        "EOF\n",
    )

    result = _run_install_script(
        env={
            "HOME": str(tmp_path),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "MAIA_INSTALL_OS_OVERRIDE": "Linux",
        }
    )

    assert result.returncode == 1
    assert "`maia --help` failed." in result.stderr


def test_install_script_rejects_unsupported_platform(tmp_path: Path) -> None:
    result = _run_install_script(
        env={
            "HOME": str(tmp_path),
            "MAIA_INSTALL_OS_OVERRIDE": "Plan9",
        }
    )

    assert result.returncode == 1
    assert "Unsupported operating system: Plan9. This installer supports macOS and Linux only." in result.stderr


def test_install_script_source_locks_primary_urls_and_commands() -> None:
    text = INSTALL_SCRIPT.read_text(encoding="utf-8")

    assert 'MAIA_INSTALL_REPO_URL="${MAIA_INSTALL_REPO_URL:-https://github.com/isme2n/maia.git}"' in text
    assert f'MAIA_INSTALL_REF="${{MAIA_INSTALL_REF:-{MAIA_INSTALL_REF}}}"' in text
    assert 'HERMES_INSTALL_URL="${HERMES_INSTALL_URL:-https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh}"' in text
    assert 'run uv tool install --reinstall --from "$repo_spec" "$MAIA_INSTALL_PACKAGE"' in text
    assert "requires a uv build that supports 'uv tool install --from'" in text
    assert 'if ! "$maia_path" --help >/dev/null 2>&1; then' in text
    assert 'run_installer_script "$HERMES_INSTALL_URL"' in text
    assert 'warn "Docker CLI is installed, but the Docker daemon is not reachable right now.' in text
    assert 'log "  maia init"' in text
