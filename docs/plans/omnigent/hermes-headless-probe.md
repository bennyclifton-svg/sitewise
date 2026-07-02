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

Task 3 checks: `~/.hermes/.env` is the shipped template with every provider
key line commented out (`# OPENROUTER_API_KEY=…`, `# GOOGLE_API_KEY=…`, …)
— confirmed no live key to test with. `hermes auth --help` surface:
`add / list / remove / reset / status / logout` for pooled credentials
(this is the OAuth/pooled-credential layer used for `openai-codex`; plain
API keys use `.env` + `model.provider` as above, or per-invocation
`--provider` / `-m`).

## Task 2 — Scripted turn + streaming

All runs piped (no TTY), from Windows via `wsl … -- bash -lc`. Note for a
resuming agent: `$` in commands gets interpolated away by the Windows-side
harness before reaching WSL, so the probes below were written to a script
file and run with `tr -d '\r' < /mnt/c/…/script.sh | bash`.

### Step 1 — non-interactive turn: WORKS, no TTY, no shims

```text
$ hermes -z 'Reply with exactly: HEADLESS OK' > /tmp/hermes-probe.txt 2>&1
$ cat /tmp/hermes-probe.txt
HEADLESS OK
```

No pty shim, no stdin tricks, no `--no-tui` needed. Exit code verified as 0
on the identical `-z` invocation below (`HERMES_EXIT=${PIPESTATUS[0]}`).

### Step 2 — streaming

**`hermes -z` is final-only (buffered) — by design.** Timestamped run:

```text
START=21:49:52.441
21:50:02.085 | 1
21:50:02.087 | 2
…
21:50:02.098 | 10
HERMES_EXIT=0
END=21:50:02.334
```

All 10 lines in 13 ms after a ~10 s silent wait. Source-confirmed
(`hermes_cli/oneshot.py`): the whole call tree runs under
`redirect_stdout(devnull)`, the final response is written once at the end,
and it explicitly sets `agent.stream_delta_callback = None` ("make sure
AIAgent doesn't invoke any streaming display callbacks").

**`hermes chat -q -Q` (quiet) is also final-only** — source-confirmed
(`cli.py`, quiet single-query path): sets
`cli.agent.stream_delta_callback = None` / `tool_gen_callback = None`
("stdout stays machine-readable … response is printed once below"), prints
`session_id: <id>` to **stderr** (stdout stays clean), exits 0/1
(`result.get("failed")` → 1).

**`hermes chat -q` (non-quiet) genuinely line-streams to a pipe** when
`display.streaming: true` (this config's value). First try was inconclusive
(10 short lines burst in 250 ms after a 7 s think — reasoning is hidden,
short answers emit sub-second). Decisive run with a longer visible output:

```text
$ PYTHONUNBUFFERED=1 hermes chat -q 'Write exactly 12 one-sentence facts about
  reinforced concrete, as a numbered list. No preamble.' 2>&1 | <timestamper>
START=21:53:01.224
21:53:01.796 | Query: Write exactly 12 one-sentence facts about reinforced concrete, as a
21:53:01.901 | Initializing agent...
21:53:03.373 | ────────────────────────────────────────
21:53:08.617 | ╭─ ⚕ Hermes ───────────────────────────────────────────────╮
21:53:08.732 |     1. Reinforced concrete combines concrete's compressive …
21:53:08.988 |     2. Steel bars are embedded in concrete to resist …
21:53:09.344 |     3. Concrete protects reinforcing steel from corrosion …
21:53:09.771 |     4. …
21:53:10.061 |     5. …
21:53:10.539 |     6. …
21:53:10.770 |     7. …
21:53:11.208 |     8. …
21:53:11.568 |     9. …
21:53:11.958 |     10. …
21:53:12.332 |     11. …
21:53:13.094 |     12. …
21:53:13.095 | ╰───────────────────────────────────────────────────────────╯
21:53:13.251 | Session:        20260702_215301_af7c07
HERMES_EXIT=0
END=21:53:13.528
```

Lines arrived every 250–450 ms across ~4.4 s of generation = **line-level
streaming, PASS** (matches `_stream_delta`'s docstring: "Line-buffered
streaming callback for real-time token rendering"). Caveats for the Phase 2
SSE relay:

- The streamed path carries Rich chrome (box borders `╭─ ⚕ Hermes ─╮`,
  indentation, wrapped `Query:` echo, session summary) — the relay must
  strip/parse it, or use `chat -q -Q` (clean stdout, but final-only), or
  move to `hermes serve`/`acp` for structured streaming.
- Hidden reasoning (`show_reasoning: false`) means multi-second silent gaps
  before visible text; SSE keep-alives will be needed.
- `PYTHONUNBUFFERED=1` was set on the streaming run (not re-tested without;
  early banner lines flushed progressively either way).

## Task 3 — Concurrency

Two simultaneous `hermes -z` turns from one non-TTY shell (backgrounded,
`wait`-ed, exit codes captured per process):

```text
START=21:54:58.519
--A-- exit=0
ALPHA
--B-- exit=0
BRAVO
END=21:55:05.291
```

- Both completed correctly in ~7 s wall clock, outputs uncorrupted and
  un-crossed, both exit 0.
- **No lock/session collisions observed**: `find ~/.hermes -name '*.lock'
  -newermt '… 21:49'` → nothing; `~/.hermes/sessions/` is empty (`-z` runs
  are session-less by design — "no session_id line"); `errors.log` gained
  nothing from the concurrent window (only pre-existing tool-availability
  warnings from the earlier 21:53 run).
- Shared `~/.hermes/logs/agent.log` is appended by both processes —
  interleaved log lines, but that's cosmetic, not corrupting.
- If Phase 2 uses `chat -q` (which *does* create sessions), ids are
  timestamp+random (`20260702_215301_af7c07`), so collisions are unlikely;
  per-turn `HOME`/`--profile` isolation remains available as a hardening
  option but is **not required** by this probe's evidence.

## Go/No-Go Gate — **PASS**

| # | Gate item | Result | Evidence |
|---|-----------|--------|----------|
| a | Non-interactive turn works | **PASS** | `hermes -z 'Reply with exactly: HEADLESS OK'` through a TTY-less `wsl … bash -lc` pipe → `HEADLESS OK`, exit 0. No pty shim needed. |
| b | Output at least line-streamed | **PASS** | `hermes chat -q '<prompt>'` (with config `display.streaming: true`) emitted lines every 250–450 ms across a ~4.4 s generation to a non-TTY pipe. (`-z` and `chat -q -Q` are final-only by design — use them where buffered-final is fine.) |
| c | MCP-over-HTTP + custom headers declarable | **PASS** | `mcp_servers.<name>.url` + `headers: {Authorization: "Bearer …"}` per server, with `${ENV_VAR}` interpolation from `~/.hermes/.env`; confirmed in official docs *and* installed source (`hermes_cli/mcp_config.py`); `hermes mcp add --url … --auth header` writes exactly this shape. Not yet exercised against a live MCP endpoint (Phase 2). |
| d | Concurrent turns don't corrupt each other | **PASS** | Two parallel `-z` turns → correct isolated outputs, both exit 0, no lock files, no new errors; `-z` is session-less. No isolation workaround required. |

Residual risks carried into Phase 2 (none gate-blocking):

1. Streaming currently rides the human-facing `chat -q` path → Rich chrome
   must be stripped/parsed, or switch to `hermes serve`/`hermes acp` for a
   structured stream.
2. Per-turn `Authorization` values via `${ENV_VAR}` resolve from the
   process env — per-turn token injection = env var on the spawned process
   or per-profile config.
3. API-key provider shape unvalidated with a live key.
4. Probe ran on WSL2 Ubuntu-24.04; re-verify once on the real Linux deploy
   host (same caveat as the earlier spike).

## Open questions

- ~~Do two concurrent headless turns collide?~~ Answered in Task 3: no
  (with `-z`; `hermes profile` / `--ignore-user-config` remain as escape
  hatches if `chat -q` sessions ever collide).
- `hermes serve` / `hermes acp` as longer-lived alternatives to per-turn CLI
  spawns — structured streaming without Rich-chrome scraping. Out of scope
  for Phase 0, revisit in Phase 2 design.
- Per-turn Authorization headers: env-var interpolation is process-wide, not
  per-request; per-turn token injection strategy to be settled in Phase 2.
- Exact token-level (sub-line) streaming granularity unmeasured — line-level
  is confirmed and suffices for the gate.
