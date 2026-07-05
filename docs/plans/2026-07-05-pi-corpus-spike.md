# Pi Corpus-Interrogation Spike Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Empirically test whether badlogic's pi agent, restricted to only Clerk's MCP document-retrieval tools, answers corpus questions from the database instead of re-ingesting source documents — producing a go/no-go decision on adopting pi for chat/Q&A turns.

**Architecture:** Standalone spike, zero changes to the Clerk app. pi runs one-shot (`pi -p`) from an isolated spike directory, connected to the existing FastMCP bridge at `http://127.0.0.1:8000/mcp` via the `pi-mcp-adapter` extension, authenticated with a turn token minted by the existing `mint_turn_token()` helper. Two conditions are compared over the same question set: **locked** (`--no-builtin-tools`, only the four retrieval tools) and **open** (built-in bash/read/write/edit also available). Same model as Hermes (`gpt-5.1` via OpenAI) so we isolate the harness/tool-surface variable, not the model.

**Tech Stack:** pi (`@earendil-works/pi-coding-agent`, Node/npm), `pi-mcp-adapter` extension, existing FastAPI + FastMCP backend, PowerShell driver script.

**Key facts (verified 2026-07-05):**
- Install: `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` → `pi` binary. Docs: https://github.com/badlogic/pi-mono (now earendil-works/pi) and https://pi.dev
- One-shot: `pi -p "prompt"`; structured output via `--mode json`. Flag `--no-builtin-tools` removes bash/read/write/edit/grep/find/ls while keeping extension tools.
- MCP: `pi install npm:pi-mcp-adapter`; project-local config at `.pi/mcp.json`; remote HTTP servers support `"headers": {"Authorization": "Bearer ${VAR}"}` and `"directTools": [...]` to register selected MCP tools as native tools. Docs: https://github.com/nicobailon/pi-mcp-adapter
- Clerk bridge: mounted at `settings.agent_mcp_url` (default `http://127.0.0.1:8000/mcp`), Bearer auth verified by `backend/app/mcp_bridge/auth.py` against HMAC turn tokens from `backend/app/mcp_bridge/tokens.py` (`AGENT_TURN_TOKEN_SECRET` in `backend/.env`).
- Retrieval tools under test: `find_document_text`, `search_documents`, `get_document`, `list_platform_knowledge`, `read_platform_knowledge` (all in `backend/app/mcp_bridge/server.py`).

**User inputs required before Task 4:** a `project_id` + owning `user_id` with real ingested documents, and 8 real questions whose answers live in those documents (with the expected source doc per question).

---

### Task 1: Install pi and verify the flags we depend on

**Files:**
- Create: `spikes/pi-corpus-spike/NOTES.md` (running log of observed versions/flags)

**Step 1: Install pi globally**

```powershell
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Expected: npm reports the package added; no install-script execution (we passed `--ignore-scripts`).

**Step 2: Verify the binary and the critical flags**

```powershell
pi --version
pi --help
```

Expected: a version string, and help output listing `-p/--print` (one-shot), `--mode` (json), and `--no-builtin-tools`. **Also note the exact model-selection flag** (expected `--model` or `-m`) — later commands use `--model`; adjust them if help names it differently. Record the version and exact flag names in `spikes/pi-corpus-spike/NOTES.md`.

**Step 3: Configure the OpenAI key and smoke-test one-shot mode**

Use the same provider/model Hermes runs (`hermes_model: gpt-5.1`, provider `openai-api` — see `backend/app/config.py:98-99`) so the comparison isolates the harness, not the model. The `OPENAI_API_KEY` value is in `backend/.env`.

```powershell
$env:OPENAI_API_KEY = "<value from backend/.env>"
pi --model gpt-5.1 -p "Reply with exactly: PI-SMOKE-OK"
```

Expected: output containing `PI-SMOKE-OK`. If the model flag differs, use the name from `pi --help` and update NOTES.md.

**Step 4: Commit**

```powershell
git add spikes/pi-corpus-spike/NOTES.md
git commit -m "spike(pi): record pi install version and verified CLI flags"
```

---

### Task 2: Install pi-mcp-adapter and point it at the Clerk bridge

**Files:**
- Create: `spikes/pi-corpus-spike/.pi/mcp.json`

**Step 1: Install the adapter extension**

```powershell
pi install npm:pi-mcp-adapter
```

Expected: pi reports the extension installed (it lands in the pi agent dir; restart pi after install — irrelevant for one-shot runs since every run is a fresh process).

**Step 2: Write the project-local MCP config**

pi reads `.pi/mcp.json` relative to its working directory, so all spike runs MUST be launched from `spikes/pi-corpus-spike/`. Create `spikes/pi-corpus-spike/.pi/mcp.json`:

```json
{
  "mcpServers": {
    "clerk": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer ${CLERK_MCP_TOKEN}"
      },
      "bearerTokenEnv": "CLERK_MCP_TOKEN",
      "directTools": [
        "find_document_text",
        "search_documents",
        "get_document",
        "list_platform_knowledge",
        "read_platform_knowledge"
      ]
    }
  }
}
```

`directTools` registers ONLY these five as native pi tools — the rest of the bridge (workspace write, tender workflow tools) stays invisible. This is the corpus-interrogation surface.

**Step 3: Commit**

```powershell
git add spikes/pi-corpus-spike/.pi/mcp.json
git commit -m "spike(pi): configure pi-mcp-adapter against clerk MCP bridge, retrieval tools only"
```

---

### Task 3: Mint a turn token and prove end-to-end connectivity

**Files:**
- Create: `spikes/pi-corpus-spike/mint_token.py`

**Step 1: Write the token-minting script**

The bridge authenticates with short-lived HMAC turn tokens (`backend/app/mcp_bridge/tokens.py:50`). Create `spikes/pi-corpus-spike/mint_token.py`:

```python
"""Mint a Clerk MCP turn token for the pi spike.

Run from backend/ so `app.*` imports and .env settings resolve:
    cd backend
    python ../spikes/pi-corpus-spike/mint_token.py
Requires SPIKE_USER_ID and SPIKE_PROJECT_ID env vars (a real user who
owns a real project with ingested documents).
"""
import os
import uuid

from app.mcp_bridge.tokens import mint_turn_token

token = mint_turn_token(
    user_id=uuid.UUID(os.environ["SPIKE_USER_ID"]),
    project_id=uuid.UUID(os.environ["SPIKE_PROJECT_ID"]),
    ttl_seconds=3600,
)
print(token)
```

(1-hour TTL instead of the production 900s so a full eval run fits one token. Never commit a minted token.)

**Step 2: Start the backend and mint a token**

Start the backend per `docs/guides/backend-setup.md` (uvicorn on port 8000) in one terminal. In another:

```powershell
$env:SPIKE_USER_ID = "<real user uuid>"
$env:SPIKE_PROJECT_ID = "<real project uuid with ingested docs>"
cd backend
$env:CLERK_MCP_TOKEN = (python ../spikes/pi-corpus-spike/mint_token.py)
cd ..
```

Expected: `$env:CLERK_MCP_TOKEN` holds a two-part `body.signature` token.

**Step 3: Prove pi can call a bridge tool end-to-end**

```powershell
cd spikes/pi-corpus-spike
pi --model gpt-5.1 --no-builtin-tools -p "Call the find_document_text tool with project_id $env:SPIKE_PROJECT_ID and query 'the'. Report only the tool call result, do not interpret it."
```

Expected: pi's output shows a `find_document_text` tool call returning JSON match results (or an empty list) — NOT an auth error. If you get `unauthorized`/`401`, re-check `AGENT_TURN_TOKEN_SECRET` matches between the running backend and the minting run.

**Step 4: Commit**

```powershell
git add spikes/pi-corpus-spike/mint_token.py
git commit -m "spike(pi): add turn-token minting script for MCP bridge auth"
```

---

### Task 4: Build the evaluation set and driver script

**Files:**
- Create: `spikes/pi-corpus-spike/questions.txt`
- Create: `spikes/pi-corpus-spike/run-eval.ps1`

**Step 1: Write the question set (requires user input)**

Ask the user for 8 questions about documents already ingested in the spike project — the kind Hermes has been mishandling (e.g. "What bearing capacity does the geotech report give for the southern footings?"). One question per line in `spikes/pi-corpus-spike/questions.txt`. For each, record the expected source document in `NOTES.md` so answers can be scored.

Good sets mix: 3 exact-phrase lookups (should hit `find_document_text`), 3 conceptual questions (should hit `search_documents`), 2 that need a longer read (should hit `get_document`).

**Step 2: Write the driver script**

Create `spikes/pi-corpus-spike/run-eval.ps1`:

```powershell
param(
    [ValidateSet("locked", "open")]
    [string]$Condition = "locked"
)

if (-not $env:CLERK_MCP_TOKEN) { throw "CLERK_MCP_TOKEN not set - mint a token first (Task 3)" }
if (-not $env:SPIKE_PROJECT_ID) { throw "SPIKE_PROJECT_ID not set" }

New-Item -ItemType Directory -Force "results" | Out-Null
$questions = Get-Content "questions.txt" | Where-Object { $_.Trim() }

$preamble = "You are answering questions about project $($env:SPIKE_PROJECT_ID). " +
    "Its uploaded documents are already ingested and fully searchable via the clerk tools. " +
    "Question: "

$i = 0
foreach ($q in $questions) {
    $i++
    $outFile = "results/$Condition-q$i.json"
    Write-Host "[$Condition] Q$i : $q"
    $prompt = $preamble + $q
    if ($Condition -eq "locked") {
        pi --model gpt-5.1 --no-builtin-tools --mode json -p $prompt > $outFile
    } else {
        pi --model gpt-5.1 --mode json -p $prompt > $outFile
    }
}
Write-Host "Done. Traces in results/ - score them into results.md"
```

Note the preamble states the corpus is ingested and searchable but does NOT name which tool to use per question — tool selection is exactly what we are measuring.

**Step 3: Dry-run the driver with one question**

Temporarily put a single question in `questions.txt`, then:

```powershell
cd spikes/pi-corpus-spike
./run-eval.ps1 -Condition locked
Get-Content results/locked-q1.json
```

Expected: a JSON trace file containing the assistant turn(s) and tool calls. Confirm tool-call names are identifiable in the JSON (that's what scoring reads). Restore the full question set afterwards.

**Step 4: Commit**

```powershell
git add spikes/pi-corpus-spike/questions.txt spikes/pi-corpus-spike/run-eval.ps1
git commit -m "spike(pi): add eval question set and two-condition driver script"
```

---

### Task 5: Run the two-condition matrix and score it

**Files:**
- Create: `spikes/pi-corpus-spike/results.md`
- Create: `spikes/pi-corpus-spike/results/` (traces; commit them — they are the evidence)

**Step 1: Run condition A (locked — the hypothesis)**

```powershell
cd spikes/pi-corpus-spike
./run-eval.ps1 -Condition locked
```

Expected: 8 trace files `results/locked-q*.json`, no errors. If the token expired mid-run, re-mint (Task 3 Step 2) and re-run.

**Step 2: Run condition B (open — pi with escape hatches)**

```powershell
./run-eval.ps1 -Condition open
```

Expected: 8 trace files `results/open-q*.json`. This condition tests whether pi's priors differ from Hermes's when bash/file tools ARE available.

**Step 3: Score both conditions into results.md**

For every trace, record in a table in `spikes/pi-corpus-spike/results.md`:

| # | Condition | Tools called (in order) | Escape attempt? (bash/read/write/other) | Answer correct? | Notes |

- "Escape attempt" = any call or attempted call to a non-retrieval tool, or prose declaring it needs the original file/OCR/database access.
- "Answer correct" = matches the expected source document recorded in NOTES.md (verify the cited content against the doc).
- Also record per-condition totals: correct count, escape count, and rough wall-clock per question.

**Step 4: Capture a 3-question Hermes baseline for the same questions**

Run the first 3 questions through the normal Clerk chat UI against the same project. In `results.md`, record for each whether Hermes answered from the retrieval tools or re-ingested/re-sourced the document (the activity trace / status events show tool usage). This anchors the comparison to the behaviour that motivated the spike.

**Step 5: Commit**

```powershell
git add spikes/pi-corpus-spike/results.md spikes/pi-corpus-spike/results/
git commit -m "spike(pi): record two-condition eval results and Hermes baseline"
```

---

### Task 6: Decision write-up

**Files:**
- Modify: `spikes/pi-corpus-spike/NOTES.md` (add Decision section)

**Step 1: Apply the decision gate**

- **GO (adopt pi for Q&A turns):** locked condition answers ≥ 7/8 correctly, zero escape attempts, and latency is acceptable for chat (roughly comparable to current Hermes turns). Next step is a separate integration plan: a `pi` runtime profile alongside `hermes_process.py`, selected per turn type, reusing `turn_context.build_agent_prompt` and the existing turn-token flow.
- **NO-GO (agent):** locked condition fails mostly on *wrong/missing answers* while calling the right tools → the retrieval tools are the weak link (search quality, chunking, extraction), not the agent. Fix the tools first; re-running this spike afterwards is cheap.
- **NO-GO (harness):** pi can't reliably drive the MCP tools (adapter instability, JSON mode issues on Windows) → record specifics; the fallback is the bare API loop from the agent comparison (same locked tool surface, loop owned by Clerk).
- Also note the open-condition result either way: if open-pi escapes like Hermes does, that confirms the tool-surface diagnosis (any agent with escape hatches will use them); if open-pi stays on the retrieval tools, pi's priors are genuinely better.

**Step 2: Write the decision, with the three most informative traces cited by filename**

**Step 3: Commit**

```powershell
git add spikes/pi-corpus-spike/NOTES.md
git commit -m "spike(pi): record go/no-go decision on pi for corpus Q&A turns"
```
