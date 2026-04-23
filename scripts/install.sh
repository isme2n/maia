#!/usr/bin/env bash

set -euo pipefail

MAIA_INSTALL_REPO_URL="${MAIA_INSTALL_REPO_URL:-https://github.com/isme2n/maia.git}"
MAIA_INSTALL_REF="${MAIA_INSTALL_REF:-v0.1.0}"
MAIA_INSTALL_PACKAGE="${MAIA_INSTALL_PACKAGE:-maia}"
MAIA_INSTALL_COMMAND="${MAIA_INSTALL_COMMAND:-maia}"
UV_INSTALL_URL="${UV_INSTALL_URL:-https://astral.sh/uv/install.sh}"
HERMES_INSTALL_URL="${HERMES_INSTALL_URL:-https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh}"
DRY_RUN=0

usage() {
    cat <<'EOF'
Maia installer

Usage: install.sh [--dry-run] [--help]

Install Maia on macOS/Linux with uv, ensure Hermes is available for `maia init`,
and print truthful next steps when installation finishes.

Options:
  --dry-run  Print the actions without changing the machine
  --help     Show this help

Environment overrides:
  MAIA_INSTALL_REPO_URL  Git repo to install Maia from
  MAIA_INSTALL_REF       Git ref to install (default: v0.1.0)
  MAIA_INSTALL_PACKAGE   Tool name to install from the Maia repo (default: maia)
  UV_INSTALL_URL         uv installer URL
  HERMES_INSTALL_URL     Hermes installer URL
EOF
}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'WARNING: %s\n' "$*"
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

have_command() {
    command -v "$1" >/dev/null 2>&1
}

refresh_path() {
    PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    export PATH
}

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '+'
        while [ "$#" -gt 0 ]; do
            printf ' %q' "$1"
            shift
        done
        printf '\n'
        return 0
    fi

    "$@"
}

run_installer_script() {
    local url="$1"

    if have_command curl; then
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '+ curl -LsSf %q | bash\n' "$url"
            return 0
        fi
        curl -LsSf "$url" | bash
        return 0
    fi

    if have_command wget; then
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '+ wget -qO- %q | bash\n' "$url"
            return 0
        fi
        wget -qO- "$url" | bash
        return 0
    fi

    die "Need curl or wget to download ${url}"
}

detect_platform() {
    local kernel
    kernel="${MAIA_INSTALL_OS_OVERRIDE:-$(uname -s)}"

    case "$kernel" in
        Linux)
            log "Detected Linux."
            ;;
        Darwin)
            log "Detected macOS."
            ;;
        CYGWIN*|MINGW*|MSYS*)
            die "Windows is not supported by this installer. Use WSL2 or a Linux/macOS shell."
            ;;
        *)
            die "Unsupported operating system: ${kernel}. This installer supports macOS and Linux only."
            ;;
    esac
}

ensure_uv() {
    refresh_path
    if have_command uv; then
        log "uv already available at $(command -v uv)"
        return 0
    fi

    log "uv not found. Installing uv."
    run_installer_script "$UV_INSTALL_URL"
    refresh_path

    if [ "$DRY_RUN" -eq 1 ]; then
        return 0
    fi

    if ! have_command uv; then
        die "uv installation finished, but \`uv\` is still not available on PATH."
    fi

    log "uv available at $(command -v uv)"
}

maia_repo_spec() {
    local repo
    repo="$MAIA_INSTALL_REPO_URL"
    case "$repo" in
        git+*)
            ;;
        *)
            repo="git+$repo"
            ;;
    esac

    if [ -n "$MAIA_INSTALL_REF" ]; then
        printf '%s@%s\n' "$repo" "$MAIA_INSTALL_REF"
        return 0
    fi

    printf '%s\n' "$repo"
}

uv_supports_tool_install_from() {
    if [ "$DRY_RUN" -eq 1 ]; then
        return 0
    fi

    uv tool install --help 2>/dev/null | grep -q -- '--from'
}

install_maia() {
    local repo_spec
    repo_spec="$(maia_repo_spec)"

    log "Installing Maia from ${repo_spec}"

    if ! uv_supports_tool_install_from; then
        die "This installer requires a uv build that supports 'uv tool install --from'. Please upgrade uv and rerun the installer."
    fi

    run uv tool install --reinstall --from "$repo_spec" "$MAIA_INSTALL_PACKAGE"
}

resolve_command_path() {
    local name="$1"
    local path=""
    local bin_dir=""

    if path="$(command -v "$name" 2>/dev/null)"; then
        printf '%s\n' "$path"
        return 0
    fi

    if have_command uv; then
        bin_dir="$(uv tool dir --bin 2>/dev/null || true)"
        if [ -n "$bin_dir" ] && [ -x "$bin_dir/$name" ]; then
            printf '%s\n' "$bin_dir/$name"
            return 0
        fi
    fi

    if [ -x "$HOME/.local/bin/$name" ]; then
        printf '%s\n' "$HOME/.local/bin/$name"
        return 0
    fi

    if [ -x "$HOME/.cargo/bin/$name" ]; then
        printf '%s\n' "$HOME/.cargo/bin/$name"
        return 0
    fi

    return 1
}

ensure_hermes() {
    local hermes_path=""

    refresh_path
    if hermes_path="$(resolve_command_path hermes)"; then
        log "Hermes already available at ${hermes_path}"
        return 0
    fi

    log "Hermes not found. Installing Hermes."
    run_installer_script "$HERMES_INSTALL_URL"
    refresh_path

    if [ "$DRY_RUN" -eq 1 ]; then
        return 0
    fi

    if ! hermes_path="$(resolve_command_path hermes)"; then
        die "Hermes installation finished, but \`hermes\` is still not available."
    fi

    log "Hermes available at ${hermes_path}"
}

verify_maia_command() {
    local maia_path=""

    refresh_path
    if ! maia_path="$(resolve_command_path "$MAIA_INSTALL_COMMAND")"; then
        die "Maia installation finished, but \`${MAIA_INSTALL_COMMAND}\` could not be found."
    fi

    if [ ! -x "$maia_path" ]; then
        die "Maia installation finished, but \`${maia_path}\` is not executable."
    fi

    if ! "$maia_path" --help >/dev/null 2>&1; then
        die "Maia installation finished, but \`${MAIA_INSTALL_COMMAND} --help\` failed."
    fi

    if ! have_command "$MAIA_INSTALL_COMMAND"; then
        warn "\`${MAIA_INSTALL_COMMAND}\` exists at ${maia_path} but is not on PATH in this shell."
        warn "Run \`export PATH=\"$(dirname "$maia_path"):\$PATH\"\` or \`uv tool update-shell\` before \`${MAIA_INSTALL_COMMAND} init\`."
    else
        log "Maia command verified at ${maia_path}"
    fi
}

warn_if_docker_unready() {
    if ! have_command docker; then
        warn "Docker CLI not found. \`maia init\` can still continue, but runtime control requires Docker CLI and a reachable Docker daemon."
        return 0
    fi

    if docker info >/dev/null 2>&1; then
        log "Docker CLI and daemon look reachable."
        return 0
    fi

    warn "Docker CLI is installed, but the Docker daemon is not reachable right now. \`maia init\` may still continue until runtime control needs Docker."
}

print_next_steps() {
    log ""
    log "Next step:"
    log "  maia init"
    log ""
    log "Maia keeps \`maia init\` as the canonical onboarding command after installation."
}

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --dry-run)
                DRY_RUN=1
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
        shift
    done
}

main() {
    parse_args "$@"
    refresh_path
    detect_platform
    ensure_uv
    install_maia
    ensure_hermes

    if [ "$DRY_RUN" -eq 1 ]; then
        log "Dry run only: skipped post-install command verification."
        print_next_steps
        return 0
    fi

    verify_maia_command
    warn_if_docker_unready
    print_next_steps
}

main "$@"
