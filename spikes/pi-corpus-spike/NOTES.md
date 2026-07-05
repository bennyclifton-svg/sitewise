# Pi Corpus Spike — Running Notes

## Install (2026-07-05)

- **Package on PATH:** `@mariozechner/pi-coding-agent@0.67.68` (already installed globally; `npm install -g @earendil-works/pi-coding-agent` failed with EEXIST on `pi.cmd` — same binary name, existing install kept)
- **Binary:** `pi --version` → `0.67.68`
- **One-shot flag:** `-p` / `--print`
- **JSON mode:** `--mode json` (also `text`, `rpc`)
- **Model flag:** `--model <pattern>` (also supports `provider/model` without `--provider`)
- **Provider flag:** `--provider openai` (required when using bare model name like `gpt-5.1`)
- **Disable built-ins:** `--no-tools` (plan text says `--no-builtin-tools` — **not present** in 0.67.68; use `--no-tools` instead)
- **Selective tools:** `--tools read,grep,find,ls` (default: read,bash,edit,write)
- **Thinking:** `--thinking off` recommended for eval latency (gpt-5.1 defaults to thinking enabled)

## Smoke test

- Command: `pi --provider openai --model gpt-5.1 --thinking off --no-session --no-tools --mode text -p "Reply with exactly: PI-SMOKE-OK"`
- Requires `OPENAI_API_KEY` from `backend/.env`
- Set `PI_OFFLINE=1` to skip startup network ops
- **Note:** Direct invocation from some shells appeared to hang (no output); running via `Start-Job` completed in ~7s with `PI-SMOKE-OK`. Driver script may need explicit timeout or job wrapper on Windows.

## Spike project (Task 3 connectivity)

- **SPIKE_USER_ID:** `f650d8d8-6dc6-4bb3-a6e8-64205bd8b47f`
- **SPIKE_PROJECT_ID:** `59dd9635-4b63-4251-b903-348ae9fa2a2b` (Test Project 112, 11 ingested docs)
- **MCP connectivity:** `find_document_text` callable via pi-mcp-adapter with turn token auth (2026-07-05). Query `'the'` rejected by tool validation; `'geotech'` returns match JSON.

## Decision

_(pending Task 6)_
