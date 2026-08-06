# Anchored AI Editing for Generated Drafts — Select → Instruct → Apply

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to work this plan task-by-task, and `superpowers:test-driven-development` within each task (write the failing test first).
> **Required reading first:** [pmp2/05-phase-5-interactive-pmp.md](pmp2/05-phase-5-interactive-pmp.md) (Task 5.6 is the manual ancestor of this feature; D1 and D13 are binding), [2026-07-05-pmp2-live-interactive-pmp.md](2026-07-05-pmp2-live-interactive-pmp.md) (design decisions + recorded baseline test failures), root `AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`.
> **Depends on:** nothing — all prerequisites are already shipped.
> **Requires no database migration.**

**Outcome:** A user reading a generated draft can select any text, attach a plain-English instruction, queue several such items in a tray, and apply them as one batch. A bounded LLM revises only the sections that were touched, a new draft version is published, and the blocks that actually changed are subtly highlighted until the next version.

---

## 1. Why this exists

Today there are exactly two ways to change a generated draft, and both are unusable for "tighten this paragraph":

1. **Manual section edit** — hover an `##` heading → **Edit section** → hand-type raw markdown in a `<textarea>` (`frontend/src/components/project/DraftReviewPanel.tsx:197-234`). Construction managers will not hand-edit markdown.
2. **Chat agent** — the agent's only write path is the MCP `write_workspace_file` tool (`backend/app/mcp_bridge/server.py:3356`), which reads the **whole** draft and writes the **whole** draft back. Unacceptable blast radius on a 40-page PMP, and the user must describe *where* in prose.

The missing capability is **precise targeting plus natural-language revision**.

## 2. Scope

**In scope (v1):** generated markdown drafts — PMP (`create_pmp`), consultant procurement, contractor EOI, trade procurement. These are exactly the workflow types `revise_workflow_artefact` already accepts.

**Out of scope (v1), and why:**

| Excluded | Reason |
|---|---|
| Cost plans / workbooks | `revise_workflow_artefact` (`backend/app/projects/artefact_adapters.py:51`) explicitly raises `ArtefactPolicyViolation("Cost Plans are canonical typed state; use the row, contingency, assumption, or refresh actions")`. `WorkbookGrid.tsx` is a read-only `<table>` with no cell addressing in the DOM. A workbook selection must route to the typed cost surface — a different feature. |
| Tender reports | `revise_workflow_artefact` raises `"Tender reports can only be revised by TCM"`. |
| Source-document passage harvesting (the `context` verb) | Phase 2. The tray is built with typed items so this is additive, not a rewrite. |
| Word-level diff highlighting | Block-level only in v1. |
| Persistent per-version diff history | Highlights show changes vs the immediately previous version only. |

**Do not** attempt to widen scope during implementation. If a workflow type is not accepted by `revise_workflow_artefact`, the tray affordance must not render for it.

## 3. Design contract (binding decisions)

### D1 — Never reverse-map rendered DOM text to source markdown

This is the single most important rule in this document.

Two regions of the renderer replace source text with synthesized React elements:

- `renderEvidenceCell` (`MarkdownContent.tsx:221-248`) replaces evidence-status text in table cells with `<Badge>` components.
- The `pre` component (`MarkdownContent.tsx:107-149`) replaces ` ```pmp-decision ` fences with `<DecisionControl>`.

Any approach that reads `window.getSelection().toString()` and searches for that string in the source markdown **will silently produce wrong anchors** in those regions.

**The rule:** the DOM selection identifies *which node* the user touched. Nothing more. The quoted text is then sliced out of the **source markdown** using that node's `position` offsets.

### D2 — Offsets come from `node.position`, free of charge

`react-markdown@10.1.0` hard-enables `passNode: true` (`node_modules/react-markdown/lib/index.js:355`), and `mdast-util-to-hast@13` copies `position` from the mdast node. Every custom component in `markdownComponents()` therefore **already receives** a `node` prop carrying `position.start.offset` and `position.end.offset`.

**Do not** add a rehype plugin. **Do not** add `unist-util-visit`. **Do not** add any dependency. The existing components simply destructure `{ children }` and throw `node` away; add it to the signatures you need.

### D3 — One normalization, run identically on both sides

`MarkdownContent` renders `normalizeDraftMarkdown(markdown)` (`MarkdownContent.tsx:194-205`) while `DraftReviewPanel` slices raw `content_markdown`. **These are two different offset spaces.** Anchors computed against the rendered string are meaningless against the stored string whenever the transform actually fires.

**Resolution:** port `normalizeDraftMarkdown` to Python, and have the apply endpoint normalize the stored markdown **before** verifying anchors, slicing, or publishing. The published content is the normalized content. Both sides then agree.

The two implementations must stay byte-identical. Task 3.1 adds a shared test vector to enforce this.

Note the consequence and state it in the commit message: the first applied batch writes normalized markdown back to storage. This is a fix — the `- |` line prefixes are a generation artefact — not a regression.

### D4 — Apply directly; the version ledger is the undo

Every write already goes through `artefact_revisions.publish()`, which is append-only. A bad batch is undone by re-publishing an earlier version, not by a rollback. No "propose and accept" step in v1.

### D5 — Block-level highlighting, previous-version scope, dismissible

The server computes `changed_ranges` (offsets into the **new** markdown) and stamps them into `provenance_metadata`. The client tints any block whose `[data-md-start, data-md-end)` intersects a changed range. Because the ranges live in provenance, highlights survive a page reload and are correct when a user navigates back to that version later.

### D6 — Locked decisions and headings are inviolable

Carried directly from `pmp2/05-phase-5-interactive-pmp.md`: an LLM revision pass must run the same guards as a refresh. Heading lines byte-identical, ` ```pmp-decision ` fences byte-identical, `decision_violations` clean.

### D7 — The model is never the calculator

Per `docs/architecture.md:63`. A slice revision must not introduce a numeric token that was not already present in the section or in the user's own instruction text. This is enforced by a validator, not by prompt wording alone.

---

## Implementation progress

| Task | Status |
|---|---|
| 1 — bounded slice agent | ✅ done — 15 tests green |
| 2 — normalization parity helper | ✅ done — 9 shared vectors + idempotence |
| 3 — orchestration service | ✅ done — 16 tests green |
| 4 — endpoint | ✅ done — 11 tests green |
| 5 — selection anchoring | ✅ done — 21 + 5 tests green |
| 6 — instruction card and tray | ✅ done — 23 tests green |
| 7 — wiring, apply, highlights | ✅ done — 20 panel tests green |

**Verification:** backend `709 passed, 3 deselected` across `tests/workflows tests/projects
tests/sitewise tests/grounding`, `ruff check app tests` clean. Frontend `274 passed (45 files)`,
`tsc --noEmit` clean, `pnpm lint` down to the one pre-existing error in
`tender/TenderCellDrilldown.tsx`. End-to-end walkthrough not yet run.

### Decisions taken during implementation

**I1 — Sections are level-2 only.** `split_sections` returns overlapping level-1 and
level-2 sections (an H1 section spans to the next H1, i.e. the whole PMP). Task 3 Step 3
filters to `level == 2`. An anchor before the first `##` therefore correctly yields
`"selection is outside any section"` rather than shipping the entire document to the slice
agent. This matches the slice validator's `##` contract and the frontend multi-section guard.

**I2 — `changed_ranges` is not inherited.** `artefact_revisions.revise()` copies base
`provenance_metadata` forward wholesale, so a later unrelated edit (e.g. **Edit section**)
would inherit stale `changed_ranges` and tint the wrong blocks. `revise()` now drops
`changed_ranges` and `applied_instructions` when inheriting, so only the revision that
computed them carries them. This makes D5 true on reload and on back-navigation.
Adds `backend/app/projects/artefact_revisions.py` to Task 3's file list.

**I3 — Frontend commands use `pnpm`,** per `frontend/AGENTS.md` ("Use `pnpm` only"), not the
`npm run test` written in the acceptance lines below.

**I4 — Normalization moves to every `MarkdownContent` caller,** not just `DraftReviewPanel`.
Task 7.2 deletes the internal `normalizeDraftMarkdown` call; the other four call sites
(`WorkspaceFilePanel`, `WorkspaceFolderPanel`, `WorkflowDraftPreview`, `TenderReportPanel`)
normalize at the call site so their rendering is unchanged.

**I6 — A foreign project answers 403, not 404.** Task 4.3 specifies "wrong owner → 404", but
the shared `_require_project_owner` helper (`app/api/projects.py:325`) raises 404 only for a
*missing* project and 403 for one owned by someone else. The endpoint reuses the helper
unchanged; the test asserts the real contract (403 foreign, 404 missing).

**I7 — The endpoint path has no `/api` prefix on `fastapi_app`.** Tests hit
`/projects/{id}/drafts/{id}/apply-instructions`; the `/api` prefix comes from the outer mount.

**I5 — Anchor comparison reuses `app.grounding.validator`.** Its normalizer `_normalize_text`
is private; a public `normalize_match_text` alias is added there and imported by the service,
rather than importing a private name across modules or writing a second normalizer.

**I8 — The changes toggle lives in the "What changed in v{n}" strip, not a header button row.**
Task 7.2 item 8 says to put it "next to **Edit markdown**", but commit `205d9ded` deleted the
panel's whole header button row — no Accept, Edit markdown, Refresh PMP, or Reopen buttons
remain, and `isEditing` / `editorValue` / `onRunUpdatePmp` are gone with them (see the lean
workflow panel doctrine). Recreating that row to host one toggle would undo a deliberate
decision. The toggle sits in the change strip instead, which is already about what changed,
and renders only when `changed_ranges` is non-empty. The Task 7.2 guard is correspondingly
`isAccepted` alone — there is no `isEditing` left to check.

**I9 — `Range.prototype.getBoundingClientRect` is polyfilled in `src/test/setup.ts`.** jsdom
implements `Range` without its layout methods. The card positions itself from the selection's
rect, so the resolver calls it; the polyfill returns a zero rect rather than degrading the
product code for a test environment.

**I10 — `truncateQuote` lives in `lib/instruction-tray.ts`.** Exporting it from
`SelectionInstructionCard.tsx` trips `react-refresh/only-export-components`; both components
import it from lib.

**I14 — The read transaction is released before the slice calls.** `get_db` yields one session
per request and commits it *after* the handler returns. Loading the project and draft opens a
transaction, and the slice calls take 1–3 minutes, so the connection sat idle-in-transaction
for the whole batch and Postgres (behind the Supabase pooler at
`aws-1-ap-northeast-1.pooler.supabase.com`) terminated it. The failure then surfaced on
`session.commit()` during dependency teardown — outside the endpoint's `except` chain and
outside `main.py`'s `SQLAlchemyError` handler — as a bare 500 with no `detail`, which the
client renders as "Request failed with status 500". Every other LLM-heavy workflow in this repo
runs on the workflow worker, so this endpoint was the first to hold a request-scoped
transaction across model latency. `apply_draft_instructions` now commits the (read-only,
data-free) transaction before `asyncio.gather`; `expire_on_commit=False` keeps `project` and
`draft` usable and `revise_workflow_artefact` opens a fresh transaction for the writes.

**I15 — A slice failure never sinks the batch.** An unexpected exception from one section (model
timeout, malformed structured response) used to be re-raised out of `asyncio.gather` and became
an unhandled 500. It is now reported as a `FailedInstruction` for that section's items, logged
with a traceback, and the sections that succeeded still publish. `CancelledError`,
`KeyboardInterrupt` and `SystemExit` are still re-raised.

**I16 — Changed-range offsets come from splice arithmetic, not a re-parse.** The previous code
re-ran `split_sections` on the assembled markdown and matched sections *by index*, which assumes
the revision yields an identical section count and order. One stray ` ``` ` in a revision flips
`split_sections`' fence state, swallows every later heading, and produces either mis-targeted
highlights or an `IndexError`. Offsets are now derived from the cumulative length deltas of the
applied splices.

**I13 — Apply failures render in the tray, not in `actionError`.** The panel's `actionError`
renders inside the collapsed "Workflow trace" `<details>`. A failed apply therefore ran for
30–45s (three slice attempts) and then reported nothing at all. `InstructionTray` now takes an
`error` prop and the panel keeps a separate `applyError`; the tray also runs the existing
`StreamingIndicator` while a batch is in flight so the wait is legible. The `Sparkles` icon is
gone from **Apply**. Pre-existing `actionError` placement is untouched — that is a wider
question about the collapsed trace section.

**I12 — Floating UI uses `bg-popover`, never `bg-background`.** `.dark .project-main-panel`
(and the left/side panels) deliberately set `--background: transparent` so nested in-flow
sections show the panel's own charcoal gradient. A *floating* element styled `bg-background`
therefore paints nothing and the document text reads straight through it — which is exactly
what the instruction card did on first run. `--popover` is not overridden in that block and
resolves to an opaque `oklch(0.196 0.006 86)`, which is why `ChatHistoryPopover` and
`ChatThreadActionsMenu` already use it. Both the card and the sticky tray use
`bg-popover text-popover-foreground`, pinned by a test in `InstructionTray.test.tsx` because
jsdom cannot compute the Tailwind class.

**I11 — Panel tests must clear `sessionStorage`.** The tray persists per draft+version by
design, and the shared `draft-1` v1 factory made trays leak between cases. `beforeEach` now
clears storage and the selection.

---

## Task 1: Backend — bounded slice agent

**Files:**
- Create: `backend/app/workflows/draft_instructions.py`
- Create: `backend/app/workflows/draft_instructions_instructions.md`
- Test: `backend/tests/workflows/test_draft_instructions.py`

Model this file on `backend/app/workflows/pmp_narrative.py`. That is the house pattern for a small, validated, non-doctrine LLM slice. Read it before writing anything.

### 1.1 Module skeleton

```python
"""Bounded LLM revision of a single draft section against user instructions."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.assistant.pmp_models import resolve_pmp_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.workflows.create_pmp import WorkflowValidationError

_INSTRUCTIONS_PATH = Path(__file__).with_name("draft_instructions_instructions.md")


def _load_agent_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


class SliceInstruction(BaseModel):
    quoted_text: str = Field(min_length=1, max_length=4000)
    instruction: str = Field(min_length=1, max_length=1000)


class DraftInstructionSliceOutput(BaseModel):
    revised_markdown: str = Field(min_length=1)


draft_instruction_agent = Agent(
    f"openai-responses:{settings.pmp_model}",
    output_type=DraftInstructionSliceOutput,
    instructions=_load_agent_instructions(),
    defer_model_check=True,
)
```

Note `defer_model_check=True` — required, matching every other agent in `app/workflows/`.

### 1.2 Prompt builder

Pure string assembly. **No doctrine paste, no seed paste, no retrieval.** The whole point of this module is that it is cheap and fast.

```python
def build_slice_prompt(
    *,
    section_markdown: str,
    instructions: list[SliceInstruction],
    project_title: str,
    validation_feedback: str | None = None,
) -> str:
```

Assemble, in this order:

1. `f"Project: {project_title}"`
2. `"You are revising ONE section of an existing construction project document."`
3. The section verbatim, fenced with an explicit marker:
   `"--- SECTION START ---\n{section_markdown}\n--- SECTION END ---"`
4. The instruction list, numbered, each as:
   `f'{n}. Regarding this passage:\n   """{item.quoted_text}"""\n   Requested change: {item.instruction}'`
5. The hard constraints, verbatim:
   - `"Return the COMPLETE revised section, including its ## heading line unchanged."`
   - `"Do NOT change the ## heading line in any way."`
   - `"Do NOT alter, move, or remove any ```pmp-decision fenced block. Reproduce each one byte-for-byte."`
   - `"Do NOT introduce any number, date, quantity, percentage or currency amount that does not already appear in the section above or in the requested changes. You are not the calculator."`
   - `"Do NOT add new ## headings."`
   - `"Change only what the requested changes ask for. Leave every other sentence byte-identical."`
6. If `validation_feedback`, append the standard retry block used elsewhere in the codebase:
   `"REVISION REQUIRED — your previous output failed validation:\n{validation_feedback}\nRegenerate the section fixing every issue."`

### 1.3 `draft_instructions_instructions.md`

Repo rule: prompts live in versioned files next to their agent, never as inline strings. Content: the persona ("You revise sections of Australian construction project management documents"), the output contract, and the tone rule (match the surrounding document register — formal, clause-referencing, no marketing language).

### 1.4 Validator

```python
_NUMERIC_RE = re.compile(r"\d[\d,.]*")
_DECISION_FENCE_RE = re.compile(r"```pmp-decision\n.*?\n```", re.DOTALL)


def validate_slice_output(
    original: str,
    revised: str,
    *,
    instructions: list[SliceInstruction],
) -> None:
    """Raise WorkflowValidationError if the revision broke a document contract."""
```

Collect issues into a `list[str]` and raise once at the end with `"; ".join(issues)` — the idiom used by `validate_pmp_narrative_output`.

Checks, in order:

| Check | Failure message |
|---|---|
| First line of `revised` == first line of `original` | `"heading line was modified"` |
| `revised` contains no `\n## ` beyond the first line | `"revision added a new ## heading"` |
| `_DECISION_FENCE_RE.findall(revised) == _DECISION_FENCE_RE.findall(original)` | `"pmp-decision block was altered or removed"` |
| Every numeric token in `revised` appears in `original` **or** in the joined instruction text | `f"revision introduced number {token!r} not present in the source or instructions"` |
| `len(revised) >= len(original) * 0.5` | `"revision dropped more than half the section"` |
| `len(revised) <= len(original) * 2.5` | `"revision more than doubled the section"` |

Numeric comparison must be on the **set** of matched tokens, and must strip trailing punctuation. Compare as strings, not floats.

### 1.5 Runner

```python
async def run_slice_revision(
    *,
    section_markdown: str,
    instructions: list[SliceInstruction],
    project_title: str,
    chat_model: str | None = None,
    max_attempts: int = 3,
) -> str:
    """Revise one section. Returns revised markdown. Raises WorkflowValidationError."""
```

Loop `max_attempts` times: build prompt (passing `validation_feedback` from the previous failure), call
`await run_agent_with_retry(draft_instruction_agent, prompt, model=resolved_model)` where
`resolved_model = chat_model.strip() if chat_model else resolve_pmp_model().execution_id`,
then `validate_slice_output(...)`. On success return `result.output.revised_markdown`. On the final failure, re-raise.

### 1.6 Tests — `backend/tests/workflows/test_draft_instructions.py`

Follow the house mocking convention: **patch the wrapper function, never call a live model, never use `TestModel`.**

```python
patch("app.workflows.draft_instructions.run_agent_with_retry", new=AsyncMock(return_value=...))
```

Required cases:
- `test_validator_rejects_modified_heading`
- `test_validator_rejects_new_heading`
- `test_validator_rejects_altered_decision_fence` — take a real fence from `tests/workflows/test_create_pmp.py::_valid_pmp_markdown` and mutate one character
- `test_validator_rejects_invented_number` — original has no `$450,000`, revision does, no instruction mentions it
- `test_validator_allows_number_supplied_in_instruction` — the instruction says "change the retention to 5%", output contains `5%` → passes
- `test_validator_rejects_truncated_section`
- `test_run_slice_revision_retries_on_validation_failure` — mock returns bad output then good output; assert two calls and that the second prompt contains `"REVISION REQUIRED"`
- `test_run_slice_revision_raises_after_max_attempts`

**Acceptance:** `cd backend && uv run pytest tests/workflows/test_draft_instructions.py -v` green.

---

## Task 2: Backend — normalization parity helper

**Files:**
- Modify: `backend/app/sitewise/markdown_sections.py`
- Test: `backend/tests/sitewise/test_markdown_sections.py` (extend)

Port `normalizeDraftMarkdown` from `frontend/src/components/project/MarkdownContent.tsx:194-205` exactly:

```python
def normalize_draft_markdown(markdown: str) -> str:
    """Strip the leading '- |' generation artefact. Must stay byte-identical to
    normalizeDraftMarkdown in frontend/src/components/project/MarkdownContent.tsx."""
    lines = []
    for line in markdown.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("- |"):
            lines.append(stripped[2:].lstrip())
        else:
            lines.append(line)
    return "\n".join(lines)
```

Read the TypeScript source and confirm the transform character-for-character before committing — including the `lstrip()` placements, which are `trimStart()` in the original.

Add a shared test vector so drift is caught:

- Create `backend/tests/sitewise/fixtures/normalize_vectors.json` — a list of `{"input": "...", "expected": "..."}` covering: no-op input, a single `- |` line, an indented `- |` line, a `- |` inside a fenced code block (which **is** transformed today — preserve that behaviour, do not "fix" it), and an empty string.
- Backend test loads the JSON and asserts `normalize_draft_markdown(input) == expected`.
- Task 5 adds the mirror-image frontend test reading the same file.

**Acceptance:** `cd backend && uv run pytest tests/sitewise/test_markdown_sections.py -v` green.

---

## Task 3: Backend — orchestration service

**Files:**
- Create: `backend/app/projects/draft_instructions_service.py`
- Test: `backend/tests/projects/test_draft_instructions_service.py`

### 3.1 Public entry point

```python
@dataclass(frozen=True)
class InstructionInput:
    anchor_start: int
    anchor_end: int
    quoted_text: str
    instruction: str


@dataclass(frozen=True)
class FailedInstruction:
    index: int
    reason: str


@dataclass(frozen=True)
class ApplyResult:
    revision: DraftArtifact
    applied_count: int
    failed: list[FailedInstruction]


async def apply_draft_instructions(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    expected_base_version: int,
    author_user_id: uuid.UUID,
    instructions: list[InstructionInput],
    chat_model: str | None = None,
) -> ApplyResult:
```

### 3.2 Algorithm — follow this order exactly

**Step 1 — Normalize.**
`source = normalize_draft_markdown(draft.content_markdown)`. Everything downstream operates on `source`.

**Step 2 — Verify every anchor before spending a single token.**

For each instruction, slice `source[anchor_start:anchor_end]` and compare to `quoted_text` under normalisation (lowercase, collapse whitespace). Reuse the comparison approach in `backend/app/grounding/validator.py::excerpt_matches_passage` — do not invent a new one.

Any mismatch → raise `StaleAnchorError` (define it in this module, subclassing `ValueError`). The endpoint maps it to **409**. This is what protects against a tray built against an older version. Bounds-check first: `0 <= start < end <= len(source)`.

**Step 3 — Group by section.**

```python
sections = split_sections(source)   # app.sitewise.markdown_sections
```

Use `split_sections`, **not** the frontend's h2-only splitter — it is fence-aware, frontmatter-aware, and returns a deduplicated `section_id`. **Key on `section_id`, never on heading text** (duplicate `##` headings otherwise collide).

For each instruction, find the section where `section.start <= anchor_start < section.end`. If none (the anchor is in the preamble before the first `##`), record a `FailedInstruction` with reason `"selection is outside any section"` and drop it.

**Step 4 — Revise sections concurrently.**

```python
results = await asyncio.gather(
    *(_revise_one(section, items) for section, items in grouped.items()),
    return_exceptions=True,
)
```

Sections are disjoint by construction, so wall time is the slowest slice (~10-15s) rather than the sum. This is what keeps a synchronous endpoint viable for a batch of eight. A `WorkflowValidationError` from a slice becomes a `FailedInstruction` for every instruction in that group; the section stays untouched.

If **every** group fails, raise `AllInstructionsFailedError` → the endpoint returns **422** with the reasons, and no version is published.

**Step 5 — Reassemble, highest offset first.**

```python
for section, revised in sorted(applied, key=lambda pair: pair[0].start, reverse=True):
    source = source[: section.start] + _ensure_trailing_newline(revised) + source[section.end :]
```

Descending order is mandatory — splicing low offsets first invalidates every later offset.

**Step 6 — Compute `changed_ranges`.**

Block-granularity diff using stdlib `difflib` (no new dependency — repo rule is write-it-yourself before adding a dep):

```python
def changed_block_ranges(original: str, revised: str, *, offset: int) -> list[dict[str, int]]:
    """Offsets of blocks in `revised` that differ from `original`, shifted by `offset`."""
    old_blocks = _split_blocks(original)   # [(text, start, end)] on blank-line boundaries
    new_blocks = _split_blocks(revised)
    matcher = difflib.SequenceMatcher(
        a=[b[0] for b in old_blocks], b=[b[0] for b in new_blocks]
    )
    ranges = []
    for tag, _, _, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "insert"}:
            for text, start, end in new_blocks[j1:j2]:
                ranges.append({"start": start + offset, "end": end + offset})
    return ranges
```

`_split_blocks` splits on blank lines, **except inside fenced code blocks** — track fence state exactly as `split_sections` does. Table rows are individual lines within one block; treating a whole table as one block is acceptable for v1.

`offset` is the section's start position **in the final assembled markdown**, which is not its start in the original. Compute the final offsets after Step 5 by re-running `split_sections` on the assembled result and matching by `section_id`.

**Step 7 — Publish.**

```python
revision = await revise_workflow_artefact(
    session,
    project=project,
    draft=draft,
    expected_base_version=expected_base_version,
    author_user_id=author_user_id,
    content_markdown=source,
    actor_source="agent_instruction",
)
```

This single call gives you, for free: `restamp_decisions`, workspace sync, `sync_decisions_from_markdown`, the `pg_advisory_xact_lock` on the revision stream, and the optimistic version check. **Do not** reimplement any of it. `ArtefactRevisionConflict` propagates untouched to the endpoint.

**Step 8 — Stamp provenance.**

After `revise_workflow_artefact` returns, merge into `revision.provenance_metadata` and flush:

```python
{
    "applied_instructions": [
        {"section_id": ..., "anchor": {"start": ..., "end": ...},
         "quoted_text": ..., "instruction": ...},
    ],
    "changed_ranges": [{"start": ..., "end": ...}],
    "sections_changed": [section.heading for section in applied_sections],
}
```

`sections_changed` is an **existing** key — reusing it makes the "What changed in v{n}" badge strip light up with no frontend work (`DraftReviewPanel.tsx:320-335`).

Truncate `quoted_text` to 500 chars in provenance. Note that `publish_project_event` has a payload key blocklist (`prompt`, `token`, `secret`) — the key `instruction` is safe, but do **not** rename it to anything containing `prompt`.

### 3.3 Tests — `backend/tests/projects/test_draft_instructions_service.py`

Patch `app.projects.draft_instructions_service.run_slice_revision` with an `AsyncMock`, and patch `revise_workflow_artefact` per the `tests/workflows/` convention.

Required cases:
- `test_untouched_sections_are_byte_identical` — **the core contract**, inherited from Task 5.6's acceptance test. Two-section document, instruction targets section 1, assert section 2 is byte-for-byte unchanged in the published markdown.
- `test_stale_anchor_raises_before_model_call` — assert the mock was never awaited
- `test_out_of_bounds_anchor_raises`
- `test_instructions_grouped_by_section` — three instructions across two sections → exactly two model calls
- `test_descending_splice_preserves_offsets` — two sections both revised to different lengths; assert both land correctly
- `test_duplicate_headings_are_addressed_by_section_id`
- `test_partial_failure_publishes_good_sections_and_reports_failures`
- `test_all_failures_raise_without_publishing` — assert `revise_workflow_artefact` never awaited
- `test_changed_ranges_cover_only_modified_blocks` — three paragraphs, one edited → exactly one range, and its offsets slice back to the edited paragraph
- `test_normalization_applied_before_anchor_check` — draft content contains a `- |` line; anchors computed against the normalized string verify successfully

**Acceptance:** `cd backend && uv run pytest tests/projects/test_draft_instructions_service.py -v` green.

---

## Task 4: Backend — endpoint

**Files:**
- Modify: `backend/app/schemas/projects.py`
- Modify: `backend/app/api/projects.py`
- Test: `backend/tests/test_draft_instructions_api.py`

### 4.1 Schemas

Add near `PatchDraftRequest` (`app/schemas/projects.py:634`):

```python
class DraftInstructionInput(BaseModel):
    anchor_start: int = Field(ge=0)
    anchor_end: int = Field(ge=1)
    quoted_text: str = Field(min_length=1, max_length=4000)
    instruction: str = Field(min_length=1, max_length=1000)


class ApplyDraftInstructionsRequest(BaseModel):
    expected_base_version: int = Field(ge=1)
    instructions: list[DraftInstructionInput] = Field(min_length=1, max_length=20)


class FailedInstructionResponse(BaseModel):
    index: int
    reason: str


class ApplyDraftInstructionsResponse(BaseModel):
    draft: DraftArtifactResponse
    applied_count: int
    failed: list[FailedInstructionResponse]
```

### 4.2 Endpoint

Add immediately after `patch_project_draft` (`app/api/projects.py:2314`), copying its structure exactly:

```python
@router.post("/{project_id}/drafts/{draft_id}/apply-instructions")
async def post_apply_draft_instructions(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: ApplyDraftInstructionsRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApplyDraftInstructionsResponse:
```

Body, in order:
1. `project = _require_project_owner(await get_project(session, project_id), user.id)`
2. `await require_active_entitlement(session, user)`
3. `draft = await get_draft_artifact(session, draft_id)`; 404 if `None` or `draft.project_id != project.id`
4. `try: result = await apply_draft_instructions(...)`
5. Exception mapping — **no custom response envelopes**, `HTTPException` only:

| Exception | Status |
|---|---|
| `ArtefactRevisionConflict` | 409 |
| `StaleAnchorError` | 409 |
| `AllInstructionsFailedError` | 422 |
| `ArtefactPolicyViolation` | 422 |

The 409 detail for `ArtefactRevisionConflict` must include the current version so the client can render "Draft moved to v{n}".

### 4.3 Tests — `backend/tests/test_draft_instructions_api.py`

Follow `backend/tests/test_chat_api.py:45-61` exactly: `AsyncMock` session, `app.dependency_overrides[get_db]` and `[get_current_user]`, `TestClient`, and `monkeypatch` on string paths.

Cases: happy path returns 200 with the new version; wrong owner → 404; stale anchor → 409; revision conflict → 409; all-failed → 422; 21 instructions → 422 from Pydantic; empty list → 422.

**Acceptance:** `cd backend && uv run pytest tests/test_draft_instructions_api.py -v` green, and `uv run ruff check app tests` clean.

---

## Task 5: Frontend — selection anchoring

**Files:**
- Modify: `frontend/src/components/project/MarkdownContent.tsx`
- Create: `frontend/src/lib/markdown-selection.ts`
- Test: `frontend/src/lib/markdown-selection.test.ts`
- Test: extend `frontend/src/components/project/MarkdownContent.test.tsx`

### 5.1 Stamp offsets in the renderer

In `baseComponents` and `markdownComponents`, add `node` to the destructured props and emit data attributes on **block-level** elements only: `p`, `li`, `tr`, `h2`, `h3`, `h4`, `blockquote`.

```tsx
p: ({ children, node }) => (
  <p className="my-3 leading-relaxed" {...mdPosition(node)}>{children}</p>
),
```

Helper in the same file:

```tsx
function mdPosition(node: unknown): Record<string, number> | undefined {
  const position = (node as { position?: { start?: { offset?: number };
                                           end?: { offset?: number } } })?.position;
  const start = position?.start?.offset;
  const end = position?.end?.offset;
  if (typeof start !== "number" || typeof end !== "number") return undefined;
  return { "data-md-start": start, "data-md-end": end };
}
```

Do **not** stamp `td`/`th` — `renderEvidenceCell` replaces their content, and `tr` is the correct addressable unit for a table.

### 5.2 The selection hook

```ts
export type MarkdownAnchor = {
  start: number;
  end: number;
  quotedText: string;
  rect: DOMRect;
};

export function resolveSelectionAnchor(
  selection: Selection | null,
  container: HTMLElement,
  source: string,
): MarkdownAnchor | { error: string } | null;
```

Algorithm:
1. Null/collapsed selection, or `selection.toString().trim()` empty → return `null`.
2. Both endpoints must be inside `container` (`container.contains(...)`) → else `null`.
3. Walk up from `anchorNode` and `focusNode` to the nearest ancestor with `[data-md-start]`. Either missing → `null`.
4. **Suppression:** if either endpoint is inside `[data-decision-id]` or `[data-instruction-ui]` → return `null`. Decision blocks have their own control; the tray must not annotate itself.
5. `start = min(both data-md-start)`, `end = max(both data-md-end)`.
6. **Multi-section guard:** if `source.slice(start, end)` contains `\n## ` → return `{ error: "Select text within a single section." }`.
7. `quotedText = source.slice(start, end)`.
8. `rect = selection.getRangeAt(0).getBoundingClientRect()`.

Note step 7: the quote comes from **source**, never from `selection.toString()`. This is D1 and it is the reason table badges and decision blocks stop mattering.

### 5.3 Tests — `frontend/src/lib/markdown-selection.test.ts`

Build DOM fixtures by hand (jsdom) with known `data-md-start`/`data-md-end` values and a matching source string, then construct a `Range` and call the resolver.

Required cases:
- resolves a selection inside one paragraph
- selection inside a table cell resolves to the enclosing `tr`'s range, and `quotedText` equals the **source** row text including pipes — not the rendered badge text
- selection inside `[data-decision-id]` returns `null`
- selection spanning two `##` sections returns the multi-section error
- selection spanning two paragraphs in one section returns the union range
- collapsed selection returns `null`
- selection outside the container returns `null`

Also add the normalization parity test here, reading `backend/tests/sitewise/fixtures/normalize_vectors.json` and asserting `normalizeDraftMarkdown` produces `expected` for each vector. Export `normalizeDraftMarkdown` from `MarkdownContent.tsx` (the file already has an `eslint-disable react-refresh/only-export-components` block at the bottom for exactly this — add it there).

**Acceptance:** `cd frontend && npm run test -- markdown-selection` green.

---

## Task 6: Frontend — instruction card and tray

**Files:**
- Create: `frontend/src/components/project/SelectionInstructionCard.tsx`
- Create: `frontend/src/components/project/InstructionTray.tsx`
- Create: `frontend/src/lib/instruction-tray.ts`
- Test: `frontend/src/components/project/InstructionTray.test.tsx`

### 6.1 Item type — typed for phase 2

```ts
export type InstructionItem = {
  id: string;                      // crypto.randomUUID()
  kind: "revise" | "context";      // only "revise" is produced in v1
  anchorStart: number;
  anchorEnd: number;
  quotedText: string;
  instruction: string;
  sectionHeading: string;          // display only
  error?: string;                  // set from a failed apply
};
```

The `kind` field is load-bearing for phase 2 (source-document passage harvesting). Include it now even though only one value is ever produced — adding it later means migrating persisted trays.

### 6.2 Persistence

`frontend/src/lib/instruction-tray.ts` — `loadTray(draftId, version)`, `saveTray(draftId, version, items)`, `clearTray(draftId, version)`. Key: `` `sitewise:tray:${draftId}:v${version}` `` in `sessionStorage`. Wrap every access in `try/catch` (Safari private mode throws) and fall back to in-memory state.

On load, if a tray exists for an **older** version of the same draft, surface it as a rebase prompt rather than silently discarding or silently applying it. The anchors are stale — the server will reject them — so the UI must say so first.

### 6.3 `SelectionInstructionCard`

Floating card positioned from the anchor's `rect` (fixed positioning, clamped to viewport). Contains: the quoted snippet truncated to ~180 chars in a muted blockquote, a `<textarea>` (2 rows, autofocus), and an **Add to tray** button. Enter adds, Shift+Enter newlines, Escape dismisses — matching the existing `ChatComposer` keyboard contract.

Root element must carry `data-instruction-ui` so the selection hook suppresses itself inside the card.

### 6.4 `InstructionTray`

Collapsible panel docked at the bottom of the draft article. Shows count, each item (section badge + truncated quote + instruction, with a remove button), **Clear all**, and **Apply N changes**. Items carrying `error` render in a destructive style with the reason.

Root element must carry `data-instruction-ui`. Everything must be `print:hidden` — the existing renderer already uses that convention for the version badge and the section nav.

**Acceptance:** tray persists across component remount; adding, removing and clearing work; `cd frontend && npm run test -- InstructionTray` green.

---

## Task 7: Frontend — wiring, apply, and highlights

**Files:**
- Modify: `frontend/src/components/project/DraftReviewPanel.tsx`
- Modify: `frontend/src/components/project/MarkdownContent.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types/project.ts`
- Modify: `frontend/src/index.css`
- Test: extend `frontend/src/components/project/DraftReviewPanel.test.tsx`

### 7.1 API client

```ts
applyDraftInstructions: async (
  projectId: string,
  draftId: string,
  expectedBaseVersion: number,
  instructions: DraftInstructionInput[],
): Promise<ApplyDraftInstructionsResponse> => ...
```

Mirror the shape and error handling of `patchDraft` (`lib/api.ts:732`).

### 7.2 Panel wiring

In `DraftReviewPanel`:

1. **Hoist normalization (D3).** Compute `const source = useMemo(() => normalizeDraftMarkdown(loadedDraft.content_markdown), [loadedDraft])` once, and pass `source` to `MarkdownContent`, to `splitMarkdownSections`, and as the base for `spliceMarkdownSection`. `MarkdownContent` must then **stop** normalizing internally — delete the call there and take the already-normalized string. Verify the existing section-edit tests still pass after this change.
2. Attach a `ref` to the markdown container and a `mouseup` + `selectionchange` listener that calls `resolveSelectionAnchor`.
3. On a resolved anchor, render `SelectionInstructionCard`; on an error result, render the message as a transient hint.
4. Render `InstructionTray` when items exist.
5. **Apply** → `api.applyDraftInstructions` → on success: `setLoadedDraft(response.draft)`, `onDraftUpdated(response.draft)`, `clearTray(...)` for the old version, and re-seed the tray with any `failed` items carrying their `reason`.
6. On 409: keep the tray intact and show `"Draft moved to v{n} — review the current text and re-apply."`
7. Gate the whole feature on the draft being editable: hide the affordance when `isAccepted`, when `isEditing`, and when `workflow_type` is a cost plan or tender report. Reuse the existing `isAccepted || isEditing` guard already applied to `onEditSection` (`DraftReviewPanel.tsx:419-421`).
8. Add a **Hide changes** / **Show changes** toggle in the header button row (next to **Edit markdown**), rendered only when `changed_ranges` is non-empty.

**Leave `Edit section` and `Edit markdown` exactly as they are.** They remain the escape hatch for a user who wants to type it themselves.

### 7.3 Highlights

`MarkdownContent` takes two new props: `changedRanges?: {start: number; end: number}[]` and `showChanges?: boolean`. In `mdPosition`, when `showChanges` and any range intersects `[start, end)`, also emit `data-md-changed=""`.

Intersection test: `range.start < end && range.end > start`.

CSS in `index.css`, alongside the existing `.draft-markdown [data-decision-id]` rules (~line 873):

```css
.draft-markdown [data-md-changed] {
  border-left: 2px solid var(--decision-assumed-bg);
  padding-left: 0.75rem;
  margin-left: -0.75rem;
  color: var(--decision-assumed-text);
}
@media print {
  .draft-markdown [data-md-changed] {
    border-left: none; padding-left: 0; margin-left: 0; color: inherit;
  }
}
```

Reuse the existing decision CSS custom properties rather than introducing new colours. Subtle is the requirement — a left rule plus a slightly warmer text tone, not a background fill.

### 7.4 Tests — extend `DraftReviewPanel.test.tsx`

Follow the existing pattern in that file: `vi.mock("@/lib/api", ...)`, local `draft(overrides)` factory, `render` + `screen.getByRole` + `waitFor`.

Cases:
- selecting text opens the card; typing and clicking **Add to tray** shows a 1-item tray
- **Apply** calls `api.applyDraftInstructions` with the exact anchors and the current version
- a returned draft with `changed_ranges` renders `[data-md-changed]` on the expected blocks and not on others
- the **Hide changes** toggle removes every `[data-md-changed]`
- a 409 keeps the tray populated and shows the rebase message
- returned `failed` items are re-seeded into the tray with their reason
- **regression:** the existing "edits one section and leaves the other section unchanged" test (`DraftReviewPanel.test.tsx:179`) still passes after the normalization hoist
- accepted drafts render no selection affordance

**Acceptance:** `cd frontend && npm run test` green (excluding the recorded baseline failures below).

---

## Recorded baseline test failures — do not chase

These fail before this work starts and are unrelated:
- `backend/tests/test_chat_api.py` — thread CRUD, 3 tests
- `backend/tests/inbox/test_upload.py` — `AttributeError` in `app/database/stripe_billing.py:86`
- tender worker Postgres-concurrency integration tests are flaky

## Full verification

```sh
cd backend
uv run pytest tests/workflows/test_draft_instructions.py \
              tests/projects/test_draft_instructions_service.py \
              tests/test_draft_instructions_api.py \
              tests/sitewise/test_markdown_sections.py -v
uv run pytest tests/workflows/ tests/projects/ -v      # regression
uv run ruff check app tests

cd ../frontend
npm run test
```

**End-to-end**, using the repo `verify` skill to drive the dev stack:

1. Open a project with an existing PMP draft.
2. Select a sentence mid-section → card appears → add an instruction.
3. Scroll to a different section, select a table row → add a second instruction.
4. Tray shows 2 items with correct section badges.
5. **Apply** → new version published, `sections_changed` strip lists both sections.
6. Exactly the edited blocks carry the highlight; the rest of the document is visually unchanged.
7. Every `DecisionControl` still renders and still toggles.
8. **Hide changes** clears the tint; reloading the page restores it.
9. **Edit section** still opens the textarea on the revised text.
10. Trigger **Refresh PMP from documents** while a tray is pending → apply afterwards → confirm the 409 rebase message rather than a corrupted document.

## Commit sequence

One conventional commit per task, in order:

```
feat(drafts): bounded slice agent for instruction-driven section revision
feat(drafts): normalize_draft_markdown parity helper + shared vectors
feat(drafts): orchestrate anchored instruction batches into a new revision
feat(drafts): apply-instructions endpoint
feat(drafts): markdown selection anchoring via node.position
feat(drafts): selection instruction card and tray
feat(drafts): wire anchored editing into DraftReviewPanel with change highlights
```
