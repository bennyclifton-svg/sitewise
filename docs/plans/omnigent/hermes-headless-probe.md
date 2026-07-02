# Hermes Headless Probe (Phase 0)

Date: 2026-07-02
Environment: WSL2 Ubuntu-24.04 on the Windows dev box, Hermes **v0.17.0**
(`2026.6.19`, upstream `2068754d`, local `9f030950`), provider `openai-codex`,
model `gpt-5.5` (ChatGPT OAuth, keyless — see
[hermes-provider-decision.md](./hermes-provider-decision.md)).

All commands run from Windows via `wsl -d Ubuntu-24.04 -- bash -lc "…"` — a
pipe, **no TTY**, which is exactly the headless condition under test.

## Task 1 — CLI surface

`hermes --version && hermes --help` (verbatim header):

```text
Hermes Agent v0.17.0 (2026.6.19) · upstream 2068754d · local 9f030950 (+1 carried commit)
Project: /home/bennyclifton/.hermes/hermes-agent
Python: 3.11.15
OpenAI SDK: 2.24.0
```

Subcommands (full list from `--help`):

```text
chat, model, moa, fallback, secrets, migrate, gateway, proxy, lsp, setup,
postinstall, whatsapp, whatsapp-cloud, slack, send, login, logout, auth,
status, cron, webhook, portal, kanban, project, hooks, doctor, security,
dump, debug, backup, checkpoints, import, config, pairing, skills, bundles,
plugins, curator, pets, journey (learning, memory-graph), memory, tools,
computer-use, mcp, sessions, insights, claw, version, update, uninstall,
acp, profile, completion, dashboard, serve, desktop (gui), logs, prompt-size
```

Top-level flags relevant to headless use (verbatim from `--help`):

```text
-z PROMPT, --oneshot PROMPT
    One-shot mode: send a single prompt and print ONLY the final
    response text to stdout. No banner, no spinner, no tool previews,
    no session_id line. Tools, memory, rules, and AGENTS.md in the CWD
    are loaded as normal; approvals are auto-bypassed. Intended for
    scripts / pipes.
-m MODEL, --model MODEL        (also env var HERMES_INFERENCE_MODEL)
--provider PROVIDER            per-invocation provider override
-t TOOLSETS, --toolsets TOOLSETS
--resume SESSION / -c [NAME]   resume sessions by id / name
--worktree, -w                 isolated git worktree (parallel agents)
--accept-hooks                 auto-approve shell hooks without a TTY
                               (= HERMES_ACCEPT_HOOKS=1; "Use on CI /
                               headless runs that can't prompt")
--yolo                         bypass dangerous-command approvals
--ignore-user-config / --ignore-rules / --safe-mode   isolated runs
```

## Headless candidates

Ranked, with evidence:

1. **`hermes -z "<prompt>"` (one-shot)** — purpose-built: "Intended for
   scripts / pipes", prints only final response text, approvals auto-bypassed.
   Primary candidate.
2. **`hermes chat -q "<prompt>" [-Q]`** — "Single query (non-interactive
   mode)"; `-Q/--quiet` = "Quiet mode for programmatic use: suppress banner,
   spinner, and tool previews. Only output the final response and session
   info." Unlike `-z` it prints session info, and supports `--resume`,
   `--max-turns N`, and `--source tool` ("third-party integrations that
   should not appear in user session lists"). Best fit for multi-turn
   server-side sessions in Phase 2.
3. **`hermes serve`** — "Start the Hermes backend server (headless; powers
   the desktop app and remote backends)". A persistent-process alternative
   to per-turn CLI spawns; not probed in Phase 0.
4. **`hermes acp`** — "Run Hermes Agent as an ACP (Agent Client Protocol)
   server". Structured JSON-RPC agent protocol over stdio; another
   programmatic surface, not probed in Phase 0.

No `--output-format`/`--json` flag exists on `-z`/`chat -q`; output is plain
text (structured output would come via `serve`/`acp` if ever needed).

Note: a `-z` turn was already observed working once during the provider spike
(`hermes -z "Reply with exactly: hello from codex"` → `hello from codex`,
see hermes-provider-decision.md) — Task 2 re-verifies deliberately, incl.
exit code and streaming.

## MCP config shape (gate item c)

Current `~/.hermes/config.yaml` has **no `mcp_servers:` section yet** (fresh
install, `hermes mcp list` → "No MCP servers configured.").

`hermes mcp add --help`:

```text
usage: hermes mcp add [-h] [--url URL] [--command MCP_COMMAND] [--args ...]
                      [--auth {oauth,header}] [--preset PRESET]
                      [--env [ENV ...]]
                      name
```

Official docs (`/docs/user-guide/features/mcp`) — HTTP server with custom
headers, verbatim shape:

```yaml
mcp_servers:
  company_api:
    url: "https://mcp.internal.example.com"
    headers:
      Authorization: "Bearer ***"
```

Per-server custom headers are supported, and `headers` values support
`${ENV_VAR}` substitution resolved from `~/.hermes/.env`.

Cross-checked against the installed source
(`~/.hermes/hermes-agent/hermes_cli/mcp_config.py`):

- `hermes mcp add <name> --url … --auth header` writes
  `server_config["headers"] = {"Authorization": f"Bearer ${{{env_key}}}"}`
  with the token stored in `~/.hermes/.env` (line ~414).
- `cfg.get("headers", {})` is read generically — **any** header key/value
  pairs are passed through, with `${ENV_VAR}` interpolation
  (`_ENV_VAR_PATTERN.sub(lambda m: os.getenv(m.group(1), ""), v)`), so a
  custom `Authorization: Bearer <turn-token>` header per server is
  declarable either literally or via env var.
- Transport is inferred: `url` key → HTTP ("Transport: HTTP → <url>"),
  `command`/`args` keys → stdio. `auth: oauth` selects OAuth 2.1 PKCE
  instead of headers. An `enabled: false` flag exists per server.

Shape Phase 2 will use (turn-token auth against Clerk's FastAPI MCP endpoint):

```yaml
mcp_servers:
  clerk:
    url: "http://127.0.0.1:8000/mcp"
    headers:
      Authorization: "Bearer ${CLERK_MCP_TOKEN}"   # or a literal value
```

Caveat for Phase 2: `${ENV_VAR}` interpolation reads the *process*
environment (populated from `~/.hermes/.env`), so per-turn tokens either go
in as env vars on the spawned process or the config must be written
per-turn/per-profile. Static headers work as-is.

## API-key provider shape (gate item for Task 3)

From `/docs/user-guide/configuration` — API keys never live in
`config.yaml`; they go in `~/.hermes/.env`, with provider selection in
`config.yaml`:

```yaml
# config.yaml
model:
  provider: openai        # or: anthropic, openrouter
  default: gpt-4o         # claude-opus-4 / anthropic/claude-opus-4
```

```text
# ~/.hermes/.env
OPENAI_API_KEY=sk-...        # openai
ANTHROPIC_API_KEY=sk-ant-... # anthropic
OPENROUTER_API_KEY=sk-or-... # openrouter
```

OpenAI-compatible custom endpoints: `model.provider: custom` +
`model.base_url: https://…/v1` + `OPENAI_API_KEY` in `.env`.
`hermes config set` "automatically routes values to the right file — API
keys are saved to `.env`". Per-invocation override: `--provider` / `-m`
flags (no config edit needed).

**Status: unvalidated with live key** — no platform API key was available in
the environment; config shape recorded from docs + CLI help only, per plan.

## Open questions

- Does `-z` stream to stdout incrementally, or buffer the final text?
  (`display.streaming: true` but top-level `streaming.enabled: false` in
  config — meaning unclear.) → Task 2.
- Do two concurrent headless turns collide on session files / locks?
  (`hermes profile` = "multiple isolated Hermes instances" exists as an
  isolation escape hatch, as does `--ignore-user-config`.) → Task 3.
- `hermes serve` / `hermes acp` as longer-lived alternatives to per-turn CLI
  spawns — out of scope for Phase 0, revisit in Phase 2 design.
- Per-turn Authorization headers: env-var interpolation is process-wide, not
  per-request; per-turn token injection strategy to be settled in Phase 2.
