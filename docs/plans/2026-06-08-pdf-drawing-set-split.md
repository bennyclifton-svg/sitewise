# PDF Drawing-Set Auto-Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a user drops a single PDF that is actually a set of separate drawings (one drawing per page), detect it, show a confirm-preview, and on confirmation split it into N single-page PDFs that ingest into the document repository as separate evidence documents.

**Architecture:** A two-phase upload for PDFs. Phase 1 (`analyze`) stages the raw PDF to a `_staging/` storage key and runs a heuristic drawing-set detector (PyMuPDF) plus per-sheet title extraction, returning a proposal without creating evidence. Phase 2 commits the user's choice: `split` (split staged PDF into single-page PDFs and run the existing per-file ingest for each, then delete staging) or `commit` (move staged PDF into `_inbox` and ingest once). All new logic sits behind the PDF path; the existing `ingest_hosted_file` pipeline, object storage, classification, and search are reused unchanged.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / PyMuPDF (`fitz`, already a dependency) / pytest (`uv run pytest`). Frontend: React + TypeScript + Vite (`pnpm`), existing `DocumentRepositoryPanel`.

**Design reference:** `docs/plans/2026-06-08-pdf-drawing-set-split-design.md` — read it before starting.

**Conventions to match (read these first):**
- `backend/app/inbox/service.py` — `InboxUploadItem`, `InboxUploadOutcome`, `upload_inbox_files`, `_upload_single_file`.
- `backend/app/inbox/paths.py` — `sanitize_filename`, `build_inbox_workspace_path`, `build_storage_key`.
- `backend/app/storage/project_files.py` — `upload_project_file`, `download_project_file`, `delete_project_file`.
- `backend/app/api/projects.py` — endpoint style, `_require_project_owner`.
- `backend/tests/inbox/test_upload.py` — the mocked-session + `TestClient` test pattern.
- `backend/tests/conftest.py` — `run_async` helper for async tests.

**Commands:**
- Backend tests: `cd backend && uv run pytest <path> -v`
- Frontend typecheck: `cd frontend && pnpm exec tsc -b --noEmit`
- Frontend test (if vitest configured): `cd frontend && pnpm test`

**Commit discipline:** TDD per task (red → green → commit). End every commit message with:
```
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 1: PDF inspection helper (page geometry + text)

A pure function that reads PDF bytes and returns per-page facts the detector and title extractor both need. Keeps PyMuPDF usage in one place.

**Files:**
- Create: `backend/app/inbox/pdf_inspect.py`
- Test: `backend/tests/inbox/test_pdf_inspect.py`

**Step 1: Write the failing test**

Build fixtures in-memory with `fitz` so tests need no external files. Add a helper at the top of the test module:

```python
import fitz

def _make_pdf(pages):
    # pages: list of (width, height, text)
    doc = fitz.open()
    for width, height, text in pages:
        page = doc.new_page(width=width, height=height)
        if text:
            page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def test_inspect_returns_page_geometry_and_text():
    from app.inbox.pdf_inspect import inspect_pdf

    data = _make_pdf([
        (1191, 842, "SITE PLAN SHEET: 2 OF 20 SCALE: 1:200"),
        (1191, 842, "GROUND FLOOR PLAN SHEET 3 OF 20"),
    ])
    info = inspect_pdf(data)

    assert info.page_count == 2
    assert info.encrypted is False
    assert info.pages[0].width == 1191
    assert info.pages[0].height == 842
    assert info.pages[0].is_landscape is True
    assert "SITE PLAN" in info.pages[0].text
    assert info.pages[0].has_text is True
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/inbox/test_pdf_inspect.py -v`
Expected: FAIL — `ModuleNotFoundError: app.inbox.pdf_inspect`.

**Step 3: Write minimal implementation**

```python
# backend/app/inbox/pdf_inspect.py
from __future__ import annotations

from dataclasses import dataclass

import fitz


@dataclass(frozen=True, slots=True)
class PageInfo:
    index: int          # 1-based page number
    width: float
    height: float
    text: str

    @property
    def is_landscape(self) -> bool:
        return self.width > self.height

    @property
    def long_edge(self) -> float:
        return max(self.width, self.height)

    @property
    def has_text(self) -> bool:
        return len(self.text.strip()) > 0


@dataclass(frozen=True, slots=True)
class PdfInfo:
    page_count: int
    encrypted: bool
    pages: list[PageInfo]


def inspect_pdf(data: bytes) -> PdfInfo:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        encrypted = bool(doc.needs_pass)
        pages: list[PageInfo] = []
        if not encrypted:
            for i in range(doc.page_count):
                page = doc[i]
                rect = page.rect
                pages.append(
                    PageInfo(
                        index=i + 1,
                        width=round(rect.width, 2),
                        height=round(rect.height, 2),
                        text=page.get_text() or "",
                    )
                )
        return PdfInfo(page_count=doc.page_count, encrypted=encrypted, pages=pages)
    finally:
        doc.close()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/inbox/test_pdf_inspect.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/inbox/pdf_inspect.py backend/tests/inbox/test_pdf_inspect.py
git commit -m "feat: add PDF inspection helper for drawing-set detection"
```

---

## Task 2: Drawing-set detector

Scored heuristic deciding whether a PDF is a set of separate drawings.

**Files:**
- Create: `backend/app/inbox/drawing_detection.py`
- Test: `backend/tests/inbox/test_drawing_detection.py`
- Integration fixture: real file at `data/delivery-house/L18 CC Plans.pdf`.

**Step 1: Write the failing tests**

Reuse the `_make_pdf` helper (copy it into this test module). Tests:

```python
import fitz  # plus _make_pdf helper as in Task 1

TITLE_BLOCK = "SHEET: 2 OF 20 SCALE: 1:200 DRAWN BY: AW DATE: 11.03.24"

def test_detects_drawing_set_uniform_a3_landscape_with_title_blocks():
    from app.inbox.drawing_detection import detect_drawing_set
    data = _make_pdf([(1191, 842, f"SITE PLAN {TITLE_BLOCK}")] * 6)
    result = detect_drawing_set(data)
    assert result.is_drawing_set is True
    assert result.confidence >= 0.7
    assert result.page_count == 6

def test_rejects_single_page():
    from app.inbox.drawing_detection import detect_drawing_set
    data = _make_pdf([(1191, 842, f"SITE PLAN {TITLE_BLOCK}")])
    assert detect_drawing_set(data).is_drawing_set is False

def test_rejects_portrait_a4_report():
    from app.inbox.drawing_detection import detect_drawing_set
    body = "This report describes the methodology and findings in detail. " * 20
    data = _make_pdf([(595, 842, body)] * 8)
    assert detect_drawing_set(data).is_drawing_set is False

def test_rejects_landscape_without_title_block_keywords():
    from app.inbox.drawing_detection import detect_drawing_set
    data = _make_pdf([(1191, 842, "Slide content only, no title block")] * 4)
    assert detect_drawing_set(data).is_drawing_set is False

def test_rejects_mixed_page_sizes():
    from app.inbox.drawing_detection import detect_drawing_set
    pages = [(1191, 842, f"SITE PLAN {TITLE_BLOCK}"), (595, 842, "report text")]
    assert detect_drawing_set(_make_pdf(pages)).is_drawing_set is False
```

Add a real-file integration test (skip if the fixture is absent so CI without data still passes):

```python
import os
import pytest

L18 = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "data", "delivery-house", "L18 CC Plans.pdf",
)

@pytest.mark.skipif(not os.path.exists(L18), reason="L18 fixture not present")
def test_detects_real_l18_drawing_set():
    from app.inbox.drawing_detection import detect_drawing_set
    with open(L18, "rb") as fh:
        result = detect_drawing_set(fh.read())
    assert result.is_drawing_set is True
    assert result.page_count == 20
    assert result.confidence >= 0.8
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/inbox/test_drawing_detection.py -v`
Expected: FAIL — module missing.

**Step 3: Write minimal implementation**

```python
# backend/app/inbox/drawing_detection.py
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.inbox.pdf_inspect import PdfInfo, inspect_pdf

_KEYWORD_PATTERNS = [
    re.compile(r"\bSCALE\b", re.I),
    re.compile(r"\bSHEET\b", re.I),
    re.compile(r"\bDRAWN\b", re.I),
    re.compile(r"\bREV\b", re.I),
    re.compile(r"\bDWG\b", re.I),
    re.compile(r"\bDATE\b", re.I),
    re.compile(r"\b\d+\s*OF\s*\d+\b", re.I),
]


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    min_pages: int = 2
    uniform_dims_tolerance_pt: float = 2.0
    uniform_dims_min_fraction: float = 0.8
    min_long_edge_pt: float = 1000.0
    min_keyword_hits_per_page: int = 2
    keyword_min_fraction: float = 0.5


@dataclass(frozen=True, slots=True)
class DetectionResult:
    is_drawing_set: bool
    confidence: float
    page_count: int
    scores: dict = field(default_factory=dict)


def _page_has_title_block(text: str, min_hits: int) -> bool:
    hits = sum(1 for pat in _KEYWORD_PATTERNS if pat.search(text))
    return hits >= min_hits


def detect_from_info(info: PdfInfo, config: DetectionConfig | None = None) -> DetectionResult:
    config = config or DetectionConfig()

    if info.encrypted or info.page_count < config.min_pages or not info.pages:
        return DetectionResult(False, 0.0, info.page_count, {"reason": "gate"})

    # Modal page size within tolerance.
    size_keys = [
        (round(p.width / config.uniform_dims_tolerance_pt),
         round(p.height / config.uniform_dims_tolerance_pt))
        for p in info.pages
    ]
    modal_key, modal_count = Counter(size_keys).most_common(1)[0]
    uniform_fraction = modal_count / len(info.pages)

    modal_pages = [p for p, k in zip(info.pages, size_keys) if k == modal_key]
    modal_page = modal_pages[0]
    large_landscape = (
        modal_page.is_landscape and modal_page.long_edge >= config.min_long_edge_pt
    )

    keyword_pages = sum(
        1 for p in info.pages
        if _page_has_title_block(p.text, config.min_keyword_hits_per_page)
    )
    keyword_fraction = keyword_pages / len(info.pages)

    is_drawing_set = (
        uniform_fraction >= config.uniform_dims_min_fraction
        and large_landscape
        and keyword_fraction >= config.keyword_min_fraction
    )

    confidence = round(
        (0.4 * uniform_fraction)
        + (0.3 * (1.0 if large_landscape else 0.0))
        + (0.3 * keyword_fraction),
        3,
    )

    return DetectionResult(
        is_drawing_set=is_drawing_set,
        confidence=confidence,
        page_count=info.page_count,
        scores={
            "uniform_dims_fraction": round(uniform_fraction, 3),
            "large_format_landscape": large_landscape,
            "keyword_fraction": round(keyword_fraction, 3),
        },
    )


def detect_drawing_set(data: bytes, config: DetectionConfig | None = None) -> DetectionResult:
    return detect_from_info(inspect_pdf(data), config)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/inbox/test_drawing_detection.py -v`
Expected: PASS (real-L18 test passes locally where `data/` exists).

**Step 5: Commit**

```bash
git add backend/app/inbox/drawing_detection.py backend/tests/inbox/test_drawing_detection.py
git commit -m "feat: add heuristic drawing-set detector"
```

---

## Task 3: Per-sheet title extraction

Extract a human-meaningful title per page with a positional fallback, and build collision-safe filenames.

**Files:**
- Create: `backend/app/inbox/sheet_titles.py`
- Test: `backend/tests/inbox/test_sheet_titles.py`

**Step 1: Write the failing tests**

```python
import fitz  # plus _make_pdf helper

def test_extracts_titles_and_builds_unique_filenames():
    from app.inbox.sheet_titles import build_sheet_plan
    data = _make_pdf([
        (1191, 842, "SUBMISSION PLANS SITE PLAN SHEET: 2 OF 20"),
        (1191, 842, "SUBMISSION PLANS ELEVATIONS SHEET: 5 OF 20"),
        (1191, 842, "SUBMISSION PLANS ELEVATIONS SHEET: 6 OF 20"),
    ])
    sheets = build_sheet_plan(data, source_filename="L18 CC Plans.pdf")
    titles = [s.title for s in sheets]
    assert "Site Plan" in titles[0] or titles[0] == "Site Plan"
    # Repeated "Elevations" titles must yield distinct filenames.
    filenames = [s.filename for s in sheets]
    assert len(set(filenames)) == len(filenames)
    assert filenames[0].endswith(".pdf")

def test_positional_fallback_when_no_text():
    from app.inbox.sheet_titles import build_sheet_plan
    data = _make_pdf([(1191, 842, ""), (1191, 842, "")])
    sheets = build_sheet_plan(data, source_filename="scan.pdf")
    assert sheets[0].title == "Sheet 01"
    assert sheets[1].filename != sheets[0].filename
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/inbox/test_sheet_titles.py -v`
Expected: FAIL — module missing.

**Step 3: Write minimal implementation**

```python
# backend/app/inbox/sheet_titles.py
from __future__ import annotations

import re
from dataclasses import dataclass

import fitz

_SHEET_SEQ = re.compile(r"(\d+)\s*OF\s*(\d+)", re.I)
_SCALE = re.compile(r"\b1\s*:\s*\d+\b")
_BOILERPLATE = re.compile(
    r"copyright|owned by|liable|disclaimer|gspublisher|abn|pty|ph:|phone|fax|"
    r"avenue|street|road|nsw|submission plans",
    re.I,
)
_TITLE_CANDIDATES = re.compile(
    r"\b(SITE PLAN|GROUND FLOOR|FIRST FLOOR|ELEVATIONS?|SECTIONS?|SLAB PLAN|"
    r"SLAB PENETRATIONS?|ELECTRICAL|WET AREA[S]?|KITCHEN|WINDOW SCHEDULE|"
    r"LANDSCAPE|SEDIMENT|EXTERNAL|CONCEPT|TITLE PAGE|FLOOR PLAN|ROOF PLAN|"
    r"DRAINAGE|STORMWATER|FOOTING|BRACING|FRAMING)\b[^\n]{0,40}",
    re.I,
)
_MAX_TITLE_LEN = 60


@dataclass(frozen=True, slots=True)
class SheetPlan:
    index: int          # 1-based page number
    title: str
    filename: str
    sheet_number_label: str | None
    scale: str | None


def _titlecase(value: str) -> str:
    cleaned = " ".join(value.split())
    return cleaned[:_MAX_TITLE_LEN].title()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    return " ".join(slug.split())


def _extract_title(text: str) -> str | None:
    if not text.strip():
        return None
    # Prefer a known drawing-type caption.
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or _BOILERPLATE.search(line):
            continue
        match = _TITLE_CANDIDATES.search(line)
        if match:
            return _titlecase(match.group(0))
    # Fallback: first short, non-boilerplate, mostly-alpha line.
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if 3 <= len(line) <= 40 and not _BOILERPLATE.search(line):
            alpha = sum(c.isalpha() for c in line)
            if alpha >= max(3, len(line) // 2):
                return _titlecase(line)
    return None


def build_sheet_plan(data: bytes, *, source_filename: str) -> list[SheetPlan]:
    stem = re.sub(r"\.pdf$", "", source_filename, flags=re.I)
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        plans: list[SheetPlan] = []
        used: set[str] = set()
        for i in range(doc.page_count):
            text = doc[i].get_text() or ""
            seq = _SHEET_SEQ.search(text)
            sheet_no = int(seq.group(1)) if seq else (i + 1)
            number_label = seq.group(0).upper() if seq else None
            scale_match = _SCALE.search(text)

            title = _extract_title(text) or f"Sheet {i + 1:02d}"
            nn = f"{sheet_no:02d}"
            base = f"{stem} - {nn} {_slugify(title)}".strip()
            filename = f"{base}.pdf"
            suffix = 2
            while filename.lower() in used:
                filename = f"{base} ({suffix}).pdf"
                suffix += 1
            used.add(filename.lower())

            plans.append(
                SheetPlan(
                    index=i + 1,
                    title=title,
                    filename=filename,
                    sheet_number_label=number_label,
                    scale=scale_match.group(0) if scale_match else None,
                )
            )
        return plans
    finally:
        doc.close()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/inbox/test_sheet_titles.py -v`
Expected: PASS. Also spot-check against the real file:
`cd backend && uv run python -c "from app.inbox.sheet_titles import build_sheet_plan; print([s.title for s in build_sheet_plan(open(r'../data/delivery-house/L18 CC Plans.pdf','rb').read(), source_filename='L18 CC Plans.pdf')])"`
Expected: a list including "Site Plan", "Ground Floor", "Elevations", etc.

**Step 5: Commit**

```bash
git add backend/app/inbox/sheet_titles.py backend/tests/inbox/test_sheet_titles.py
git commit -m "feat: add per-sheet title extraction and filename builder"
```

---

## Task 4: PDF page splitter

Split a multi-page PDF into per-page byte blobs, lossless.

**Files:**
- Create: `backend/app/inbox/pdf_split.py`
- Test: `backend/tests/inbox/test_pdf_split.py`

**Step 1: Write the failing tests**

```python
import fitz  # plus _make_pdf helper

def test_splits_into_single_pages_preserving_text():
    from app.inbox.pdf_split import split_pdf_pages
    data = _make_pdf([
        (1191, 842, "PAGE ONE SITE PLAN"),
        (1191, 842, "PAGE TWO ELEVATIONS"),
    ])
    parts = split_pdf_pages(data)
    assert len(parts) == 2
    for part in parts:
        d = fitz.open(stream=part, filetype="pdf")
        assert d.page_count == 1
        d.close()
    assert "PAGE ONE" in fitz.open(stream=parts[0], filetype="pdf")[0].get_text()
    assert "PAGE TWO" in fitz.open(stream=parts[1], filetype="pdf")[0].get_text()

def test_rejects_pdf_over_page_cap():
    import pytest
    from app.inbox.pdf_split import split_pdf_pages, PdfSplitError
    data = _make_pdf([(595, 842, "x")] * 3)
    with pytest.raises(PdfSplitError):
        split_pdf_pages(data, max_pages=2)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/inbox/test_pdf_split.py -v`
Expected: FAIL — module missing.

**Step 3: Write minimal implementation**

```python
# backend/app/inbox/pdf_split.py
from __future__ import annotations

import fitz

DEFAULT_MAX_PAGES = 200


class PdfSplitError(ValueError):
    pass


def split_pdf_pages(data: bytes, *, max_pages: int = DEFAULT_MAX_PAGES) -> list[bytes]:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if doc.needs_pass:
            raise PdfSplitError("PDF is encrypted")
        if doc.page_count > max_pages:
            raise PdfSplitError(
                f"PDF has {doc.page_count} pages, exceeding the limit of {max_pages}"
            )
        parts: list[bytes] = []
        for i in range(doc.page_count):
            out = fitz.open()
            out.insert_pdf(doc, from_page=i, to_page=i)
            parts.append(out.tobytes(garbage=4, deflate=True))
            out.close()
        return parts
    finally:
        doc.close()
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/inbox/test_pdf_split.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/inbox/pdf_split.py backend/tests/inbox/test_pdf_split.py
git commit -m "feat: add lossless PDF page splitter"
```

---

## Task 5: Staging storage + analyze service

Stage the raw PDF and produce the analysis proposal. Staging key uses a `_staging/` prefix so it is never treated as evidence.

**Files:**
- Create: `backend/app/inbox/split_service.py`
- Modify: `backend/app/schemas/projects.py` (add response schemas after `InboxUploadResponse`, line ~55)
- Test: `backend/tests/inbox/test_split_service.py`

**Step 1: Write the failing test** (service-level, storage + DB mocked)

```python
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import fitz
from app.database.project import Project
from tests.conftest import run_async

# reuse _make_pdf helper

def _project():
    return Project(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        owner_user_id=uuid.uuid4(), slug="demo", title="Demo",
        workspace_path="04-projects/demo", phase="procurement",
        archetype="small-commercial", user_role="architect-pm", state="NSW",
        status="active", project_metadata={},
        created_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
    )

def test_analyze_stages_pdf_and_returns_proposal():
    from app.inbox.split_service import analyze_pdf_upload
    data = _make_pdf([(1191, 842, "SITE PLAN SHEET: 2 OF 20 SCALE: 1:200")] * 4)

    async def _run():
        with patch("app.inbox.split_service.upload_project_file") as mock_upload:
            result = await analyze_pdf_upload(
                project=_project(), filename="L18 CC Plans.pdf", content=data,
            )
        mock_upload.assert_called_once()
        assert result.is_drawing_set is True
        assert result.page_count == 4
        assert len(result.pages) == 4
        assert result.staging_id

    run_async(_run())
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/inbox/test_split_service.py -v`
Expected: FAIL — module missing.

**Step 3: Add schemas** to `backend/app/schemas/projects.py` after `InboxUploadResponse`:

```python
class PdfSheetProposal(BaseModel):
    index: int
    proposed_title: str
    filename: str
    has_text: bool


class PdfAnalyzeResponse(BaseModel):
    staging_id: str
    is_drawing_set: bool
    confidence: float
    page_count: int
    scores: dict = Field(default_factory=dict)
    pages: list[PdfSheetProposal] = Field(default_factory=list)
```

(Confirm `Field` is already imported in that module — it is, used by `CreateProjectRequest`.)

**Step 4: Write the service implementation**

```python
# backend/app/inbox/split_service.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import structlog

from app.database.project import Project
from app.inbox.drawing_detection import detect_from_info
from app.inbox.pdf_inspect import inspect_pdf
from app.inbox.sheet_titles import build_sheet_plan
from app.storage.project_files import download_project_file, upload_project_file

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SheetProposal:
    index: int
    proposed_title: str
    filename: str
    has_text: bool


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    staging_id: str
    storage_key: str
    is_drawing_set: bool
    confidence: float
    page_count: int
    scores: dict
    pages: list[SheetProposal]


def _staging_storage_key(project_id: uuid.UUID, staging_id: str) -> str:
    return f"{project_id}/_staging/{staging_id}.pdf"


async def analyze_pdf_upload(
    *, project: Project, filename: str, content: bytes
) -> AnalyzeResult:
    staging_id = uuid.uuid4().hex
    storage_key = _staging_storage_key(project.id, staging_id)

    await asyncio.to_thread(
        upload_project_file, storage_key=storage_key, content=content, filename=filename
    )

    info = inspect_pdf(content)
    detection = detect_from_info(info)
    sheet_plan = build_sheet_plan(content, source_filename=filename)

    pages = [
        SheetProposal(
            index=plan.index,
            proposed_title=plan.title,
            filename=plan.filename,
            has_text=page.has_text if page else False,
        )
        for plan, page in zip(sheet_plan, info.pages)
    ]

    logger.info(
        "pdf_analyzed",
        project=project.slug,
        staging_id=staging_id,
        is_drawing_set=detection.is_drawing_set,
        page_count=detection.page_count,
    )

    return AnalyzeResult(
        staging_id=staging_id,
        storage_key=storage_key,
        is_drawing_set=detection.is_drawing_set,
        confidence=detection.confidence,
        page_count=detection.page_count,
        scores=detection.scores,
        pages=pages,
    )
```

**Step 5: Run test to verify it passes & commit**

Run: `cd backend && uv run pytest tests/inbox/test_split_service.py -v`
Expected: PASS.

```bash
git add backend/app/inbox/split_service.py backend/app/schemas/projects.py backend/tests/inbox/test_split_service.py
git commit -m "feat: add PDF analyze/staging service and schemas"
```

---

## Task 6: Split commit service (split staged PDF → ingest N sheets)

Download the staged PDF, split it, ingest each sheet via the existing upload path, attach provenance, delete staging.

**Files:**
- Modify: `backend/app/inbox/split_service.py` (add `split_staged_pdf` + `commit_staged_pdf_single`)
- Modify: `backend/app/inbox/service.py` — extend `_upload_single_file` to accept optional `extra_metadata` and `original_filename` overrides (see note), OR add a thin wrapper. See Step 3.
- Test: `backend/tests/inbox/test_split_service.py` (add cases)

**Note on reuse:** `_upload_single_file` currently derives everything from `InboxUploadItem`. The split path needs to (a) pass page bytes under the extracted filename and (b) record provenance metadata. The simplest non-invasive approach: build an `InboxUploadItem` per sheet with `filename=plan.filename` and `content=page_bytes`, call the existing `upload_inbox_files`, then in a follow-up pass write provenance metadata onto the resulting `SourceDocument.document_metadata`. Implement provenance write as a small helper to keep `service.py` untouched. If during implementation you find metadata must be set at ingest time for the classifier/title, prefer threading an optional `metadata_overrides` param through `ingest_hosted_file` — but only if tests prove it's needed (YAGNI).

**Step 1: Write the failing tests**

```python
def test_split_staged_pdf_ingests_each_sheet_and_deletes_staging():
    from app.inbox.split_service import split_staged_pdf
    data = _make_pdf([
        (1191, 842, "SITE PLAN SHEET: 2 OF 20"),
        (1191, 842, "ELEVATIONS SHEET: 5 OF 20"),
    ])
    project = _project()
    session = AsyncMock()

    async def fake_upload(session, *, project, items):
        from app.inbox.service import InboxUploadOutcome
        return [
            InboxUploadOutcome(
                id=uuid.uuid4(), filename=item.filename,
                workspace_path=f"{project.workspace_path}/_inbox/{item.filename}",
                content_hash="h", size_bytes=len(item.content),
                ingest_status="ingested", message="ok",
            )
            for item in items
        ]

    async def _run():
        with (
            patch("app.inbox.split_service.download_project_file", return_value=data),
            patch("app.inbox.split_service.upload_inbox_files", side_effect=fake_upload) as mock_ingest,
            patch("app.inbox.split_service.delete_project_file") as mock_delete,
            patch("app.inbox.split_service._attach_split_provenance", new=AsyncMock()),
        ):
            outcomes = await split_staged_pdf(
                session, project=project, staging_id="abc123",
                source_filename="L18 CC Plans.pdf",
            )
        assert len(outcomes) == 2
        mock_ingest.assert_called_once()
        mock_delete.assert_called_once()  # staging removed

    run_async(_run())

def test_split_staged_pdf_keeps_staging_when_all_fail():
    from app.inbox.split_service import split_staged_pdf
    data = _make_pdf([(1191, 842, "SITE PLAN SHEET: 2 OF 20")])
    project = _project()

    async def fake_upload(session, *, project, items):
        from app.inbox.service import InboxUploadOutcome
        return [
            InboxUploadOutcome(
                id=uuid.uuid4(), filename=i.filename, workspace_path="w",
                content_hash="h", size_bytes=1, ingest_status="failed", message="boom",
            ) for i in items
        ]

    async def _run():
        with (
            patch("app.inbox.split_service.download_project_file", return_value=data),
            patch("app.inbox.split_service.upload_inbox_files", side_effect=fake_upload),
            patch("app.inbox.split_service.delete_project_file") as mock_delete,
            patch("app.inbox.split_service._attach_split_provenance", new=AsyncMock()),
        ):
            await split_staged_pdf(
                AsyncMock(), project=project, staging_id="abc123",
                source_filename="x.pdf",
            )
        mock_delete.assert_not_called()  # staging retained for retry

    run_async(_run())
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/inbox/test_split_service.py -v`
Expected: FAIL — `split_staged_pdf` missing.

**Step 3: Implement** (append to `split_service.py`)

```python
import hashlib

from sqlalchemy import update

from app.database.session import AsyncSession  # if not already importable, use typing only
from app.database.source_document import SourceDocument
from app.inbox.pdf_split import split_pdf_pages
from app.inbox.service import InboxUploadItem, InboxUploadOutcome, upload_inbox_files
from app.storage.project_files import delete_project_file


async def _attach_split_provenance(session, *, outcomes, sheet_plans, source_filename, source_hash):
    by_filename = {plan.filename: plan for plan in sheet_plans}
    for outcome in outcomes:
        plan = by_filename.get(outcome.filename)
        if plan is None or outcome.ingest_status not in {"ingested", "skipped"}:
            continue
        metadata = {
            "split_from": source_filename,
            "split_source_hash": source_hash,
            "sheet_index": plan.index,
            "sheet_total": len(sheet_plans),
            "sheet_number_label": plan.sheet_number_label,
            "sheet_scale": plan.scale,
            "split_method": "heuristic_v1",
            "title": plan.title,
        }
        # Merge into existing metadata (JSONB). Load, update, flush.
        doc = await session.get(SourceDocument, outcome.id)
        if doc is not None:
            merged = dict(doc.document_metadata or {})
            merged.update({k: v for k, v in metadata.items() if v is not None})
            doc.document_metadata = merged
    await session.flush()


async def split_staged_pdf(
    session, *, project: Project, staging_id: str, source_filename: str
) -> list[InboxUploadOutcome]:
    storage_key = _staging_storage_key(project.id, staging_id)
    content = await asyncio.to_thread(download_project_file, storage_key=storage_key)
    source_hash = hashlib.sha256(content).hexdigest()

    page_blobs = await asyncio.to_thread(split_pdf_pages, content)
    sheet_plans = build_sheet_plan(content, source_filename=source_filename)

    items = [
        InboxUploadItem(filename=plan.filename, content=blob)
        for plan, blob in zip(sheet_plans, page_blobs)
    ]
    outcomes = await upload_inbox_files(session, project=project, items=items)

    succeeded = [o for o in outcomes if o.ingest_status in {"ingested", "skipped"}]
    if succeeded:
        await _attach_split_provenance(
            session, outcomes=outcomes, sheet_plans=sheet_plans,
            source_filename=source_filename, source_hash=source_hash,
        )
        await session.commit()
        await asyncio.to_thread(delete_project_file, storage_key=storage_key)
    else:
        logger.warning("pdf_split_all_failed", staging_id=staging_id, project=project.slug)

    return outcomes


async def commit_staged_pdf_single(
    session, *, project: Project, staging_id: str, source_filename: str
) -> InboxUploadOutcome:
    storage_key = _staging_storage_key(project.id, staging_id)
    content = await asyncio.to_thread(download_project_file, storage_key=storage_key)
    outcomes = await upload_inbox_files(
        session, project=project,
        items=[InboxUploadItem(filename=source_filename, content=content)],
    )
    await asyncio.to_thread(delete_project_file, storage_key=storage_key)
    return outcomes[0]
```

Note: `upload_inbox_files` already calls `session.commit()`. The provenance helper runs after and commits again; verify in the test that double-commit on the mocked session is acceptable (it is — mocked). On the real DB this is two commits, which is fine.

**Step 4: Run tests to verify they pass & commit**

Run: `cd backend && uv run pytest tests/inbox/test_split_service.py -v`
Expected: PASS.

```bash
git add backend/app/inbox/split_service.py backend/tests/inbox/test_split_service.py
git commit -m "feat: add split-commit and keep-single services with provenance"
```

---

## Task 7: API endpoints (analyze / split / commit)

**Files:**
- Modify: `backend/app/api/projects.py` (add three endpoints after `get_project_evidence`, and imports)
- Test: `backend/tests/inbox/test_split_endpoints.py`

**Step 1: Write the failing tests** (mirror `test_upload.py` client fixture)

```python
def test_analyze_endpoint_requires_ownership(client, mock_session):
    other = _project(); other.owner_user_id = uuid.uuid4()
    with patch("app.api.projects.get_project", new=AsyncMock(return_value=other)):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/analyze",
            files=[("file", ("x.pdf", b"%PDF-1.4", "application/pdf"))],
        )
    assert r.status_code == 403

def test_analyze_endpoint_returns_proposal(client, mock_session):
    from app.inbox.split_service import AnalyzeResult, SheetProposal
    async def fake_analyze(*, project, filename, content):
        return AnalyzeResult(
            staging_id="s1", storage_key="k", is_drawing_set=True, confidence=0.9,
            page_count=1, scores={}, pages=[SheetProposal(1, "Site Plan", "x - 01 Site Plan.pdf", True)],
        )
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.analyze_pdf_upload", side_effect=fake_analyze),
    ):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/analyze",
            files=[("file", ("x.pdf", b"%PDF-1.4", "application/pdf"))],
        )
    assert r.status_code == 200
    assert r.json()["is_drawing_set"] is True
    assert r.json()["pages"][0]["proposed_title"] == "Site Plan"

def test_split_endpoint_returns_outcomes(client, mock_session):
    from app.inbox.service import InboxUploadOutcome
    async def fake_split(session, *, project, staging_id, source_filename):
        return [InboxUploadOutcome(
            id=uuid.uuid4(), filename="x - 01 Site Plan.pdf", workspace_path="w",
            content_hash="h", size_bytes=1, ingest_status="ingested", message="ok")]
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.split_staged_pdf", side_effect=fake_split),
    ):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/s1/split",
            json={"source_filename": "x.pdf"},
        )
    assert r.status_code == 201
    assert r.json()["files"][0]["ingest_status"] == "ingested"
```

**Step 2: Run to verify failure.**

Run: `cd backend && uv run pytest tests/inbox/test_split_endpoints.py -v`
Expected: FAIL — endpoints missing.

**Step 3: Implement endpoints** in `backend/app/api/projects.py`.

Add imports near the other inbox imports:
```python
from app.inbox.split_service import (
    analyze_pdf_upload,
    commit_staged_pdf_single,
    split_staged_pdf,
)
from app.schemas.projects import (
    PdfAnalyzeResponse,
    PdfSheetProposal,
    # ... existing imports
)
```

Add a small request schema in `schemas/projects.py`:
```python
class StagedSplitRequest(BaseModel):
    source_filename: str = Field(min_length=1, max_length=512)
```

Endpoints (place after `get_project_evidence`):
```python
@router.post("/{project_id}/inbox/analyze")
async def post_inbox_analyze(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PdfAnalyzeResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await ensure_user_exists(session, user)
    content = await file.read()
    result = await analyze_pdf_upload(
        project=project, filename=file.filename or "upload.pdf", content=content
    )
    return PdfAnalyzeResponse(
        staging_id=result.staging_id,
        is_drawing_set=result.is_drawing_set,
        confidence=result.confidence,
        page_count=result.page_count,
        scores=result.scores,
        pages=[
            PdfSheetProposal(
                index=p.index, proposed_title=p.proposed_title,
                filename=p.filename, has_text=p.has_text,
            )
            for p in result.pages
        ],
    )


@router.post("/{project_id}/inbox/{staging_id}/split", status_code=status.HTTP_201_CREATED)
async def post_inbox_split(
    project_id: uuid.UUID,
    staging_id: str,
    body: StagedSplitRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InboxUploadResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    outcomes = await split_staged_pdf(
        session, project=project, staging_id=staging_id,
        source_filename=body.source_filename,
    )
    return InboxUploadResponse(files=[
        InboxUploadResult(
            id=o.id, filename=o.filename, workspace_path=o.workspace_path,
            content_hash=o.content_hash, size_bytes=o.size_bytes,
            ingest_status=o.ingest_status, message=o.message,
        ) for o in outcomes
    ])


@router.post("/{project_id}/inbox/{staging_id}/commit", status_code=status.HTTP_201_CREATED)
async def post_inbox_commit_single(
    project_id: uuid.UUID,
    staging_id: str,
    body: StagedSplitRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InboxUploadResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    outcome = await commit_staged_pdf_single(
        session, project=project, staging_id=staging_id,
        source_filename=body.source_filename,
    )
    return InboxUploadResponse(files=[InboxUploadResult(
        id=outcome.id, filename=outcome.filename, workspace_path=outcome.workspace_path,
        content_hash=outcome.content_hash, size_bytes=outcome.size_bytes,
        ingest_status=outcome.ingest_status, message=outcome.message,
    )])
```

**Step 4: Run tests to verify they pass & run the whole inbox suite.**

Run: `cd backend && uv run pytest tests/inbox -v`
Expected: PASS (all, including prior tasks).

**Step 5: Commit**

```bash
git add backend/app/api/projects.py backend/app/schemas/projects.py backend/tests/inbox/test_split_endpoints.py
git commit -m "feat: add analyze/split/commit inbox endpoints"
```

---

## Task 8: Frontend API client methods

**Files:**
- Modify: `frontend/src/lib/api.ts` (add after `deleteProjectEvidence`)
- Modify: `frontend/src/lib/types/project.ts` (add response types)

**Step 1: Add types** to `frontend/src/lib/types/project.ts`:

```typescript
export type PdfSheetProposal = {
  index: number;
  proposed_title: string;
  filename: string;
  has_text: boolean;
};

export type PdfAnalyzeResult = {
  staging_id: string;
  is_drawing_set: boolean;
  confidence: number;
  page_count: number;
  scores: Record<string, unknown>;
  pages: PdfSheetProposal[];
};
```

**Step 2: Add API methods** to `frontend/src/lib/api.ts`. `analyze` uses multipart like `uploadInboxFiles`; split/commit use JSON `post`:

```typescript
analyzePdf: async (
  projectId: string,
  file: File,
): Promise<PdfAnalyzeResult> => {
  const formData = new FormData();
  formData.append("file", file);
  const token = await getAccessToken();
  if (!token) throw new ApiError("Not signed in.", { kind: "http", status: 401 });
  const base = env.apiBaseUrl.replace(/\/$/, "");
  return httpRequest<PdfAnalyzeResult>(
    `${base}/projects/${projectId}/inbox/analyze`,
    {
      method: "POST",
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      body: formData,
      timeoutMs: WORKFLOW_TIMEOUT_MS,
    },
  );
},

splitStagedPdf: async (
  projectId: string,
  stagingId: string,
  sourceFilename: string,
): Promise<InboxUploadResult[]> => {
  const response = await api.post<{ files: InboxUploadResult[] }>(
    `/projects/${projectId}/inbox/${stagingId}/split`,
    { source_filename: sourceFilename },
    { timeoutMs: WORKFLOW_TIMEOUT_MS },
  );
  return response.files;
},

commitStagedPdf: async (
  projectId: string,
  stagingId: string,
  sourceFilename: string,
): Promise<InboxUploadResult[]> => {
  const response = await api.post<{ files: InboxUploadResult[] }>(
    `/projects/${projectId}/inbox/${stagingId}/commit`,
    { source_filename: sourceFilename },
    { timeoutMs: WORKFLOW_TIMEOUT_MS },
  );
  return response.files;
},
```

Add `PdfAnalyzeResult` to the type import block at the top of `api.ts`.

**Step 3: Typecheck**

Run: `cd frontend && pnpm exec tsc -b --noEmit`
Expected: no new errors in `api.ts` / `project.ts`.

**Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/types/project.ts
git commit -m "feat: add PDF analyze/split API client methods"
```

---

## Task 9: Frontend confirm-preview in DocumentRepositoryPanel

Wire analyze-first behaviour for PDFs and an inline proposal card.

**Files:**
- Modify: `frontend/src/components/project/DocumentRepositoryPanel.tsx`

**Step 1: Add state and the proposal type** near the other `useState` calls:

```typescript
type SplitProposal = {
  sourceFile: File;
  analysis: PdfAnalyzeResult;
};

const [splitProposals, setSplitProposals] = useState<SplitProposal[]>([]);
const [resolvingStagingId, setResolvingStagingId] = useState<string | null>(null);
```

Import `PdfAnalyzeResult` from `@/lib/types/project`.

**Step 2: Branch PDF uploads through analyze.** In `uploadFilesBatch`, before the existing per-file loop, split `accepted` into `pdfs` (`.pdf`) and `others`. Upload `others` exactly as today. For each pdf, call `api.analyzePdf`; if `is_drawing_set`, push a proposal; otherwise add it to the normal upload list. Keep the existing progress/error handling for the non-proposal path.

```typescript
const isPdf = (f: File) => f.name.toLowerCase().endsWith(".pdf");
const pdfs = accepted.filter(isPdf);
const nonDrawingFiles: File[] = accepted.filter((f) => !isPdf(f));

for (const pdf of pdfs) {
  try {
    const analysis = await api.analyzePdf(projectId, pdf);
    if (analysis.is_drawing_set) {
      setSplitProposals((current) => [...current, { sourceFile: pdf, analysis }]);
    } else {
      nonDrawingFiles.push(pdf);
    }
  } catch (error) {
    setUploadError(`Could not analyze "${pdf.name}": ${formatUploadError(error)}`);
  }
}
// then run the existing batch-ingest loop over nonDrawingFiles instead of accepted
```

**Step 3: Add resolve handlers:**

```typescript
async function resolveSplit(proposal: SplitProposal, mode: "split" | "single") {
  setResolvingStagingId(proposal.analysis.staging_id);
  setUploadError(null);
  try {
    if (mode === "split") {
      await api.splitStagedPdf(projectId, proposal.analysis.staging_id, proposal.sourceFile.name);
    } else {
      await api.commitStagedPdf(projectId, proposal.analysis.staging_id, proposal.sourceFile.name);
    }
    setSplitProposals((current) =>
      current.filter((p) => p.analysis.staging_id !== proposal.analysis.staging_id),
    );
    await onUploadComplete();
  } catch (error) {
    setUploadError(`Could not process "${proposal.sourceFile.name}": ${formatUploadError(error)}`);
  } finally {
    setResolvingStagingId(null);
  }
}
```

**Step 4: Render proposal cards** above the table (after the `uploadError` block), one per proposal: header with filename + `page_count` + `Math.round(confidence*100)%`, a scrollable list of `pages` (`{index} {proposed_title}`), and two buttons — "Split into N documents" (calls `resolveSplit(p, "split")`) and "Keep as single PDF" (`resolveSplit(p, "single")`), both disabled while `resolvingStagingId === p.analysis.staging_id` (show a `Loader2` spinner). Match existing Tailwind classes used in the panel.

**Step 5: Typecheck**

Run: `cd frontend && pnpm exec tsc -b --noEmit`
Expected: no new errors in `DocumentRepositoryPanel.tsx`.

**Step 6: Update preview pages.** `CockpitPreviewPage.tsx` renders the panel with mock handlers — no change needed (analyze is only triggered on real drops). Verify it still typechecks.

**Step 7: Commit**

```bash
git add frontend/src/components/project/DocumentRepositoryPanel.tsx
git commit -m "feat: add drawing-set split confirm-preview to repository panel"
```

---

## Task 10: Full regression + manual verification

**Step 1: Backend** — run the whole suite:

Run: `cd backend && uv run pytest -q`
Expected: all pass (no regressions in existing inbox/evidence tests).

**Step 2: Frontend** — typecheck and build:

Run: `cd frontend && pnpm exec tsc -b --noEmit`
Expected: only the pre-existing unrelated errors (`DraftReviewPanel.tsx` null checks, `CockpitPreviewPage.tsx:229` cost-plan props) — no new errors in touched files.

**Step 3: Manual smoke (optional, needs running stack + Supabase storage).** Use superpowers:verification-before-completion. Drop `data/delivery-house/L18 CC Plans.pdf` into a project repository; confirm the proposal shows 20 sheets with sensible titles; click "Split into 20"; confirm 20 documents appear and the staging object is gone.

**Step 4: Final commit (docs/notes if any).**

```bash
git add -A
git commit -m "chore: PDF drawing-set split feature complete"
```

---

## Notes & risks for the implementer

- **Double commit in `split_staged_pdf`:** `upload_inbox_files` commits internally; the provenance pass commits again. Acceptable, but if you refactor to a single transaction, ensure provenance metadata is written before the first commit.
- **Title extraction is heuristic and builder-specific.** The `_TITLE_CANDIDATES` regex covers common residential CC-set captions; broaden it as real files reveal gaps. The positional fallback guarantees the feature never hard-fails on an unrecognised template.
- **Staging cleanup** for abandoned analyses is deferred (TTL/sweep on `_staging/`). Out of scope here.
- **`source_filename` is client-supplied** to split/commit. It only affects generated names; the staged bytes are authoritative. Sanitised downstream by `sanitize_filename`.
- **Do not** alter the existing `/inbox/upload` path or non-PDF behaviour.
- After completion, use superpowers:finishing-a-development-branch to decide merge/PR.
```
