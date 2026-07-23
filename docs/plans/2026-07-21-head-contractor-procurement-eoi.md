# Head-Contractor Procurement (EOI) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give SiteWise a correct head-contractor procurement path — starting with a client-issued **Expression of Interest (EOI)** — built on a shared procurement-request engine, and stop the chat agent from silently routing contractor requests into the consultants-only fee-proposal workflow.

**Architecture:** Extract the reusable spine of `consultant_procurement.py` (evidence retrieval, doctrine merge, versioned draft artefact, workspace sync, provenance trace) into a new engine `procurement_request.py`. Documents become pluggable via a `ProcurementDocument` abstract base class. The existing consultant path keeps **byte-identical** behaviour by delegating to the engine through a thin `ConsultantDocument` adapter. A new `ContractorEoiDocument` produces the EOI. The RFT is a later document on the same engine (out of scope here).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, pytest (backend rootdir = `backend/`); FastMCP tools; React + Vitest (frontend).

---

## How to use this plan (for the person handing off segments)

- **Segments are ordered and dependent.** Hand them off in order. Each segment states the segments it depends on.
- **Each segment is self-contained:** it repeats the context an agent needs, lists exact files, gives complete code, and ends with a **Definition of Done** the agent must prove with a command before you accept it.
- **Do-not-touch rules are load-bearing.** Segment 1 (the refactor) must not change any consultant output. The golden test in Segment 1 is the tripwire.
- **Run backend tests from `backend/`** (that is the pytest rootdir — tests import `from tests.conftest import ...`). Run frontend tests from `frontend/`.
- **Commit after each segment.** Branch names suggested per segment; open one PR per segment.

Dependency graph:

```
Segment 0 (guardrail)  ──┐
                          ├─ independent, ship first
Segment 1 (engine refactor) ── requires nothing, but do AFTER 0 to avoid conflicts
        │
        ├─ Segment 2 (EOI document + renderer)     requires 1
        │        │
        │        ├─ Segment 3 (capability + tool + worker wiring)  requires 2
        │        ├─ Segment 4 (doctrine frontmatter)               requires 2
        │        └─ Segment 5 (frontend routing)                   requires 2
        │
        └─ (later) RFT document — NOT in this plan
```

---

# Segment 0 — Guardrail: contractors must not reach the consultant workflow

**Depends on:** nothing. Ship this first; it delivers value alone.

**Why:** `normalise_discipline` currently manufactures a generic profile for *any* string, so `discipline="main_contractor"` silently produces a nonsensical consultant "Request for Fee Proposal". Close that hole for contractor/trade terms while keeping the deliberate open fallback for genuinely-unlisted *consultants*.

**Files:**
- Modify: `backend/app/workflows/consultant_procurement.py` (the `normalise_discipline` function, currently at lines 366-386)
- Modify: `backend/app/mcp_bridge/server.py` (the `start_consultant_procurement` tool, currently at lines 1347-1371)
- Modify: `backend/app/agent/workspace_instructions.py` (the consultant-procurement routing paragraph, currently at lines 83-88)
- Test: `backend/tests/workflows/test_consultant_procurement.py`

### Task 0.1 — Write the failing guard test

Add to `backend/tests/workflows/test_consultant_procurement.py`:

```python
import pytest
from app.workflows.consultant_procurement import (
    NonConsultantDiscipline,
    normalise_discipline,
)


@pytest.mark.parametrize(
    "discipline",
    [
        "main contractor",
        "main_contractor",
        "main works",
        "head contractor",
        "principal contractor",
        "builder",
        "design and construct",
        "subcontractor",
        "sub contractor",
        "trade contractor",
        "trade package",
    ],
)
def test_contractor_disciplines_are_rejected(discipline: str) -> None:
    with pytest.raises(NonConsultantDiscipline):
        normalise_discipline(discipline)


def test_unknown_consultant_still_falls_through(monkeypatch) -> None:
    # A genuinely unlisted *consultant* must still get a generic profile.
    profile = normalise_discipline("acoustic consultant")
    assert profile.name == "acoustic consultant"
    assert profile.slug == "acoustic_consultant"
```

**Step: Run it, expect failure.**
Run (from `backend/`): `pytest tests/workflows/test_consultant_procurement.py -k "contractor_disciplines or unknown_consultant" -v`
Expected: FAIL — `NonConsultantDiscipline` cannot be imported.

### Task 0.2 — Add the exception and the guard

In `backend/app/workflows/consultant_procurement.py`, **above** `def normalise_discipline`:

```python
# Post-normalisation forms (_normalise_key lowercases, strips punctuation,
# collapses whitespace, and turns "_" into " "). Substring match is intentional
# so "main works contractor" and "d and c contractor" are both caught.
_NON_CONSULTANT_TERMS = (
    "main contractor",
    "main works",
    "head contractor",
    "principal contractor",
    "builder",
    "design and construct",
    "d and c contractor",
    "subcontractor",
    "sub contractor",
    "trade contractor",
    "trade package",
)


class NonConsultantDiscipline(ValueError):
    """Raised when a procurement target is a contractor, not a consultant.

    Consultant procurement produces a client-issued Request for Fee Proposal
    (RFP). A main works / trade contractor needs a Request for Tender (RFT) or an
    Expression of Interest (EOI) — a different instrument this workflow does not
    produce.
    """

    def __init__(self, discipline: str) -> None:
        self.discipline = discipline
        super().__init__(
            f"{discipline!r} is a construction contractor, not a consultant "
            "discipline. Use the head-contractor procurement path (EOI/RFT), not "
            "consultant procurement, which only produces a request for fee proposal."
        )
```

Then edit `normalise_discipline` — insert the guard immediately after the empty-string check:

```python
def normalise_discipline(discipline: str) -> DisciplineProfile:
    cleaned = " ".join(discipline.strip().split())
    if not cleaned:
        raise ValueError("discipline is required")
    key = _normalise_key(cleaned)
    if any(term in key for term in _NON_CONSULTANT_TERMS):  # NEW
        raise NonConsultantDiscipline(cleaned)              # NEW
    aliased = DISCIPLINE_ALIASES.get(key, key)
    if aliased in DISCIPLINE_PROFILES:
        return DISCIPLINE_PROFILES[aliased]
    return _profile(
        cleaned,
        # ...unchanged fallback body...
    )
```

**Step: Run, expect pass.**
Run (from `backend/`): `pytest tests/workflows/test_consultant_procurement.py -v`
Expected: PASS (new tests pass; all pre-existing consultant tests still pass).

### Task 0.3 — Fail fast at the tool boundary (before queueing)

In `backend/app/mcp_bridge/server.py`, edit `start_consultant_procurement` so a contractor discipline is rejected **before** a run is queued, instead of failing asynchronously inside the worker. Add the import near the other consultant imports (around line 126):

```python
from app.workflows.consultant_procurement import (
    draft_consultant_procurement_artifact as run_consultant_procurement_artifact,
    normalise_discipline as _normalise_consultant_discipline,
    NonConsultantDiscipline,
)
```

Then in the tool body, validate first:

```python
@mcp.tool
async def start_consultant_procurement(
    project_id: str,
    discipline: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    max_pages: int = 1,
    instructions: str | None = None,
) -> dict:
    """Queue a durable consultant request-for-fee-proposal artefact."""
    try:
        _normalise_consultant_discipline(discipline)
    except NonConsultantDiscipline as exc:
        return {
            "kind": "blocked",
            "reason": str(exc),
            "redirect": "start_contractor_eoi",
        }
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="consultant_procurement",
        # ...unchanged...
    )
```

> Note: `start_contractor_eoi` does not exist until Segment 3. The `redirect` string is a forward reference; it is inert until then. That is intentional and safe.

### Task 0.4 — Tell the agent the rule

In `backend/app/agent/workspace_instructions.py`, in the consultant-procurement routing paragraph (lines 83-88), append one sentence:

```
Do not route a main works contractor, head contractor, builder, subcontractor,
or trade package to start_consultant_procurement — that tool is consultants only
and produces a request for fee proposal (RFP), not a tender (RFT) or EOI.
```

### Task 0.5 — Commit

```bash
git checkout -b fix/consultant-procurement-contractor-guardrail
git add backend/app/workflows/consultant_procurement.py backend/app/mcp_bridge/server.py backend/app/agent/workspace_instructions.py backend/tests/workflows/test_consultant_procurement.py
git commit -m "fix(procurement): reject contractor disciplines from consultant workflow"
```

### ✅ Definition of Done — Segment 0
- `pytest tests/workflows/test_consultant_procurement.py -v` — all PASS, run from `backend/`.
- `normalise_discipline("main contractor")` raises `NonConsultantDiscipline`; `normalise_discipline("acoustic consultant")` still returns a generic profile.
- No change to any existing consultant output string.

---

# Segment 1 — Extract the shared procurement-request engine

**Depends on:** Segment 0 (merge order, to avoid touching `consultant_procurement.py` twice in parallel).

**Why:** Both the consultant RFP and the future contractor EOI/RFT are the same *process* (client-issued request → evidence-grounded, versioned draft) over different *templates*. Extract the process once.

**The firewall rule:** the consultant path's observable output — rendered markdown, `workflow_type`, `workspace_path`, `title`, `runtime`, and `source_trace` shape — must not change by a single byte. A golden test enforces this.

**Files:**
- Create: `backend/app/workflows/procurement_request.py`
- Modify: `backend/app/workflows/consultant_procurement.py`
- Create: `backend/tests/workflows/test_consultant_procurement_golden.py`
- Fixture dir: `backend/tests/workflows/fixtures/`

### Task 1.1 — Capture the golden output BEFORE refactoring

Write `backend/tests/workflows/test_consultant_procurement_golden.py`. It renders a fixed structural-engineer RFP with fully stubbed retrieval (reuse the stubbing style already in `test_consultant_procurement.py` — `_StubRetriever`, `_install`, `_project`) and compares the rendered markdown to a committed fixture file.

```python
from pathlib import Path

# Reuse the existing helpers by importing them from the sibling test module.
from tests.workflows.test_consultant_procurement import (
    _StubRetriever,
    _install,
    _project,
    _passage,
    _cost_plan_markdown,
    _Session,
    _run,
)

FIXTURE = Path(__file__).parent / "fixtures" / "consultant_rfp_structural_v01.md"


def _deterministic_retriever() -> _StubRetriever:
    return _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="project-brief.pdf",
                    path="04-projects/walsh-renovation/00-brief/project-brief.pdf",
                    content="Owner wants a two-storey renovation.",
                )
            ],
        },
    )


def test_consultant_rfp_matches_golden(monkeypatch) -> None:
    from types import SimpleNamespace

    retriever = _deterministic_retriever()
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    result = _run(session=_Session(), discipline="structural engineer")

    if not FIXTURE.exists():  # one-time capture, then commit the fixture
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(result.draft.content_markdown, encoding="utf-8")

    assert result.draft.content_markdown == FIXTURE.read_text(encoding="utf-8")
    assert result.draft.workflow_type == "consultant_procurement_structural_engineer"
    assert result.draft.title == "Request for Fee Proposal - Structural engineer"
```

**Step: Run once to capture the fixture, then run again to confirm it is stable.**
Run (from `backend/`): `pytest tests/workflows/test_consultant_procurement_golden.py -v` (twice).
Expected: first run PASS (writes fixture), second run PASS (matches). Commit the fixture file now, before any refactor.

### Task 1.2 — Create the engine `procurement_request.py`

Create `backend/app/workflows/procurement_request.py`. It holds: the `EvidenceQuery` dataclass (move from consultant module), a `ProcurementTarget` protocol, a `ProcurementDocument` ABC, a `ProcurementRequestResult`, the orchestrator `draft_procurement_request`, and the retrieval/trace/versioning/workspace helpers **moved verbatim** from `consultant_procurement.py`.

Move these functions **unchanged** out of `consultant_procurement.py` into the engine (they contain no consultant-specific vocabulary): `_normalise_key`, `_slugify`, `_retrieve_project_evidence`, `_retrieve_platform_knowledge`, `_project_evidence_item`, `_platform_knowledge_item`, `_source_trace`, `_bullets`, `_unique_by_path`, `_unique_display_names`, `_platform_title`, `_attr`, `_compact`, `_money`, `_is_consultant_fee_proposal`→rename to `_is_received_fee_proposal`, `_document_kind`, `_reviewable_evidence`, `_extract_fee_amount`, `_information_to_review`, `_background`.

> The moved functions that are *also* consultant-specific in wording (`_background`, `_information_to_review`, `_document_kind`) are used by the consultant renderer — they can stay in the engine as shared helpers OR stay in `consultant_procurement.py`. **Decision to keep the diff small:** leave renderer-only helpers in `consultant_procurement.py`; move only the retrieval/trace/version/workspace spine. The list above is the maximal move; if unsure, move less.

The engine's core abstraction and orchestrator:

```python
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import create_draft_artifact, next_draft_version
from app.database.project import Project
from app.retrieval.retriever import DocumentRetriever


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    key: str
    label: str
    query: str


@runtime_checkable
class ProcurementTarget(Protocol):
    """What the request is for: a consultant discipline, or a works package."""

    @property
    def name(self) -> str: ...
    @property
    def slug(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ProcurementRequestResult:
    draft: DraftArtifact
    target_name: str
    source_trace: dict[str, Any]


class ProcurementDocument(ABC):
    """A pluggable client-issued procurement document (RFP, EOI, later RFT)."""

    document_key: str        # e.g. "consultant_procurement" / "contractor_eoi"
    workspace_subfolder: str # e.g. "02-consultant" / "02-procurement"
    filename_stem: str       # e.g. "consultant_procurement" / "contractor_eoi"
    knowledge_workflow: str  # doctrine catalog key
    runtime_name: str        # e.g. "clerk-consultant-procurement"

    @abstractmethod
    def resolve_target(self, raw: str) -> ProcurementTarget: ...

    @abstractmethod
    def title(self, target: ProcurementTarget) -> str: ...

    @abstractmethod
    def evidence_queries(self, target: ProcurementTarget) -> tuple[EvidenceQuery, ...]: ...

    @abstractmethod
    async def forecast(
        self, session: AsyncSession, *, project_id: uuid.UUID, target: ProcurementTarget
    ) -> dict[str, Any]: ...

    @abstractmethod
    def assumptions_and_missing(
        self,
        *,
        project: Project,
        evidence: list[dict[str, Any]],
        forecast: dict[str, Any],
        target: ProcurementTarget,
    ) -> tuple[list[str], list[str]]: ...

    @abstractmethod
    def render(
        self,
        *,
        project: Project,
        target: ProcurementTarget,
        project_evidence: list[dict[str, Any]],
        platform_knowledge: list[dict[str, Any]],
        forecast: dict[str, Any],
        assumptions: list[str],
        missing_inputs: list[str],
        max_pages: int,
        instructions: str | None,
    ) -> str: ...


def workflow_type_for(document: ProcurementDocument, target: ProcurementTarget) -> str:
    return f"{document.document_key}_{target.slug}"


def workspace_path_for(
    project: Project, document: ProcurementDocument, *, target_slug: str, version: int
) -> str:
    root = project.workspace_path.rstrip("/")
    return (
        f"{root}/{document.workspace_subfolder}/"
        f"{document.filename_stem}_{target_slug}_v{version:02d}.draft.md"
    )


async def draft_procurement_request(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    document: ProcurementDocument,
    raw_target: str,
    max_pages: int = 1,
    instructions: str | None = None,
    auto_commit: bool = True,
) -> ProcurementRequestResult:
    target = document.resolve_target(raw_target)
    pages = max(1, min(max_pages, 3))
    retriever = DocumentRetriever(session)

    project_evidence = await _retrieve_project_evidence(
        retriever, project=project, queries=document.evidence_queries(target)
    )
    platform_knowledge = await _retrieve_platform_knowledge(
        retriever, target_name=target.name, knowledge_workflow=document.knowledge_workflow
    )
    platform_knowledge = _merge_required_guidance(
        platform_knowledge, project, knowledge_workflow=document.knowledge_workflow
    )
    forecast = await document.forecast(session, project_id=project.id, target=target)
    assumptions, missing_inputs = document.assumptions_and_missing(
        project=project, evidence=project_evidence, forecast=forecast, target=target
    )
    source_trace = _source_trace(
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        forecast=forecast,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
    )
    markdown = document.render(
        project=project,
        target=target,
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        forecast=forecast,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
        max_pages=pages,
        instructions=instructions,
    )

    wf_type = workflow_type_for(document, target)
    version_hint = await next_draft_version(
        session, project_id=project.id, workflow_type=wf_type
    )
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=wf_type,
        title=document.title(target),
        workspace_path=workspace_path_for(
            project, document, target_slug=target.slug, version=version_hint
        ),
        author_user_id=user_id,
        content_markdown=markdown,
        model=None,
        runtime=document.runtime_name,
        expected_base_version=version_hint - 1,
        actor_source=f"{document.document_key}_workflow",
        provenance_metadata={
            "workflow": document.document_key,
            "target": target.name,
            "max_pages": pages,
            "instructions": instructions,
            "source_trace": source_trace,
        },
    )
    await _sync_draft_workspace(session, project=project, document=document, draft=draft, markdown=markdown)
    if auto_commit:
        await session.commit()
    return ProcurementRequestResult(draft=draft, target_name=target.name, source_trace=source_trace)
```

Also move the parameterised versions of `_retrieve_project_evidence` (now takes `queries=`), `_retrieve_platform_knowledge` (takes `target_name`, `knowledge_workflow`), `_required_guidance_paths`/`_merge_required_guidance` (take `knowledge_workflow`), and `_sync_draft_workspace` (uses `document.workspace_subfolder`/`filename_stem` instead of the consultant-hardcoded path) into the engine. Keep their bodies identical except the parameters that were previously hardcoded constants.

> **Provenance-key note:** the consultant module currently writes `provenance_metadata["discipline"]`. The engine writes `provenance_metadata["target"]`. If anything downstream reads `["discipline"]`, keep BOTH keys for the consultant document (add `"discipline": target.name` in the consultant adapter's provenance — see Task 1.3). Grep first: `grep -rn "provenance_metadata\[.discipline" backend/ ` and `grep -rn "\"discipline\"" backend/app`.

### Task 1.3 — Make `consultant_procurement.py` delegate

Rewrite the consultant module so it: keeps `DisciplineProfile`, `DISCIPLINE_PROFILES`, `DISCIPLINE_ALIASES`, `normalise_discipline` (with the Segment 0 guard), the consultant renderer helpers, and the guard — but replaces the orchestrator body with a `ConsultantDocument(ProcurementDocument)` adapter whose methods call the existing consultant helpers. `DisciplineProfile` already has `.name` and `.slug`, so it satisfies `ProcurementTarget` unchanged.

```python
from app.workflows.procurement_request import (
    EvidenceQuery,
    ProcurementDocument,
    ProcurementTarget,
    draft_procurement_request,
)

WORKFLOW_TYPE_PREFIX = "consultant_procurement"
RUNTIME_NAME = "clerk-consultant-procurement"
KNOWLEDGE_WORKFLOW = "consultant-procurement"


class ConsultantDocument(ProcurementDocument):
    document_key = WORKFLOW_TYPE_PREFIX
    workspace_subfolder = "02-consultant"
    filename_stem = "consultant_procurement"
    knowledge_workflow = KNOWLEDGE_WORKFLOW
    runtime_name = RUNTIME_NAME

    def resolve_target(self, raw: str) -> ProcurementTarget:
        return normalise_discipline(raw)   # includes the contractor guard

    def title(self, target: ProcurementTarget) -> str:
        return f"Request for Fee Proposal - {target.name}"

    def evidence_queries(self, target):        # existing _evidence_queries body
        ...
    async def forecast(self, session, *, project_id, target):  # _forecast_for_discipline + reconcile
        ...
    def assumptions_and_missing(self, *, project, evidence, forecast, target):  # _assumptions_and_missing_inputs
        ...
    def render(self, *, project, target, project_evidence, platform_knowledge,
               forecast, assumptions, missing_inputs, max_pages, instructions) -> str:
        return _render_markdown(...)   # existing consultant renderer


CONSULTANT_DOCUMENT = ConsultantDocument()


async def draft_consultant_procurement_artifact(
    session, *, project, user_id, discipline, max_pages=1, instructions=None, auto_commit=True
) -> ConsultantProcurementResult:
    result = await draft_procurement_request(
        session,
        project=project,
        user_id=user_id,
        document=CONSULTANT_DOCUMENT,
        raw_target=discipline,
        max_pages=max_pages,
        instructions=instructions,
        auto_commit=auto_commit,
    )
    return ConsultantProcurementResult(
        draft=result.draft,
        discipline=result.target_name,
        source_trace=result.source_trace,
    )
```

Keep `ConsultantProcurementResult` and the public function name/signature exactly as they are — `worker.py` and `server.py` import them and must not change in this segment.

### Task 1.4 — Prove the firewall held

Run (from `backend/`):
```
pytest tests/workflows/test_consultant_procurement.py tests/workflows/test_consultant_procurement_golden.py tests/workflows/test_consultant_procurement_evidence.py tests/mcp_bridge/test_tools_consultant_procurement.py -v
```
Expected: **all PASS with zero edits to those pre-existing test files.** If the golden test fails, the refactor changed consultant output — revert and redo until byte-identical. Then run the full backend suite: `pytest -q`.

### Task 1.5 — Commit

```bash
git checkout -b refactor/procurement-request-engine
git add backend/app/workflows/procurement_request.py backend/app/workflows/consultant_procurement.py backend/tests/workflows/test_consultant_procurement_golden.py backend/tests/workflows/fixtures/consultant_rfp_structural_v01.md
git commit -m "refactor(procurement): extract shared procurement-request engine"
```

### ✅ Definition of Done — Segment 1
- All consultant + tool tests PASS, unedited.
- Golden fixture matches byte-for-byte.
- `procurement_request.py` contains no consultant-specific vocabulary (no "discipline", "fee proposal", "02-consultant" literals).

---

# Segment 2 — The EOI document and renderer

**Depends on:** Segment 1.

**Why:** Add the contractor EOI as a second `ProcurementDocument`. It is **unpriced**, is **explicitly not an offer**, and targets a **works package**, not a discipline.

**Files:**
- Create: `backend/app/workflows/contractor_procurement.py`
- Create: `backend/tests/workflows/test_contractor_eoi.py`

### Task 2.1 — Write failing EOI tests

Create `backend/tests/workflows/test_contractor_eoi.py`. Mirror the stubbing style of `test_consultant_procurement.py` (monkeypatch the engine module's `DocumentRetriever`, `next_draft_version`, `create_draft_artifact`, and the workspace-sync helper — patch them where the engine looks them up, i.e. on `app.workflows.procurement_request`).

```python
import uuid
from types import SimpleNamespace

from app.workflows import procurement_request as engine
from app.workflows.contractor_procurement import draft_contractor_eoi_artifact
from tests.conftest import run_async

# ... reuse a stub retriever + _install-style monkeypatch targeting `engine` ...

def test_eoi_is_unpriced_and_not_an_offer(monkeypatch) -> None:
    # ...install stubs, no evidence...
    result = run_async(draft_contractor_eoi_artifact(
        _Session(), project=_project(), user_id=USER_ID, package="Main Works",
    ))
    md = result.draft.content_markdown
    assert result.draft.title == "Expression of Interest - Main Works"
    assert result.draft.workflow_type == "contractor_eoi_main_works"
    assert result.draft.workspace_path.endswith(
        "/02-procurement/contractor_eoi_main_works_v01.draft.md"
    )
    # Anti-regression of the original bug: no fee/price language leaks in.
    for banned in ("fee proposal", "lump-sum fee", "hourly rate", "disbursement"):
        assert banned.lower() not in md.lower()
    # EOI-defining content is present.
    assert "Expression of Interest" in md
    assert "not an offer" in md.lower() or "client is not bound" in md.lower()
    assert "returnable" in md.lower() or "company profile" in md.lower()


def test_eoi_never_renders_a_budget_figure(monkeypatch) -> None:
    # Even with a cost plan on file, no dollar amount appears in the client-issued EOI.
    # ...install stubs WITH a cost plan containing "$920,000"...
    result = run_async(draft_contractor_eoi_artifact(
        _Session(), project=_project(), user_id=USER_ID, package="Main Works",
    ))
    assert "$" not in result.draft.content_markdown
    assert "TBC by client" in result.draft.content_markdown
```

Run (from `backend/`): `pytest tests/workflows/test_contractor_eoi.py -v` → FAIL (module/function missing).

### Task 2.2 — Implement `contractor_procurement.py`

```python
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.workflows.procurement_request import (
    EvidenceQuery,
    ProcurementDocument,
    ProcurementRequestResult,
    ProcurementTarget,
    draft_procurement_request,
)

WORKFLOW_TYPE_PREFIX = "contractor_eoi"
RUNTIME_NAME = "clerk-contractor-eoi"
KNOWLEDGE_WORKFLOW = "head-contractor-procurement"


@dataclass(frozen=True, slots=True)
class PackageProfile:
    name: str
    slug: str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "main_works"


def normalise_package(package: str) -> PackageProfile:
    cleaned = " ".join(package.strip().split()) or "Main Works"
    return PackageProfile(name=cleaned, slug=_slugify(cleaned))


class ContractorEoiDocument(ProcurementDocument):
    document_key = WORKFLOW_TYPE_PREFIX
    workspace_subfolder = "02-procurement"
    filename_stem = "contractor_eoi"
    knowledge_workflow = KNOWLEDGE_WORKFLOW
    runtime_name = RUNTIME_NAME

    def resolve_target(self, raw: str) -> ProcurementTarget:
        return normalise_package(raw)

    def title(self, target: ProcurementTarget) -> str:
        return f"Expression of Interest - {target.name}"

    def evidence_queries(self, target: ProcurementTarget) -> tuple[EvidenceQuery, ...]:
        return (
            EvidenceQuery("project_brief", "Project brief",
                          "project brief owner objectives scope site constraints"),
            EvidenceQuery("scope_of_works", "Scope of works",
                          "scope of works design drawings specifications trade breakdown"),
            EvidenceQuery("programme", "Programme",
                          "programme milestones construction start completion sequencing"),
            EvidenceQuery("planning_pathway", "Planning pathway",
                          "planning approval DA CC construction certificate conditions of consent"),
            EvidenceQuery("procurement_strategy", "Procurement strategy",
                          "procurement strategy contract form AS 4000 head contractor tender"),
        )

    async def forecast(self, session, *, project_id, target) -> dict[str, Any]:
        # An EOI is unpriced; there is no fee to benchmark and no dollar figure is
        # ever rendered into a client-issued EOI (budget-leakage guard).
        return {"used": False, "reason": "EOI is unpriced; no fee benchmark applies."}

    def assumptions_and_missing(self, *, project, evidence, forecast, target):
        roles = {item["role"] for item in evidence}
        missing = []
        if "scope_of_works" not in roles:
            missing.append("Scope of works / current design status.")
        if "programme" not in roles:
            missing.append("Indicative construction programme and key dates.")
        missing.extend([
            "Intended contract form (e.g. AS 4000) and procurement route.",
            "Indicative value band (client to confirm; not published from the cost plan).",
            "EOI close date and time.",
            "Submission contact and lodgement method.",
        ])
        assumptions = [
            "This is a client-issued Expression of Interest to shortlist a head "
            "contractor. It is not a tender, not an offer, and respondents are not "
            "asked to price the works.",
            "The client is not bound to shortlist, issue an RFT, or proceed, and "
            "respondents bear their own EOI costs.",
        ]
        return assumptions, missing

    def render(self, *, project, target, project_evidence, platform_knowledge,
               forecast, assumptions, missing_inputs, max_pages, instructions) -> str:
        state = getattr(project, "state", None) or "TBC"
        sections = [
            f"# Expression of Interest - {target.name}",
            "",
            "## Invitation",
            f"- {project.title} invites Expressions of Interest for the {target.name} package.",
            "- This EOI is issued to shortlist capable contractors. It is not a tender or an offer.",
            "",
            "## Project overview",
            f"- Project: {project.title}",
            f"- Jurisdiction: {state}",
            "- Indicative value band: TBC by client before issue.",
            "- Intended procurement route / contract form: TBC by client before issue.",
            "- Indicative programme window: TBC by client before issue.",
            "",
            "## Scope of the works package",
            "- Describe the in-scope main works and note separate consultant and trade packages.",
            *[f"- {line}" for line in _scope_lines(project_evidence)],
            "",
            "## EOI returnables",
            "- Company profile, structure, and financial capacity (turnover, references).",
            "- Comparable project experience with referees.",
            "- Proposed key personnel and project team.",
            "- Current workload and capacity to resource this project.",
            "- High-level delivery methodology and programme approach.",
            "- Licences, insurances, and accreditations (builder's licence, safety, quality).",
            "- Declaration of any conflicts of interest.",
            "",
            "## Shortlisting basis",
            "- EOIs are assessed on capability, relevant experience, capacity, and financial standing.",
            "- Price is not sought at EOI stage; shortlisted respondents may be invited to tender (RFT).",
            "",
            "## Conditions of EOI",
            *[f"- {line}" for line in assumptions[:2]],
            "- The client may vary, suspend, or discontinue this process at any time.",
            "",
            "## Submission instructions",
            "- Submit the EOI response to the client-nominated contact in PDF format.",
            "- Close date/time and lodgement method: TBC by client before issue.",
            "",
            _basis_footer(project_evidence, platform_knowledge, missing_inputs),
        ]
        if instructions and instructions.strip():
            sections.insert(-1, f"- Additional instruction: {' '.join(instructions.split())}")
        return "\n".join(sections).rstrip() + "\n"


CONTRACTOR_EOI_DOCUMENT = ContractorEoiDocument()


@dataclass(frozen=True, slots=True)
class ContractorEoiResult:
    draft: Any
    package: str
    source_trace: dict[str, Any]


async def draft_contractor_eoi_artifact(
    session: AsyncSession, *, project: Project, user_id: uuid.UUID,
    package: str = "Main Works", max_pages: int = 1,
    instructions: str | None = None, auto_commit: bool = True,
) -> ContractorEoiResult:
    result = await draft_procurement_request(
        session, project=project, user_id=user_id,
        document=CONTRACTOR_EOI_DOCUMENT, raw_target=package,
        max_pages=max_pages, instructions=instructions, auto_commit=auto_commit,
    )
    return ContractorEoiResult(
        draft=result.draft, package=result.target_name, source_trace=result.source_trace,
    )


def _scope_lines(evidence: list[dict[str, Any]]) -> list[str]:
    seen, lines = set(), []
    for item in evidence:
        if item.get("role") != "scope_of_works":
            continue
        path = item.get("relative_path") or item.get("filename")
        if path and path not in seen:
            seen.add(path)
            lines.append(f"Refer scope evidence: {path}")
    return lines or ["Scope of works to be issued to shortlisted respondents."]


def _basis_footer(evidence, knowledge, missing_inputs) -> str:
    docs = ", ".join(sorted({
        (i.get("filename") or i.get("relative_path") or "") for i in evidence
    } - {""})) or "none found"
    guidance = ", ".join(k.get("title", "") for k in knowledge[:2] if k.get("title")) or "none found"
    missing = "; ".join(missing_inputs[:4])
    return f"Basis used: project docs: {docs}. Platform guidance: {guidance}. Missing inputs: {missing}."
```

Run (from `backend/`): `pytest tests/workflows/test_contractor_eoi.py -v` → PASS.

### Task 2.3 — Commit

```bash
git checkout -b feat/contractor-eoi-document
git add backend/app/workflows/contractor_procurement.py backend/tests/workflows/test_contractor_eoi.py
git commit -m "feat(procurement): add contractor EOI document and renderer"
```

### ✅ Definition of Done — Segment 2
- `pytest tests/workflows/test_contractor_eoi.py -v` PASS.
- No `$`, no "fee proposal", "hourly rate", or "disbursement" appears in EOI output (asserted).
- EOI lands under `02-procurement/`, titled `Expression of Interest - <package>`, workflow_type `contractor_eoi_<slug>`.

---

# Segment 3 — Capability gate, MCP tool, and worker dispatch

**Depends on:** Segment 2.

**Why:** Wire the EOI document into the durable workflow system so the agent can queue it and the worker can execute it.

**Files:**
- Modify: `backend/app/projects/workflow_capabilities.py`
- Modify: `backend/app/mcp_bridge/server.py`
- Modify: `backend/app/workflows/worker.py`
- Modify: `backend/app/agent/workspace_instructions.py`
- Test: `backend/tests/projects/test_workflow_capabilities.py`, `backend/tests/workflows/test_workflow_runs.py`

### Task 3.1 — Capability (test first)

Add to `backend/tests/projects/test_workflow_capabilities.py`:

```python
def test_contractor_eoi_supported_when_taxonomy_and_state_present() -> None:
    cap = workflow_capabilities(_snapshot()).capabilities["contractor_eoi"]
    assert cap.status == "supported"


def test_contractor_eoi_needs_state() -> None:
    cap = workflow_capabilities(_snapshot(state=None)).capabilities["contractor_eoi"]
    assert cap.status == "needs_input"
    assert "state" in cap.required_fields
```

Run → FAIL (`KeyError: 'contractor_eoi'`).

In `backend/app/projects/workflow_capabilities.py`:

```python
CONTRACTOR_EOI = "contractor_eoi"
_CONTRACTOR_FIELDS = ("building_class", "work_type", "state")
```

And inside `workflow_capabilities()`'s `capabilities` dict, add:

```python
        CONTRACTOR_EOI: _required_profile_capability(snapshot, _CONTRACTOR_FIELDS),
```

Run → PASS.

### Task 3.2 — MCP tool + capability map

In `backend/app/mcp_bridge/server.py`:

Add to `_MCP_WORKFLOW_CAPABILITIES` (lines 974-980):
```python
    "contractor_eoi": "contractor_eoi",
```

Add the tool next to `start_consultant_procurement`:
```python
@mcp.tool
async def start_contractor_eoi(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    package: str = "Main Works",
    max_pages: int = 1,
    instructions: str | None = None,
) -> dict:
    """Queue a durable client-issued head-contractor Expression of Interest (EOI).

    Use for "invite EOIs", "run an EOI", or "shortlist a main works contractor".
    The output is an unpriced, client-issued EOI — not a priced tender (RFT).
    """
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="contractor_eoi",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        parameters={
            "package": package,
            "max_pages": max_pages,
            "instructions": instructions,
        },
    )
```

### Task 3.3 — Worker dispatch

In `backend/app/workflows/worker.py`, add the import (near line 26):
```python
from app.workflows.contractor_procurement import draft_contractor_eoi_artifact
```
Add a branch in `_dispatch` (after the `consultant_procurement` branch, before the `else`):
```python
    elif run.workflow_type == "contractor_eoi":
        result = await draft_contractor_eoi_artifact(
            session,
            project=project,
            user_id=run.requested_by_user_id,
            package=str(parameters.get("package", "Main Works")),
            max_pages=int(parameters.get("max_pages", 1)),
            instructions=parameters.get("instructions"),
            auto_commit=False,
        )
```
`_json_result` already serialises any dataclass with a `draft` field, so `ContractorEoiResult` needs no special handling.

### Task 3.4 — Agent routing instructions

In `backend/app/agent/workspace_instructions.py`: (1) add `start_contractor_eoi` to the tool list (near lines 45-52), and (2) add a routing paragraph:
```
When asked to invite expressions of interest, run an EOI, or shortlist a main
works contractor, head contractor, or builder, call start_contractor_eoi with the
current snapshot and revision inputs. If the user asks specifically for a priced
tender (RFT), say the priced RFT document is not available yet and offer the EOI
(shortlisting) instead — do not present an EOI as if it were an RFT.
```

### Task 3.5 — Run integration tests

Add a `test_workflow_runs.py` case that queues `contractor_eoi` and asserts the worker produces a `contractor_eoi_main_works` draft (mirror the existing consultant run test in that file). Run (from `backend/`):
```
pytest tests/projects/test_workflow_capabilities.py tests/workflows/test_workflow_runs.py -v
pytest -q
```
Expected: PASS.

### Task 3.6 — Commit

```bash
git add backend/app/projects/workflow_capabilities.py backend/app/mcp_bridge/server.py backend/app/workflows/worker.py backend/app/agent/workspace_instructions.py backend/tests/projects/test_workflow_capabilities.py backend/tests/workflows/test_workflow_runs.py
git commit -m "feat(procurement): wire contractor EOI capability, tool, and worker"
```

### ✅ Definition of Done — Segment 3
- `get_workflow_capabilities` returns a `contractor_eoi` entry (supported with full profile, `needs_input` without `state`).
- Queuing `start_contractor_eoi` produces a durable run the worker completes into a `02-procurement/contractor_eoi_*` draft.
- Full backend suite green.

---

# Segment 4 — Head-contractor doctrine wiring

**Depends on:** Segment 2 (needs `KNOWLEDGE_WORKFLOW = "head-contractor-procurement"`).

**Why:** So the EOI cites head-contractor procurement guidance deterministically (same catalog mechanism as consultant procurement's `_required_guidance_paths`), not consultant guidance.

**Files:**
- Modify (frontmatter only): relevant seeds under `data/seed/`
- Test: `backend/tests/` (whichever module tests `select_required_paths` / the knowledge catalog — grep to find it)

### Task 4.1 — Find the exact frontmatter shape

Run: `grep -rn "required_by" data/seed | head` and open one hit (e.g. `data/seed/procurement-quoting-guide.md`) to see the exact YAML (`required_by:` mapping of `workflow: N`).

### Task 4.2 — Tag the head-contractor seeds

Add `head-contractor-procurement: <n>` under `required_by:` in the frontmatter of the seeds that govern contractor procurement — at minimum `data/seed/procurement-tendering-guide.md` and `data/seed/as-standards-reference.md`; also consider `role-builder.md` and `role-d-and-c.md`. Do **not** remove existing `consultant-procurement` keys.

### Task 4.3 — Verify resolution

Write/extend a test asserting `select_required_paths(workflow="head-contractor-procurement", ...)` returns the tagged seeds and **excludes** the doctrine core (mirror how the consultant path is verified). Run the knowledge-catalog test module + `pytest -q`.

### Task 4.4 — Commit

```bash
git add data/seed backend/tests
git commit -m "feat(knowledge): add head-contractor-procurement doctrine tags"
```

### ✅ Definition of Done — Segment 4
- `select_required_paths("head-contractor-procurement", ...)` returns the intended guidance and omits the doctrine core.
- An EOI generated for a fully-populated project shows non-empty "Platform guidance" in its basis footer (not "none found").

---

# Segment 5 — Frontend routing

**Depends on:** Segment 2 (path/prefix conventions).

**Why:** So an EOI draft opens in the procurement workspace, and the `02-procurement/contractor_eoi_*` path is recognised as a draft file.

**Files:**
- Modify: `frontend/src/components/project/workflow/workflowRouting.ts`
- Modify: `frontend/src/components/project/workflow/workspaceRouting.ts`
- Test: `frontend/src/components/project/workflow/workspaceRouting.test.ts` (and `workflowRouting.test.ts` if present)

### Task 5.1 — Route the workflow slug to the procurement tile

In `workflowRouting.ts`, add to `WORKFLOW_SLUG_TO_TILE` (line 4-19):
```ts
  contractor_eoi: "procurement",
```
(`rft` already maps to `"procurement"`.) Leave `IMPLEMENTED_TILES` unchanged unless the procurement tile is actually built — the second loop still returns `"procurement"` as a fallback.

### Task 5.2 — Recognise the EOI workspace path (test first)

Add to `workspaceRouting.test.ts` a case asserting the new matcher is true for `.../02-procurement/contractor_eoi_main_works_v01.draft.md` and false for a consultant path. Then add to `workspaceRouting.ts`:
```ts
/** True when the explorer path points at a contractor EOI draft. */
export function isContractorEoiWorkspaceFile(path: string): boolean {
  const normalised = path.replaceAll("\\", "/");
  return /\/02-procurement\/contractor_eoi_.+_v\d+\.draft\.md$/i.test(normalised);
}
```

### Task 5.3 — Run frontend tests + commit

Run (from `frontend/`): `npx vitest run src/components/project/workflow/`
Expected: PASS.
```bash
git add frontend/src/components/project/workflow/
git commit -m "feat(procurement): route contractor EOI drafts to procurement workspace"
```

### ✅ Definition of Done — Segment 5
- `npx vitest run src/components/project/workflow/` PASS.
- `isContractorEoiWorkspaceFile` recognises the EOI path; `contractor_eoi` maps to the procurement tile.

---

## Out of scope (next plan)
- **RFT document** (`ContractorRftDocument`): priced tender with scope of works, returnable schedules, contract particulars, and evaluation criteria — a second `ProcurementDocument` on the same engine once the EOI tracer is proven.
- Procurement tile UI implementation (`IMPLEMENTED_TILES`).
- EOI → RFT shortlist handoff.
