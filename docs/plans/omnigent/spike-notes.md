# Omnigent Linux Spike Notes

Date: 2026-07-01

Status: **PASSED.** A Hermes-backed turn ran end-to-end on the ChatGPT
subscription, on Linux, through Omnigent (`omnigent hermes`). R1 + R2 de-risked.
Do proceed to Phase 1.

## Goal

Prove a vanilla Omnigent session can run with Hermes on the Linux target, on the
user's ChatGPT subscription, before vendoring Omnigent or changing Clerk code.

## Linux Target

- **WSL2 Ubuntu 24.04** (installed fresh via `wsl --install -d Ubuntu-24.04`) on a
  Windows 10 dev box. WSL 2.7.10, kernel 6.18. Counts as the R2 Linux surface for
  the spike; final production validation should still happen on the real
  VPS/Docker deploy host.
- `localhost` is shared with Windows, so the web UI at `127.0.0.1:6767` and all
  OAuth loopback callbacks are reachable from the Windows browser.

## Versions / Install

- **Hermes** `v0.17.0`, provider `openai-codex`, model `gpt-5.5`
  (see [hermes-provider-decision.md](./hermes-provider-decision.md)).
- **Omnigent** `0.3.0`, installed via the bootstrap:
  `curl -fsSL https://raw.githubusercontent.com/omnigent-ai/omnigent/main/scripts/install_oss.sh | sh`
  (prompts to install `uv`; found `node`/`npm`/`tmux`; installs `bubblewrap`).
  Binary → `~/.local/bin/omnigent`.
- `omnigent setup` detected the Codex OAuth credential:
  `Default model set to: gpt-5.5 (via OpenAI Codex)` — `OpenAI Codex credentials: ✓`.
  **This is the Task 0.2 "omnigent setup shows Hermes ready" acceptance.**

## Web server / UI

- Launched with `omnigent server --no-open` (foreground; `--no-open` for
  headless — WSL can't auto-open a browser). Binds `http://127.0.0.1:6767`.
- **No accounts/login prompt** — single-user local mode. Loaded cleanly in the
  Windows browser at `http://localhost:6767`.
- `chat.db` → `/home/bennyclifton/.omnigent/chat.db`;
  artifacts → `~/.omnigent/artifacts`; logs → `~/.omnigent/logs/`.
- Omnigent needs an execution **host** to run a harness; the foreground
  `omnigent server` does **not** start one ("No hosts" in the UI). Registered one
  with `omnigent host --server http://localhost:6767` (the UI's "Connect a host"
  dialog shows the same as `omni host --server http://localhost:6767`). Host
  `DESKTOP-H82BB8Q`, foreground daemon, logs → `~/.omnigent/logs/host-runner/`.

## Key finding — Omnigent web chat is coding-CLI-oriented (affects Phases 1/2/4)

The web chat runs agents on **coding harnesses / SDKs**, none of which accept our
**keyless ChatGPT OAuth**:

- Harnesses: Claude Code / OpenCode / Cursor / Kiro / Qwen / Kimi = *needs setup*;
  **Codex = *binary missing*** (wants the standalone Codex CLI = the `codex-native`
  harness).
- Debby/Polly "Agent Harness": Claude SDK (needs Anthropic key), OpenAI Agents SDK
  (needs OpenAI API key), Codex (*binary missing*).
- **No "Hermes"** appears in either the harness or agent-harness lists — stock
  Omnigent reaches Hermes only via the top-level `omnigent hermes` command.

Sending on the "Codex" harness produced:
`Error · harness_not_configured · harness 'codex-native' is not configured on host
… run 'omnigent setup' … to install the CLI and set a default credential`.
This **confirms R1's prediction**: `codex-native` (Codex CLI) is distinct from
Hermes' `openai-codex` provider and we do not need it.

### Acceptance path taken

Ran **`omnigent hermes`** — launches the Hermes TUI in an Omnigent terminal, on
the already-configured `openai-codex / gpt-5.5` brain (keyless). A turn completed
successfully. This is the on-plan path: Phase 2 wires the Clerk agent with
`harness: hermes`, and Phase 4 strips exactly the coding-CLI chrome seen above.

## Boot errors + fixes (for a resuming agent)

- **WSL DNS flakiness** for the install hosts → set public DNS:
  `echo -e "nameserver 8.8.8.8\nnameserver 1.1.1.1" | sudo tee /etc/resolv.conf`.
- **Hidden sudo prompt** during the bootstrap (bubblewrap step): the installer
  spinner drew over `[sudo] password:`. Diagnosed via `ps` in a 2nd shell (a
  lone `sudo` with no `apt-get` child = waiting for password); fixed by typing
  the password blind in the running window.
- **`gio: Operation not supported`** when auto-opening a browser → use
  `--no-browser` (auth) / `--no-open` (server) and open URLs manually in the
  Windows browser. WSL2 loopback makes the callbacks resolve.

## Implications for later phases

- **Phase 1 (vendor):** the web harness picker (Claude Code / Codex / Cursor / …)
  is the coding-agent chrome; **Phase 4** strips it from the end-user view.
- **Phase 2 (agent + tool bridge):** wire the Clerk agent with `harness: hermes`
  so it uses the `openai-codex` brain directly, bypassing the
  `codex-native` / API-key agent-harnesses entirely.
- **Deploy (R2):** `tmux` + `bubblewrap` are present on the Linux target, so the
  full native sandbox surface is available there (unlike the Windows host).

## Acceptance Gate

- [x] Omnigent installed and `omnigent server` serves the web UI on Linux
      (`localhost:6767`, single-user mode, loads in browser).
- [x] `omnigent setup` reports Hermes/Codex ready: `gpt-5.5 (via OpenAI Codex)`.
- [x] A **Hermes-backed** turn completes on the ChatGPT subscription, on Linux,
      via `omnigent hermes`. R1 + R2 de-risked.
