# Official Planning Attachments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ground planning answers in the actual instrument text attached to the active project — NSW Acts/SEPPs/LEP via the official XML export, and DCP via an allowlisted council PDF or user upload — without treating a blocked HTML scrape as a sourced read.

**Architecture:** Keep discovery on the local NSW legislation registry. Change `read_web_source` so `legislation.nsw.gov.au` instruments are fetched from `/export/xml/current/{id}`, not the Cloudflare-guarded HTML view. Persist a successful read as a per-project official attachment (`source_type=reference`, `document_class=planning_instrument`, `knowledge_scope=official`). Add `attach_official_instrument` for explicit LEP/DCP attach (URL or already-uploaded file). Never write these rows as `project_evidence`. Do not automate around browser challenges.

**Tech Stack:** Python 3.12, FastAPI/FastMCP, SQLAlchemy `source_documents`, existing `SafePageFetcher`, pytest.

**Design:** `docs/plans/2026-08-16-official-planning-attachments-design.md`

---

## Current seams

- Registry + HTML URL: `backend/app/web_research/nsw_legislation.py`
- Read + excerpt: `backend/app/web_research/service.py`
- HTTPS/.gov.au fetch: `backend/app/web_research/fetcher.py` (HTML/PDF only today)
- Tools: `search_web` / `read_web_source` in `backend/app/mcp_bridge/server.py`
- Unused class: `planning_instrument` in `backend/ingest/types.py`
- Hosted ingest hardcodes `source_type="project_evidence"`: `backend/ingest/hosted.py`
- Identity bootstrap runs on every inbox ingest: `backend/app/workflows/document_ingest.py`

Official XML URL (human HTML stays the citation URL):

```text
https://legislation.nsw.gov.au/export/xml/current/{instrument_id}
```

Inner West LEP 2022 instrument id: `epi-2022-0457`.

---

### Task 1: NSW XML export URL and XML text extraction

**Files:**
- Modify: `backend/app/web_research/nsw_legislation.py`
- Modify: `backend/app/web_research/service.py`
- Modify: `backend/app/web_research/fetcher.py`
- Test: `backend/tests/web_research/test_nsw_legislation.py`
- Test: `backend/tests/web_research/test_service.py`
- Test: `backend/tests/web_research/test_fetcher.py`

**Step 1: Write the failing tests**

```python
def test_nsw_xml_export_url_for_an_instrument() -> None:
    assert xml_export_url("act-1979-203") == (
        "https://legislation.nsw.gov.au/export/xml/current/act-1979-203"
    )


def test_instrument_id_from_legislation_html_url() -> None:
    assert instrument_id_from_url(
        "https://legislation.nsw.gov.au/view/whole/html/inforce/current/act-1979-203"
    ) == "act-1979-203"


def test_read_uses_xml_export_for_nsw_legislation() -> None:
    # fetcher must be called with the export/xml URL, not the HTML view
    ...


def test_extract_nsw_legislation_xml_returns_title_and_section_text() -> None:
    xml = b"""<?xml version="1.0"?>
    <exdoc>
      <title>Environmental Planning and Assessment Act 1979</title>
      <content>
        <level>
          <head>4.15 Evaluation</head>
          <block><txt>A consent authority is to take into consideration the relevant matters.</txt></block>
        </level>
      </content>
    </exdoc>
    """
    title, text = extract_legislation_xml(xml)
    assert title == "Environmental Planning and Assessment Act 1979"
    assert "4.15 Evaluation" in text
    assert "consent authority" in text


def test_fetch_accepts_official_xml_content_type() -> None:
    # SafePageFetcher allows application/xml
    ...
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/web_research/test_nsw_legislation.py tests/web_research/test_service.py tests/web_research/test_fetcher.py -q`
Expected: FAIL — `xml_export_url` / `extract_legislation_xml` missing; read still hits HTML; XML content type rejected.

**Step 3: Minimal implementation**

- Add `xml_export_url(instrument_id)` and `instrument_id_from_url(url)` on the NSW module.
- Add `extract_legislation_xml(content: bytes) -> tuple[str, str]` in `service.py` using `xml.etree.ElementTree`. Strip tags, join text, prefer `<title>` then first heading.
- In `WebResearchService.read`, if the URL is a NSW legislation instrument, fetch `xml_export_url(...)` and parse XML. Keep the original HTML URL as `WebSource.url` (canonical citation).
- In `SafePageFetcher`, allow `application/xml`, `text/xml`, and `application/xhtml+xml`.
- Do not add a browser workaround. Cloudflare challenge still raises `WebFetchError`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/web_research/test_nsw_legislation.py tests/web_research/test_service.py tests/web_research/test_fetcher.py -q`
Expected: PASS

**Step 5: Commit** (only if the user asked to commit)

```bash
git add backend/app/web_research backend/tests/web_research
git commit -m "feat: read NSW legislation from the official XML export"
```

---

### Task 2: Add the Inner West LEP to the discovery registry

**Files:**
- Modify: `backend/app/web_research/nsw_legislation.py`
- Test: `backend/tests/web_research/test_nsw_legislation.py`

**Step 1: Write the failing test**

```python
def test_nsw_provider_ranks_inner_west_lep_for_an_lga_query() -> None:
    results = _search("Inner West local environmental plan heritage conservation")
    assert results[0].title == "Inner West Local Environmental Plan 2022"
    assert results[0].url.endswith("/epi-2022-0457")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/web_research/test_nsw_legislation.py::test_nsw_provider_ranks_inner_west_lep_for_an_lga_query -q`
Expected: FAIL — Inner West LEP not in ranked results.

**Step 3: Minimal implementation**

Add a `_NswLegislationSource` for Inner West LEP 2022 (`epi-2022-0457`) with topics covering LEP, Inner West, heritage, conservation area, zoning, height, FSR. Do not add a shared LGA warehouse — one registry row is enough for discovery. Other LGAs are added the same way when a project needs them.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/web_research/test_nsw_legislation.py -q`
Expected: PASS

---

### Task 3: Persist a successful official read as a project attachment

**Files:**
- Create: `backend/app/web_research/attachments.py`
- Test: `backend/tests/web_research/test_attachments.py`
- Modify: `backend/app/mcp_bridge/server.py` (`read_web_source`)

**Step 1: Write the failing tests**

```python
def test_persist_official_attachment_writes_reference_not_evidence() -> None:
    document = persist_official_attachment(
        session,
        project_id=PROJECT_ID,
        project_slug="newtown-extension",
        source=web_source,  # WebSource from a successful read
        text=full_text,
    )
    assert document.source_type == "reference"
    assert document.document_class == "planning_instrument"
    assert document.document_metadata["knowledge_scope"] == "official"
    assert document.document_metadata["official_url"] == web_source.url
    assert document.relative_path.startswith("official/")


def test_find_official_attachment_returns_fresh_snapshot() -> None:
    ...


def test_persist_official_attachment_replaces_same_url_and_keeps_previous_hash() -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/web_research/test_attachments.py -q`
Expected: FAIL — module missing.

**Step 3: Minimal implementation**

`persist_official_attachment` upserts `SourceDocument` on `(project_id, relative_path)` where `relative_path` is `official/{instrument_id_or_slug}`. Fields:

| Field | Value |
| --- | --- |
| `source_type` | `reference` |
| `document_class` | `planning_instrument` |
| `knowledge_scope` | `official` |
| `official_url` | canonical HTML/PDF URL |
| `authority_class` | from `WebSource` |
| `retrieved_at` | ISO timestamp |
| `content_hash` | sha256 of fetched bytes |
| `previous_content_hash` | prior hash when replaced |
| `normalized_content` | extracted text |

No embeddings in this pass. `find_document_text` / `get_document` read `normalized_content`.

`read_web_source` after a successful live read calls persist. If a snapshot exists and is younger than 7 days (`OFFICIAL_ATTACHMENT_MAX_AGE_DAYS`), return it instead of fetching — unless `refresh=True`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/web_research/test_attachments.py tests/mcp_bridge/test_tools_web_research.py -q`
Expected: PASS

---

### Task 4: `attach_official_instrument` MCP tool

**Files:**
- Modify: `backend/app/mcp_bridge/server.py`
- Modify: `backend/app/agent/workspace_instructions.py`
- Modify: `backend/app/agent/turn_context.py`
- Test: `backend/tests/mcp_bridge/test_tools_web_research.py`
- Test: `backend/tests/agent/test_workspace_instructions.py`
- Test: `backend/tests/agent/test_turn_context.py`

**Step 1: Write the failing tests**

```python
def test_attach_official_instrument_from_nsw_instrument_id(monkeypatch) -> None:
    # attach_official_instrument(project_id, instrument_id="act-1979-203")
    # fetches XML export, persists official attachment, returns WebSource + document_id


def test_attach_official_instrument_from_council_pdf_url(monkeypatch) -> None:
    # url=https://www.innerwest.nsw.gov.au/.../dcp.pdf
    # uses existing PDF extraction; persists official attachment


def test_attach_official_instrument_from_uploaded_document(monkeypatch) -> None:
    # document_id of an already-ingested inbox PDF
    # retags source_type=reference, document_class=planning_instrument,
    # knowledge_scope=official; does not copy into platform knowledge


def test_attach_official_instrument_rejects_non_gov_url() -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/mcp_bridge/test_tools_web_research.py -q -k attach`
Expected: FAIL — tool missing.

**Step 3: Minimal implementation**

New tool `attach_official_instrument(project_id, instrument_id=None, url=None, document_id=None, section_hint=None, refresh=False)`.

Exactly one of `instrument_id`, `url`, `document_id`. Status messages: “Attaching official instrument” / “Attached official instrument” / “Official instrument attach failed”.

Update workspace + turn-context guidance: if a planning question needs current controls and no matching official attachment exists, attach it (or ask for the DCP PDF). Do not answer from search titles as if the page was read. After attach, cite retrieval date.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/mcp_bridge/test_tools_web_research.py tests/agent/test_workspace_instructions.py tests/agent/test_turn_context.py -q`
Expected: PASS

---

### Task 5: Classify LEP/DCP filenames; skip identity bootstrap

**Files:**
- Modify: `backend/ingest/classify.py`
- Modify: `backend/ingest/router.py` (PDF extractor for `planning_instrument`)
- Modify: `backend/app/projects/identity_bootstrap.py`
- Test: `backend/tests/ingest/test_classify.py`
- Test: `backend/tests/projects/test_identity_bootstrap.py`

**Step 1: Write the failing tests**

```python
def test_classify_lep_filename_as_planning_instrument() -> None:
    entry = _entry("delivery-newtown/official/Inner-West-LEP-2022.pdf")
    assert classify_entry(entry).document_class == "planning_instrument"


def test_classify_dcp_filename_as_planning_instrument() -> None:
    entry = _entry("delivery-newtown/_inbox/Inner West DCP 2022.pdf")
    assert classify_entry(entry).document_class == "planning_instrument"


def test_classify_does_not_treat_dcp_assessment_report_as_instrument() -> None:
    entry = _entry("delivery-newtown/_inbox/Heritage DCP assessment report.pdf")
    assert classify_entry(entry).document_class == "report"


def test_bootstrap_skips_official_planning_instruments() -> None:
    # knowledge_scope=official or document_class=planning_instrument → noop
    ...
```

Inbox upload of a DCP still starts as `project_evidence` until `attach_official_instrument(document_id=...)` retags it. Classification is only for register/bootstrap safety.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ingest/test_classify.py tests/projects/test_identity_bootstrap.py -q`
Expected: FAIL — class never assigned; bootstrap still runs.

**Step 3: Minimal implementation**

Filename tokens (conservative): `local environmental plan`, `development control plan`, or a whole-word `lep` / `dcp` that is not followed by `assessment` / `report` / `statement`. Skip bootstrap when `document_class == "planning_instrument"` or `knowledge_scope == "official"`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingest/test_classify.py tests/projects/test_identity_bootstrap.py -q`
Expected: PASS

---

### Task 6: Label official attachments in document tools and answer trace

**Files:**
- Modify: `backend/app/mcp_bridge/server.py` (`find_document_text`, `get_document`, `search_documents`)
- Modify: `backend/app/api/chat.py` (`_agent_source_trace` if needed)
- Modify: `frontend/src/lib/answer-trace.ts` only if a persisted official attachment should show as a web/official source without a live `read_web_source`
- Test: `backend/tests/mcp_bridge/test_project_file_tools.py` (or a focused new test)
- Test: `backend/tests/agent/test_agent_chat_api.py`
- Test: `frontend/src/lib/answer-trace.test.ts` if that file exists, else `frontend/src/components/chat/AssistantMessage.test.tsx`

**Step 1: Write the failing tests**

Document tool results for official rows include `knowledge_scope: "official"` and `source_type: "reference"`. Answer-trace stays **Internet search** when only `search_web` ran; it becomes a sourced official chip when `read_web_source` or `attach_official_instrument` persisted a source.

**Step 2–4:** Fail, implement, pass as above.

---

### Task 7: Architecture note

**Files:**
- Modify: `docs/architecture.md` §6 official web research paragraph

State that NSW legislation reads use the official XML export, that a successful read may be stored as a per-project official attachment, and that browser challenges still fail closed. Do not describe a shared LGA cache.

---

## Out of scope (do not implement)

- Shared LGA / statewide instrument warehouse
- Spatial Viewer or zoning-map scrape
- Headless browser / stealth User-Agent
- Auto-crawling a council site for “the” DCP
- Embedding official attachments in this pass
- Changing official text into `project_evidence`

## Verification

```bash
cd backend
uv run pytest tests/web_research tests/mcp_bridge/test_tools_web_research.py tests/ingest/test_classify.py tests/projects/test_identity_bootstrap.py tests/agent/test_workspace_instructions.py tests/agent/test_turn_context.py tests/agent/test_agent_chat_api.py -q
```

Frontend, only if Task 6 touched UI:

```bash
cd frontend
pnpm exec vitest run src/components/chat/AssistantMessage.test.tsx src/lib/answer-trace.ts
```
