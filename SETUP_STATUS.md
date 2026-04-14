# Maia setup status

Prepared on this server for Codex-driven development.

## Ready
- Codex CLI installed and working (`codex-cli 0.120.0`)
- OpenAI API key present
- Git repository initialized at `/home/asle/maia`
- Default branch renamed to `main`

## Blockers to finish full Maia runtime setup
- Docker is not installed on this server
- `docker compose` is therefore unavailable
- Git user name/email are not configured, so the initial commit could not be created yet

## Verified Codex smoke test
Run from `/home/asle/maia`:

```bash
codex exec 'Reply with READY and nothing else.'
```

This already succeeds.

## Recommended next steps
1. Configure git identity for this machine or this repo.
2. Install Docker Engine + Docker Compose plugin.
3. Have Codex scaffold the initial Maia repo structure and CLI.
