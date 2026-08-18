# Stage 7 — Automatic Filing / Sort Files Repair

**Goal:** Files file themselves as classification completes. Sort Files becomes an
idempotent recovery action that never returns an unexplained zero.

**Read this first:** the backend is already ~80% there.
[`01-ground-truth.md`](./01-ground-truth.md) §"What already exists" —
`SortOutcome`, `SortFilesCounts` and per-file reason strings all exist.
**Do not build a new outcome model.** Three real gaps:

1. `"Ingestion is still in progress"` is a *reason string*, not an outcome, so the
   UI cannot tell "waiting" from "skipped".
2. The frontend collapses all outcomes into one number.
3. `sort_service` re-downloads files for a preview (`_file_previews`) instead of
   reading persisted classification — a D2 violation, and slow.

**Ownership:** `backend/app/intake/sort_service.py`,
`backend/app/workflows/document_ingest.py`,
`frontend/src/pages/ProjectCockpitPage.tsx`,
`frontend/src/components/project/ProjectControlBoard.tsx`.
**Forbidden:** classifier logic, `filing_destination` internals.

**Predecessor:** Stage 6 `[x]`.

**Reading list:**
- [`01-ground-truth.md`](./01-ground-truth.md) §"Sort Files path"
- `backend/app/intake/sort_service.py` (lines 30–90 and 410–480)
- `backend/app/workflows/document_ingest.py:100-140`
- `backend/tests/workflows/test_sort_files.py`

---

## Task 7.1 — Split `skipped` into honest outcomes

`backend/app/intake/sort_service.py`:

```python
SortOutcome = Literal[
    "moved",
    "already-filed",
    "waiting",        # NEW — ingestion in flight, will file automatically
    "needs-review",   # NEW — classified, but confidence < 0.65
    "unresolved",     # no destination could be computed
    "skipped",        # deliberately not sorted (manifests)
    "failed",         # NEW — ingestion failed; retry required
    "refused",
]
```

Then reassign the three existing branches around line 446:

| Current | Becomes |
|---|---|
| manifest → `skipped` | `skipped` (unchanged) |
| `pending/queued/ingesting` → `skipped` | **`waiting`** |
| `failed` → `skipped` | **`failed`** |

Add matching counters to `SortFilesCounts`. Keep `skipped` in the dataclass —
removing it breaks `_build_manifest_markdown`.

**Failing test first**, `backend/tests/workflows/test_sort_files.py`:

```python
def test_files_still_ingesting_report_waiting_not_skipped() -> None:
    result = run_async(sort_inbox_files(session, project=_project()))
    record = next(r for r in result.records if r.filename == "still-ingesting.pdf")
    assert record.outcome == "waiting"
    assert result.counts.waiting == 1
    assert result.counts.skipped == 0
```

## Task 7.2 — Auto-file on classification success

In `backend/app/workflows/document_ingest.py` (already calls `sort_inbox_files`
at ~line 128): after a document reaches a classified, confident state, file *that
one document* rather than deferring to a whole-inbox sweep.

```python
if classification.confidence >= 0.65:
    await file_single_document(session, project=project, document=document)
```

Target UX:

```text
Upload → Reading… → Classifying… → Report · Structural · 92% → Filed → Design/Structural
```

The user should never need to remember a second button.

Guard against double-filing: `file_single_document` must be a no-op if the
document is no longer in `_inbox/`.

## Task 7.3 — Stop re-downloading (D2)

`sort_service.py` currently calls `_file_previews(record)` — which downloads up
to 4096 bytes per file — to feed `classify_inbox_destination`.

After Stage 6, `filing_destination` takes a `Classification`. So:

```python
classification = load_persisted_classification(session, record)   # DB read, no download
destination_folder = filing_destination(
    classification,
    workspace_path=record.workspace_path,
    filename=record.filename,
    project_workspace_path=project.workspace_path,
)
```

Then **delete `_file_previews` and `_Previews`** if nothing else uses them:

```bash
grep -rn "_file_previews\|_Previews" backend/ | grep -v __pycache__
```

Add a regression test asserting sort performs zero storage downloads:

```python
def test_sort_does_not_download_files(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("app.intake.sort_service.download_project_file",
                        lambda *a, **k: calls.append(a))
    run_async(sort_inbox_files(session, project=_project()))
    assert calls == []
```

This test is the D2 enforcement point for the whole programme. Keep it.

## Task 7.4 — Idempotent moves

```python
def test_sort_twice_is_a_no_op() -> None:
    first = run_async(sort_inbox_files(session, project=_project()))
    second = run_async(sort_inbox_files(session, project=_project()))
    assert second.counts.moved == 0
    assert second.counts.already_filed == first.counts.moved
```

## Task 7.5 — Frontend outcome breakdown

`ProjectControlBoard.tsx` / `ProjectCockpitPage.tsx`. Every file must land in
exactly one visible bucket. **Never render a bare "0 moved".**

```text
Sorted 12 files

  8  Filed
  3  Waiting for ingestion — these will file automatically
  1  Needs review — low confidence, tap to classify
```

Rules:
- If `waiting > 0` and `moved == 0`, the headline is *"3 files are still being
  processed. They will be filed automatically when classification completes."* —
  not *"0 moved"*. This single string is the fix for the plan's §3.1 complaint.
- `needs-review` rows link to the Stage 5 classification chip.
- `failed` rows offer retry.

Update the existing vitest cases in `ProjectControlBoard.test.tsx` (they pass
`sortFilesResult={null}` in ~8 places) and add one per new outcome.

```bash
cd frontend && pnpm typecheck && pnpm test && pnpm lint && pnpm build
```

## Task 7.6 — The scenario that defines success

Manual, end-to-end. Use the `verify` skill recipe
(`.claude/skills/verify`) for the dev-stack + isolated-test-user setup.

```text
1. Upload 10 documents at once.
2. Click Sort Files IMMEDIATELY, before ingestion finishes.
3. Observe: files still ingesting show "Waiting", NOT a zero result.
4. Wait for ingestion.
5. Observe: they file themselves, without pressing Sort again.
```

Record the observed output verbatim in `TRACKER.md`. A screenshot is better.

> Repo memory: server ingest runs ~20s/doc, so step 2 has a comfortable window.
> That slowness is a known separate issue — do not fix it here.

## Exit gate

- [ ] `waiting` / `needs-review` / `failed` are real outcomes, not reason strings
- [ ] No-download regression test passes
- [ ] `_file_previews` deleted (or its remaining caller justified in `TRACKER.md`)
- [ ] Sorting twice moves nothing the second time
- [ ] Frontend renders a per-outcome breakdown; no bare zero-result path exists
- [ ] Task 7.6 scenario observed and recorded
- [ ] `pnpm typecheck && pnpm test && pnpm build` clean
- [ ] No new backend failures vs. baseline
