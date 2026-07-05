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

## MCP bridge (pi-mcp-adapter)

MCP reaches the Clerk bridge via the **`pi-mcp-adapter`** extension (`pi install npm:pi-mcp-adapter`), not pi built-ins. Project-local config: `spikes/pi-corpus-spike/.pi/mcp.json` (pi reads this relative to cwd — all spike runs must start from that directory).

- **Remote HTTP server:** `http://127.0.0.1:8000/mcp` (`settings.agent_mcp_url`)
- **Auth:** `Authorization: Bearer ${CLERK_MCP_TOKEN}` — token minted by `mint_token.py` (HMAC turn token, 1h TTL)
- **`directTools`:** registers only these five as native pi tools; everything else on the bridge (workspace write, tender workflow, etc.) stays invisible:

  | Tool | Role |
  | --- | --- |
  | `find_document_text` | Exact-phrase lookup in ingested corpus |
  | `search_documents` | Conceptual / semantic search |
  | `get_document` | Full document read |
  | `list_platform_knowledge` | Platform knowledge index |
  | `read_platform_knowledge` | Platform knowledge read |

Locked eval runs combine `--no-tools` (no bash/read/write/edit) with the five MCP tools above — that is the full tool surface under test.

## Spike project (Task 3 connectivity)

- **SPIKE_USER_ID:** `f650d8d8-6dc6-4bb3-a6e8-64205bd8b47f`
- **SPIKE_PROJECT_ID:** `59dd9635-4b63-4251-b903-348ae9fa2a2b` (Test Project 112, 11 ingested docs)
- **MCP connectivity:** `find_document_text` callable via pi-mcp-adapter with turn token auth (2026-07-05). Query `'the'` rejected by tool validation; `'geotech'` returns match JSON.

## Eval question set (Task 4)

| # | Question | Expected source | Tool bias |
| --- | --- | --- | --- |
| 1 | Bearing capacity for southern footings (Terratech) | `06-geotechnical-report-terratech.md` | find_document_text |
| 2 | Sydney Water BOS fee (sewer diagram email) | `08-email-sydney-water-sewer-diagram.md` | find_document_text |
| 3 | CivilFlow stormwater/OSD quote (Karen Morrison email) | `10-email-stormwater-consultant-quote.md` | find_document_text |
| 4 | Key stage milestones (master programme) | `11-master-programme-chen-residence.md` | search_documents |
| 5 | Survey recommendations before footing design | `05-survey-report-north-shore-surveying.md` | search_documents |
| 6 | Harrison Clarke fee structure (engagement letter) | `01-engagement-letter-harrison-clarke-studio.md` | search_documents |
| 7 | Geotech scope and borehole locations (Terratech) | `06-geotechnical-report-terratech.md` | get_document |
| 8 | Arborist / tree protection issues (survey report) | `05-survey-report-north-shore-surveying.md` | get_document |

## Decision

**Verdict: GO (with integration caveats)**

Locked condition meets the plan gate: **7/8 correct**, **zero escape attempts**, typical latency ~17s/question (acceptable for chat).

### Why GO

- pi reliably drives Clerk retrieval MCP tools from ingested corpus without bash/read/write escape.
- Locked surface produces *better* grounding on Q1 than open (correctly refuses to invent bearing capacity).
- Same model (`gpt-5.1`) isolates harness effect: tool-locked pi stays on corpus tools; failures are grounding/MCP reliability, not re-ingest behaviour.

### Caveats for integration

1. **MCP adapter stability:** `locked-q3.json` hit `MCP server "clerk" not available` mid-run → hallucinated answer. Production needs reconnect/retry or turn-level error surfacing.
2. **Windows driver:** Use `Start-Job` wrapper (documented in `run-eval.ps1`); bare `pi -p` hangs in some shells.
3. **CLI flag:** Use `--no-tools` not `--no-builtin-tools` (pi 0.67.68).
4. **Open condition:** Built-ins available did not cause escape in this eval, but Q1 open hallucinated — locking tools is still warranted for Q&A turns.

### Next step

Separate integration plan: pi runtime profile alongside `hermes_process.py` for corpus Q&A turns, reusing `turn_context.build_agent_prompt` and existing turn-token mint flow. Branch: `feature/omnigent-shell`.

### Cited traces

- `results/locked-q1.json` — correct refusal to invent bearing capacity
- `results/locked-q3.json` — MCP blip + hallucination
- `results/open-q1.json` — open condition hallucination with same retrieval tools
