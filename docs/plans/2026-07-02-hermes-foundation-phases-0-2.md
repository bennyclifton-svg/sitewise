# Hermes Foundation (Phases 0–2) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** De-risk headless Hermes, land the in-flight Stage-0.5/ODL tender work cleanly, and build the MCP-over-HTTP tool bridge with per-project authorization — Phases 0–2 of [2026-07-02-agent-first-dashboard-design.md](./2026-07-02-agent-first-dashboard-design.md).

**Architecture:** Hermes runs headless on Linux (WSL2 dev / VPS prod) and reaches Clerk's domain logic through an MCP server mounted on the existing FastAPI app at `/mcp`. Every MCP tool authenticates a short-lived HMAC "turn token" (minted by Clerk when it invokes Hermes) and authorizes the project at the tool layer. Tools are thin: they delegate to existing service functions in `tender/router.py`, `tender/services/jobs.py`, and `app/retrieval/`.

**Tech Stack:** Python 3.12, FastAPI, async SQLAlchemy, `fastmcp` (3.4.2 already in venv, transitive — will be declared), `opendataloader-pdf[hybrid]` (already declared), Hermes CLI v0.17.0 in WSL2 Ubuntu-24.04, pytest, uv.

**Branch/worktree note:** This plan deliberately runs **in place on `feature/omnigent-shell`** — no worktree. Phase 1's whole job is landing the dirty working tree that already sits on this branch. Do not stash or discard it.

**Environment note:** Dev box is Windows. Backend commands run from `backend/` with `uv run ...` (PowerShell). Hermes/WSL commands run via `wsl -d Ubuntu-24.04 -- <cmd>` from PowerShell, or inside an interactive WSL shell. Commit messages end with:
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

**Verified starting state (2026-07-02):**
- Tender suite: **171 passed, 1 skipped**, with two known problems:
  1. `tests/tender/test_worker_chain.py` fails collection — imports `OcrResult`, removed when ingestion moved to ODL (Task 5 fixes).
  2. 8 tests error with `PermissionError` on `C:\Users\orlan\AppData\Local\Temp\pytest-of-orlan` — environmental, pytest can't scan its temp root (Task 4 fixes).
- `opendataloader-pdf[hybrid]==2.4.7` already in `backend/pyproject.toml`; `tender/services/pdf.py` already wraps it.
- Hermes v0.17.0 + `openai-codex` OAuth already configured in WSL (see [omnigent/spike-notes.md](./omnigent/spike-notes.md)).
- `Project.workspace_path` exists; ownership = single `owner_user_id` (no membership table — do not invent one).

---

## Phase 0 — Hermes headless probe (Tasks 1–3)

This phase is a **probe, not TDD**: experiments with recorded findings and a go/no-go gate. Deliverable: `docs/plans/omnigent/hermes-headless-probe.md`. If the gate fails, STOP — the design needs revisiting before Phases 2+ (Phase 1 is independent and may proceed).

### Task 1: Discover Hermes' non-interactive surface

**Files:**
- Create: `docs/plans/omnigent/hermes-headless-probe.md` (notes as you go)

**Step 1: Dump the CLI surface**

Run (PowerShell):
```powershell
wsl -d Ubuntu-24.04 -- bash -lc "hermes --version && hermes --help"
```
Expected: version `0.17.x` and a help screen. Record the full subcommand/flag list in the notes file.

**Step 2: Look for the headless entry points**

In the help output, look for (any of): a print/non-interactive flag (`-p`, `--print`, `--prompt`), a `run`/`exec` subcommand, an output-format flag (`--output-format`, `--json`), a stdin mode. For each candidate, run its `--help`:
```powershell
wsl -d Ubuntu-24.04 -- bash -lc "hermes <candidate> --help"
```
Also check the official docs if unclear: https://hermes-agent.nousresearch.com/docs (the providers page was reliable during the spike).

**Step 3: Check MCP support in config**

Phase 2 depends on Hermes consuming an MCP-over-HTTP server. Find how `~/.hermes/config.yaml` declares MCP servers:
```powershell
wsl -d Ubuntu-24.04 -- bash -lc "cat ~/.hermes/config.yaml"
```
plus the docs' MCP/integrations page. Record the exact config shape (transport, url, headers — we need custom `Authorization` headers for turn tokens; note whether per-server headers are supported).

**Step 4: Record findings + commit**

Write findings into `docs/plans/omnigent/hermes-headless-probe.md` (sections: CLI surface, headless candidates, MCP config shape, open questions).

```powershell
git add docs/plans/omnigent/hermes-headless-probe.md
git commit -m "docs(omnigent): hermes headless probe - CLI surface findings"
```

### Task 2: Run a scripted, streaming turn

**Step 1: Non-interactive turn**

Using the best candidate from Task 1 (illustrative — substitute the real flag):
```powershell
wsl -d Ubuntu-24.04 -- bash -lc "hermes run 'Reply with exactly: HEADLESS OK' 2>&1 | tee /tmp/hermes-probe.txt"
```
Expected: completes without a TTY, output contains `HEADLESS OK`, exit code 0. If Hermes refuses without a TTY, try piping stdin, `--no-tui`-style flags, or `script -qec` as a pty shim — record whichever works (a pty shim is acceptable for the probe but flag it as a deploy risk).

**Step 2: Verify output streams incrementally**

```powershell
wsl -d Ubuntu-24.04 -- bash -lc "hermes run 'Count slowly from 1 to 10, one number per line' 2>&1 | while IFS= read -r line; do echo \"$(date +%H:%M:%S.%3N) | $line\"; done"
```
Expected: timestamps spread over the turn (streaming), not all identical at the end (buffered). Record which. If line-buffered only, that's still a PASS (SSE can relay lines); token-level is a bonus.

**Step 3: Record + commit** (same notes file; message `docs(omnigent): hermes headless probe - scripted turn + streaming`)

### Task 3: API-key provider shape, concurrency, and the gate

**Step 1: Confirm API-key provider config**

From the providers docs + `hermes model`/`hermes auth --help`: record exactly how a plain API-key provider (e.g. `openai` or `anthropic`) is declared in `config.yaml` — the shape the **platform key** will use in production. If a real API key is available, configure it in a scratch config and run one turn on it. If not, record the config shape only and add "unvalidated with live key" to the notes — do not buy a key for the probe.

**Step 2: Two concurrent turns**

```powershell
wsl -d Ubuntu-24.04 -- bash -lc "hermes run 'Reply A' > /tmp/a.txt 2>&1 & hermes run 'Reply B' > /tmp/b.txt 2>&1 & wait; echo '--A--'; cat /tmp/a.txt; echo '--B--'; cat /tmp/b.txt"
```
Expected: both complete correctly. Record any lock-file/session-dir collisions (they dictate whether `backend/agent/` needs per-turn `HOME`/config isolation).

**Step 3: Write the go/no-go gate into the notes**

PASS requires: (a) a non-interactive turn works, (b) output is at least line-streamed, (c) MCP-over-HTTP with custom headers is declarable in config, (d) concurrent turns don't corrupt each other (or an isolation workaround is recorded). Mark PASS/FAIL per item.

**Step 4: Commit**

```powershell
git add docs/plans/omnigent/hermes-headless-probe.md
git commit -m "docs(omnigent): close Phase 0 probe - headless Hermes go/no-go"
```

---

## Phase 1 — Land Stage-0.5 + ODL fixture eval (Tasks 4–9)

### Task 4: Fix the pytest temp-dir permission error (environmental)

**Step 1: Remove the broken temp root**

```powershell
Remove-Item -Recurse -Force "C:\Users\orlan\AppData\Local\Temp\pytest-of-orlan"
```
If removal is denied, don't fight it — add `--basetemp` instead:  in `backend/pyproject.toml` under `[tool.pytest.ini_options]` add `addopts = "--basetemp=.pytest-tmp"` and add `.pytest-tmp/` to `.gitignore`.

**Step 2: Verify the 8 errored tests now pass**

```powershell
# from backend/
uv run pytest tests/tender/test_openai_client.py tests/tender/test_expectations.py tests/tender/test_eval_golden.py -q
```
Expected: PASS (no `PermissionError`). Only commit if pyproject/.gitignore changed.

### Task 5: Fix `test_worker_chain.py` for ODL-based ingestion

**Files:**
- Modify: `backend/tests/tender/test_worker_chain.py:14` and `:174-183`

The test still injects the deleted pytesseract-era `ocr=` dependency. `ingest_document` now takes `downloader/uploader/extractor/converter` ([ingestion.py:39](../../backend/tender/services/ingestion.py#L39)). Inject `extractor` so the unit test never invokes the real ODL/JVM.

**Step 1: Fix the import (line 14)**

```python
from tender.services.ingestion import ingest_document
from tender.services.pdf import PageExtract
```

**Step 2: Fix the injection (lines 174–183)**

```python
    session.execute_values = [[], []]
    run_async(
        ingest_document(
            session,
            _job("ingest_document", document),
            downloader=lambda *, storage_key: _text_pdf(),
            uploader=lambda *, storage_key, content, filename: storage_key,
            extractor=lambda pdf_bytes: [
                PageExtract(
                    page_no=1,
                    text="Quotation\nFooting $1,000\nSlab and drainage allowance included",
                )
            ],
        )
    )
```
(`_text_pdf()` stays — `render_page_png` still consumes the real bytes.)

**Step 3: Run the file**

```powershell
uv run pytest tests/tender/test_worker_chain.py -v
```
Expected: PASS (collection error gone, chain asserts `classify_document → extract_line_items → embed_items`).

**Step 4: Do NOT commit yet** — this lands inside Task 7's split commits.

### Task 6: Full suite + lint green

**Step 1:**
```powershell
uv run pytest tests -q
uv run ruff check .
```
Expected: 0 failures/errors (skips fine), ruff clean. Fix anything small that surfaces; anything structural → stop and reassess before committing.

### Task 7: Split-commit the working tree

One logical commit per group, in this order. **Before each commit run `git status --short` and stage only the listed paths.**

**Step 1: Investigate the two surprises first (do not skip):**
- `D backend/alembic/versions/007_tender_knowledge.py` — a deleted migration. Run `git log --oneline -3 -- backend/alembic/versions/007_tender_knowledge.py` and `ls backend/alembic/versions/`. Confirm 007 was renumbered/absorbed and `uv run alembic heads` shows a single head. If the deletion looks accidental, STOP and ask the user.
- `line.md` at repo root — read it. If it's scratch, delete it; if meaningful, move it under `docs/` in the docs commit.

**Step 2: Commit groups** (adjust only if Step 1 found problems):

1. **Build/config:** `backend/pyproject.toml backend/uv.lock backend/app/config.py backend/sitecustomize.py backend/tests/test_sitecustomize.py`
   `build(tender): ODL + config for Stage-0.5 ingestion`
2. **Migration reconciliation:** the 007 deletion (+ any replacement revision)
   `chore(db): reconcile tender knowledge migration`
3. **ODL pipeline backend:** `backend/tender/services/pdf.py ingestion.py classification.py context.py extraction_handler.py backend/tender/llm/schema.py openai_client.py prompts/classify_document_v0.1.0.md backend/tender/schemas.py backend/tender/services/jobs.py mapping.py silence.py backend/tender/worker.py backend/tender/router.py` + all `backend/tests/tender/` changes
   `feat(tender): Stage-0.5 front half - ODL ingest, classify, extract, auto-chain`
4. **Dockerfile:** `deploy/docker/backend.Dockerfile` (after Task 9 verifies JVM)
   `build(docker): JVM for opendataloader-pdf`
5. **Frontend:** all `frontend/src/` changes incl. `TenderIntakePanel.tsx`
   `feat(tender-ui): intake panel + comparison surfaces for Stage-0.5`
6. **Docs:** `docs/plans/2026-06-13-tcm-stage0.5-ingestion-classification.md docs/plans/tcm/01-stage0-consolidation.md docs/issues/tcm-stage0.5-ingestion/ docs/local-repo/` (+ `line.md` disposition)
   `docs(tcm): Stage-0.5 plan, issues, local-repo PRD (parked - doctrine adopted)`

**Step 3: Verify clean:** `git status --short` shows only `docs/*.pdf` fixtures (next task) — nothing else.

### Task 8: ODL fixture eval

**Files:**
- Move: `docs/Enmore.pdf`, `docs/Kaposi.pdf`, `docs/NexusBuilt.pdf` → `backend/tests/tender/fixtures/`
- Create: `backend/tests/tender/test_odl_fixture_eval.py`

**Step 1: Check sizes, then move**

```powershell
Get-ChildItem docs/*.pdf | Select-Object Name, Length
New-Item -ItemType Directory -Force backend/tests/tender/fixtures
git mv docs/Enmore.pdf docs/Kaposi.pdf docs/NexusBuilt.pdf backend/tests/tender/fixtures/
```
If any file exceeds ~10 MB, leave them in place gitignored and make the test `skipif` missing instead — note which path you took.

**Step 2: Write the eval test** (marked — excluded from the default fast suite):

```python
# backend/tests/tender/test_odl_fixture_eval.py
"""ODL extraction eval over the real tender fixtures (slow: invokes the JVM)."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from tender.services.pdf import extract_pages

FIXTURES = Path(__file__).parent / "fixtures"
PDFS = ["Enmore.pdf", "Kaposi.pdf", "NexusBuilt.pdf"]


@pytest.mark.integration
@pytest.mark.tender_eval
@pytest.mark.parametrize("name", PDFS)
def test_odl_extracts_real_tender_fixture(name: str) -> None:
    pdf_path = FIXTURES / name
    if not pdf_path.exists():
        pytest.skip(f"fixture {name} not present")

    start = time.perf_counter()
    pages = extract_pages(pdf_path.read_bytes())
    elapsed = time.perf_counter() - start

    assert pages, f"{name}: ODL returned no pages"
    non_empty = [p for p in pages if p.text.strip()]
    assert len(non_empty) >= max(1, len(pages) // 2), (
        f"{name}: {len(non_empty)}/{len(pages)} pages have text"
    )
    total_chars = sum(len(p.text) for p in pages)
    print(f"\n{name}: {len(pages)} pages, {total_chars} chars, {elapsed:.1f}s")
```

**Step 3: Run it** (needs Java on PATH — if missing on Windows, run inside WSL or record as Linux-verified-only):

```powershell
uv run pytest tests/tender/test_odl_fixture_eval.py -m tender_eval -v -s
```
Expected: 3 PASS with timing lines. Record the timings in the commit message — this is the ODL accuracy/speed baseline the design requires before the old extraction path can ever be deleted.

**Step 4: Commit**

```powershell
git add backend/tests/tender/fixtures backend/tests/tender/test_odl_fixture_eval.py
git commit -m "test(tender): ODL fixture eval baseline (Enmore/Kaposi/NexusBuilt)"
```

### Task 9: Verify the backend image can run ODL

**Step 1:** Read `deploy/docker/backend.Dockerfile`. Confirm it installs a JRE (e.g. `default-jre-headless` / `temurin`). `opendataloader-pdf` shells out to Java — no JVM, no intake. If missing, add:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless && rm -rf /var/lib/apt/lists/*
```
**Step 2:** If Docker is available locally build it (`docker build -f deploy/docker/backend.Dockerfile .`); otherwise mark "verify on VPS deploy" in the commit. Commit as group 4 of Task 7 if not already done.

---

## Phase 2 — MCP tool bridge + per-project authz (Tasks 10–16, TDD)

@superpowers:test-driven-development applies to every task here. New code lives in `backend/app/mcp_bridge/`. Reused seams (do not reimplement): `tender/router.py` service functions `create_comparison`/`list_comparisons`/`get_comparison_detail`/`create_quote`/`store_project_file_quote_document` (lines 59–196), `tender.services.jobs.enqueue`, `app.database.projects.get_project`/`user_owns_project`, `app.database.session`.

### Task 10: Declare fastmcp

**Step 1:** `uv add fastmcp` (already in venv at 3.4.2 as a transitive dep — this pins it as a direct one).
**Step 2:** Verify the header-dependency import the server will use:
```powershell
uv run python -c "from fastmcp.server.dependencies import get_http_headers; print('ok')"
```
If that import doesn't exist in this fastmcp version, check `uv run python -c "import fastmcp; help(fastmcp.server.dependencies)"` and record the correct accessor before Task 13.
**Step 3:** Commit `build(mcp): declare fastmcp for the Clerk tool bridge`.

### Task 11: Turn tokens (mint/verify)

**Files:**
- Create: `backend/app/mcp_bridge/__init__.py`, `backend/app/mcp_bridge/tokens.py`
- Modify: `backend/app/config.py` (add `agent_turn_token_secret: str = ""` following the existing Settings field style)
- Test: `backend/tests/mcp_bridge/test_tokens.py` (+ empty `backend/tests/mcp_bridge/__init__.py` if the repo's test layout needs it — mirror `tests/tender/`)

**Step 1: Write the failing tests**

```python
# backend/tests/mcp_bridge/test_tokens.py
import uuid

import pytest

from app.mcp_bridge.tokens import TurnTokenError, mint_turn_token, verify_turn_token

SECRET = "test-secret"
USER = uuid.uuid4()
PROJECT = uuid.uuid4()


def test_round_trip():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET, now=1000.0)
    claims = verify_turn_token(token, secret=SECRET, now=1500.0)
    assert claims.user_id == USER
    assert claims.project_id == PROJECT


def test_expired_token_rejected():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET, now=1000.0, ttl_seconds=60)
    with pytest.raises(TurnTokenError):
        verify_turn_token(token, secret=SECRET, now=1061.0)


def test_tampered_token_rejected():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET)
    body, sig = token.rsplit(".", 1)
    with pytest.raises(TurnTokenError):
        verify_turn_token(body + ".AAAA", secret=SECRET)


def test_wrong_secret_rejected():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET)
    with pytest.raises(TurnTokenError):
        verify_turn_token(token, secret="other")
```

**Step 2:** `uv run pytest tests/mcp_bridge/test_tokens.py -v` → FAIL (module missing).

**Step 3: Implement** (stdlib only — no new deps):

```python
# backend/app/mcp_bridge/tokens.py
"""Short-lived HMAC turn tokens binding a Hermes turn to (user, project)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass

from app.config import settings


class TurnTokenError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TurnClaims:
    user_id: uuid.UUID
    project_id: uuid.UUID
    expires_at: float


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: bytes, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), body, hashlib.sha256).digest())


def mint_turn_token(
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    ttl_seconds: int = 900,
    secret: str | None = None,
    now: float | None = None,
) -> str:
    secret = secret or settings.agent_turn_token_secret
    now = time.time() if now is None else now
    body = json.dumps(
        {"uid": str(user_id), "pid": str(project_id), "exp": now + ttl_seconds},
        separators=(",", ":"),
    ).encode()
    return f"{_b64(body)}.{_sign(body, secret)}"


def verify_turn_token(
    token: str,
    *,
    secret: str | None = None,
    now: float | None = None,
) -> TurnClaims:
    secret = secret or settings.agent_turn_token_secret
    now = time.time() if now is None else now
    try:
        body_b64, sig = token.rsplit(".", 1)
        body = _unb64(body_b64)
    except Exception as exc:
        raise TurnTokenError("malformed token") from exc
    if not hmac.compare_digest(_sign(body, secret), sig):
        raise TurnTokenError("bad signature")
    payload = json.loads(body)
    if payload["exp"] <= now:
        raise TurnTokenError("expired")
    return TurnClaims(
        user_id=uuid.UUID(payload["uid"]),
        project_id=uuid.UUID(payload["pid"]),
        expires_at=payload["exp"],
    )
```

**Step 4:** Tests → PASS. **Step 5:** Commit `feat(mcp): HMAC turn tokens for agent tool calls`.

### Task 12: Tool-layer project authorization

**Files:**
- Create: `backend/app/mcp_bridge/auth.py`
- Test: `backend/tests/mcp_bridge/test_auth.py`

**Step 1: Failing tests.** Follow the repo's mocked-session style (see `_Session` in `tests/tender/test_worker_chain.py`). Cases: (a) valid token + owned project → returns project; (b) token's `project_id` ≠ requested project → `ToolAuthError`; (c) project owned by someone else → `ToolAuthError`; (d) missing/garbage token → `ToolAuthError`. Stub `get_project`/`user_owns_project` via monkeypatch.

**Step 2: Implement:**

```python
# backend/app/mcp_bridge/auth.py
"""The security seam: every tool call is authorized per project. Never bypass."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.projects import get_project, user_owns_project
from app.mcp_bridge.tokens import TurnTokenError, verify_turn_token


class ToolAuthError(Exception):
    """Raised when a tool call is not permitted; message is safe to show the model."""


async def authorize_project_access(
    session: AsyncSession,
    *,
    authorization_header: str | None,
    project_id: uuid.UUID,
):
    if not authorization_header or not authorization_header.lower().startswith("bearer "):
        raise ToolAuthError("missing turn token")
    try:
        claims = verify_turn_token(authorization_header[7:])
    except TurnTokenError as exc:
        raise ToolAuthError(f"invalid turn token: {exc}") from exc
    if claims.project_id != project_id:
        raise ToolAuthError("turn token is not scoped to this project")
    project = await get_project(session, project_id)
    if project is None or not user_owns_project(project, claims.user_id):
        raise ToolAuthError("project not found or not accessible")
    return project
```
(Verify `get_project` / `user_owns_project` signatures in `app/database/projects.py` first; `tender/router.py:198` uses them the same way.)

**Steps 3–5:** red → green → commit `feat(mcp): tool-layer per-project authorization`.

### Task 13: MCP server + first read-only tools

**Files:**
- Create: `backend/app/mcp_bridge/server.py`
- Test: `backend/tests/mcp_bridge/test_tools_comparisons.py`

**Step 1: Failing tests** using fastmcp's in-memory client against the `FastMCP` instance, with the session factory monkeypatched to a stub session pre-loaded with a project + comparisons (repo mock style). Cases: (a) `list_tender_comparisons` with valid token returns comparison summaries; (b) cross-project token → tool error mentioning authorization; (c) `get_tender_comparison` for a comparison in another project → error.

**Step 2: Implement the server skeleton:**

```python
# backend/app/mcp_bridge/server.py
"""Clerk's MCP tool server: thin tools delegating to existing services."""
from __future__ import annotations

import uuid

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers  # verified in Task 10

from app.database.session import get_session_factory  # match the real factory name
from app.mcp_bridge.auth import ToolAuthError, authorize_project_access
from tender.router import get_comparison_detail, list_comparisons

mcp = FastMCP("clerk")


def _auth_header() -> str | None:
    headers = get_http_headers()
    return headers.get("authorization")


@mcp.tool
async def list_tender_comparisons(project_id: str) -> list[dict]:
    """List tender comparisons for a project with their quotes and stages."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        await authorize_project_access(
            session, authorization_header=_auth_header(), project_id=pid
        )
        comparisons = await list_comparisons(session, project_id=pid)
        return [
            {
                "id": str(c.id),
                "status": getattr(c, "status", None),
                "quotes": [
                    {"id": str(q.id), "builder": q.builder_name, "stage": q.stage}
                    for q in c.quotes
                ],
            }
            for c in comparisons
        ]
```
Add `get_tender_comparison(comparison_id)` the same way: load via `get_comparison_detail`, then authorize against `comparison.project_id` (reject before returning any data). Adapt the session-factory import to whatever `app/database/session.py` actually exports — read it first; reuse, don't invent.

**Steps 3–5:** red → green → commit `feat(mcp): clerk MCP server with comparison read tools`.

### Task 14: `start_tender_comparison` action tool

**Files:**
- Modify: `backend/app/mcp_bridge/server.py`
- Test: `backend/tests/mcp_bridge/test_tools_start_comparison.py`

This is the NL-trigger entry ("compare the 3 selected structural tenders"). It **composes existing services only**: `create_comparison` → per quote `create_quote` (`QuoteCreate` from `tender.schemas`) → `store_project_file_quote_document(workspace_path=...)` → `jobs.enqueue(kind="ingest_document", ...)` per document — mirroring what `post_quote_project_file_document` does at [router.py:395](../../backend/tender/router.py#L395) (read it first and copy its enqueue payload exactly).

Signature:
```python
@mcp.tool
async def start_tender_comparison(
    project_id: str,
    context: dict,
    quotes: list[dict],  # [{"builder_name": str, "workspace_paths": [str, ...]}]
) -> dict:  # {"comparison_id": ..., "quotes": [...]}
```
Test cases: (a) happy path creates comparison + quotes + docs and enqueues one `ingest_document` job per document (assert on the stub session's `.jobs`); (b) unauthorized project → error, **nothing persisted**; (c) unknown workspace path → per-quote error surfaced, other quotes still created (partial failure is allowed and expected).

Red → green → commit `feat(mcp): start_tender_comparison action tool`.

### Task 15: `search_documents` tool

**Files:**
- Modify: `backend/app/mcp_bridge/server.py`
- Test: `backend/tests/mcp_bridge/test_tools_search.py`

**Step 1:** Read `app/retrieval/retriever.py` (`DocumentRetriever`, line 15) and one existing caller (grep `DocumentRetriever(` in `app/chat/`) to get the real constructor/query signature.
**Step 2:** Failing test with a stubbed retriever: authorized call returns `[{document, snippet, score}]`; unauthorized → error.
**Step 3:** Thin tool: authorize, delegate to `DocumentRetriever`, map results. No query logic in the tool.
**Step 4:** Commit `feat(mcp): search_documents tool over existing retriever`.

### Task 16: Mount at `/mcp` + integration proof

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/mcp_bridge/test_mount.py`

**Step 1: Failing test:** build the app, assert an MCP initialize round-trip works over ASGI (use `fastmcp.Client` pointed at the mounted app if supported, else a raw httpx-ASGI POST of an `initialize` JSON-RPC message to `/mcp`) and that a tool call **without** a turn token returns an auth error (proving the seam is on by default).

**Step 2: Mount** in `app/main.py` next to the router includes:

```python
from app.mcp_bridge.server import mcp

mcp_app = mcp.http_app(path="/")
fastapi_app.mount("/mcp", mcp_app)
```
(fastmcp 3.x may require passing `lifespan=mcp_app.lifespan` into the FastAPI app or combining lifespans — check `mcp.http_app()` docs/introspection; wire whichever this version needs so both lifespans run.)

**Step 3:** Full suite + ruff:
```powershell
uv run pytest tests -q
uv run ruff check .
```
Expected: all green.

**Step 4:** Commit `feat(mcp): mount clerk MCP server at /mcp`.

**Step 5: Manual smoke (optional but recommended):** run the backend (`uv run uvicorn app.main:fastapi_app`), mint a token via a one-liner, and from WSL configure Hermes with the MCP server (`url: http://<windows-host>:8000/mcp`, the Authorization header shape recorded in Task 1 Step 3) and ask it to list comparisons. Record the result in the probe notes — this is the first end-to-end Hermes→Clerk tool call.

---

## Completion

- Update the design doc's build-sequence table (Phases 0–2 gates → done, with dates).
- Suggested follow-up plan: Phase 3 (`backend/agent/` runtime + SSE + sessions).
