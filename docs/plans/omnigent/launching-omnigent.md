# Launching upstream Omnigent (dev reference — Linux only)

> Rescued from the superseded `omnigent-shell-integration` plan README when that folder was
> removed (2026-07-02). Omnigent is **not** part of the product (see
> [2026-07-02-agent-first-dashboard-design.md](../2026-07-02-agent-first-dashboard-design.md) —
> Hermes brain, Clerk shell). These instructions launch the standalone upstream Omnigent CLI as
> validated in the Phase 0 spike ([spike-notes.md](./spike-notes.md)), useful for borrowing its
> chat UI as a visual spec. Runtime is **Linux only** (needs `tmux` + `bubblewrap`); Windows is
> dev-only. On this box, "Linux" == WSL2 Ubuntu 24.04.

```powershell
# From Windows PowerShell — open Linux (WSL2 Ubuntu). Install first if missing:
#   wsl --install -d Ubuntu-24.04
wsl -d Ubuntu-24.04
```

Then, at the Ubuntu shell prompt:

```sh
# 1. Install (bootstrap; installs uv + bubblewrap, binary → ~/.local/bin/omnigent)
curl -fsSL https://raw.githubusercontent.com/omnigent-ai/omnigent/main/scripts/install_oss.sh | sh

# 2. Configure the brain — should report "gpt-5.5 (via OpenAI Codex)" ✓
omnigent setup

# 3. Start the web UI (headless; binds http://127.0.0.1:6767)
omnigent server --no-open

# 4. Register an execution host — REQUIRED, else the UI shows "No hosts"
omnigent host --server http://localhost:6767

# 5. The actual Hermes reasoning path (keyless ChatGPT-subscription brain)
omnigent hermes
```

The three long-running commands (server, host, hermes) each need their own WSL shell (or tmux pane).
Open `http://localhost:6767` in the Windows browser (WSL2 loopback makes it reachable).

**Gotchas:** use `omnigent hermes` (not the web chat's harness picker — those want API keys; our
ChatGPT OAuth only works via Hermes' `openai-codex` provider). Pass `--no-open`/`--no-browser` and
open URLs manually — WSL's `gio` can't auto-launch a browser.
