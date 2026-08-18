# Stage 5 — User Classification Override

**Goal:** A human correction becomes permanent truth (D4), and simultaneously
becomes labelled evaluation data for §53.

**Build this before any model fallback.** Overrides are what make a model
fallback measurable later.

**Ownership:** new migration, `backend/app/projects/classification_override.py`,
`backend/app/api/projects.py` (one new endpoint), `backend/app/mcp_bridge/server.py`
(one new tool), `frontend/src/components/project/ClassificationChip.tsx`.
**Forbidden:** `ingest/types.py`, `ingest/classify.py` beyond the Stage-A hook.

**Predecessor:** Stage 3 `[x]`. Stage 4 recommended but not required.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D4
- `backend/app/database/source_document.py`
- `backend/alembic/versions/047_programme.py` (migration house style)
- `backend/app/api/projects.py` — one existing project-scoped POST, for the
  authorization pattern
- `backend/AGENTS.md` §Database Migrations

---

## Task 5.1 — Migration

`backend/alembic/versions/048_document_classification_overrides.py`.

Deliberately minimal — D8 forbids a classification-history subsystem.

```python
op.create_table(
    "document_classification_overrides",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("project_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("content_hash", sa.String(64), nullable=True),
    sa.Column("relative_path", sa.String(1024), nullable=True),
    sa.Column("key_basis", sa.String(16), nullable=False),   # 'content_hash' | 'relative_path'
    sa.Column("document_class", sa.String(64), nullable=False),
    sa.Column("document_subject", sa.String(64), nullable=True),
    sa.Column("previous_class", sa.String(64), nullable=True),
    sa.Column("reason", sa.Text(), nullable=True),
    sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True),
              server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True),
              server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    sa.CheckConstraint(
        "(key_basis = 'content_hash' AND content_hash IS NOT NULL) OR "
        "(key_basis = 'relative_path' AND relative_path IS NOT NULL)",
        name="ck_override_key_present",
    ),
)
op.create_index("uq_override_project_hash", "document_classification_overrides",
                ["project_id", "content_hash"], unique=True,
                postgresql_where=sa.text("content_hash IS NOT NULL"))
op.create_index("uq_override_project_path", "document_classification_overrides",
                ["project_id", "relative_path"], unique=True,
                postgresql_where=sa.text("content_hash IS NULL"))
```

**`key_basis` resolves OD-3.** Stage 0 query 8 told you how many rows have a null
`content_hash`. If that count is 0, still build `key_basis` — new uploads can
fail hashing.

Write a real `downgrade()`. Do not leave `pass`.

```bash
cd backend
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```

All three must succeed. That is your rollback rehearsal.

## Task 5.2 — The single service function

`backend/app/projects/classification_override.py`. **REST and MCP both call this.
Neither may reimplement it** (D8).

```python
async def set_document_classification(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    document_class: DocumentClass,
    document_subject: DocumentSubject | None,
    actor_id: uuid.UUID,
    reason: str | None = None,
) -> SourceDocument:
    """Record a human override and apply it. basis=user, confidence=1.0 (D4)."""
```

It must, in one transaction:
1. Load the document, assert `document.project_id == project_id` (**tenant guard**).
2. Upsert the override row on the correct unique index.
3. Update `source_documents.document_class`, and set
   `document_metadata.confidence = 1.0`, `document_metadata.basis = "user"`,
   `document_metadata.subject = <subject>`.
4. Trigger only dependent side effects — chunker choice, drawing-register
   membership, retrieval filters, consultant evidence status, procurement stage.
   **Do not re-OCR. Do not re-embed** unless the chunker actually changed.
5. Emit a project activity event.

## Task 5.3 — Stage A lookup

In `classify_entry`, before every other signal:

```python
override = lookup_override(project_id, content_hash, relative_path)
if override:
    return Classification(
        document_class=override.document_class,
        document_subject=override.document_subject or "none",
        ingest_mode="full_text",
        document_metadata={"basis": "user", "confidence": "1.0"},
        confidence=1.0,
        basis="user",
    )
```

`classify_entry` is currently pure and sync. Rather than making it async, pass an
already-resolved override into it. Keep the pure function pure — the caller does
the lookup.

## Task 5.4 — REST endpoint

`PUT /api/projects/{project_id}/documents/{document_id}/classification`

Copy the authorization decorator/dependency from a neighbouring project-scoped
route in `app/api/projects.py`. **Write the authorization test first:**

```python
async def test_override_rejects_cross_project_document():
    # doc belongs to project A; caller authorized for project B -> 404 (not 403)
```

404, not 403 — do not leak existence across tenants. `backend/AGENTS.md` says
project authorization is a test-first security seam.

## Task 5.5 — Survives re-ingest

```python
async def test_override_survives_reingest():
    # 1. ingest Heritage Impact Statement.pdf -> report
    # 2. override -> certificate
    # 3. re-ingest the identical file
    # 4. assert document_class == "certificate"
    #    assert metadata["basis"] == "user"
    #    assert metadata["confidence"] == "1.0"
```

## Task 5.6 — Survives a file move

```python
async def test_override_survives_file_move():
    # override, then move the file to another folder, then re-classify
    # content_hash is unchanged -> override still applies
```

If `key_basis == "relative_path"`, a move legitimately breaks the key. Assert
that case explicitly and document it as a known limitation in `TRACKER.md`.

## Task 5.7 — Frontend chip

`frontend/src/components/project/ClassificationChip.tsx` — **one** reusable
component, used by Inbox, document explorer, document preview, and later Pulse.
Four copies would be a D8 violation.

```text
Scan_20260815_001.pdf
[ Report ▾ ] [ Structural ▾ ]   ⚠ Low confidence
```

- Class and subject dropdowns are the frozen Stage 3 vocabularies.
- Show the ⚠ only when `confidence < 0.65`.
- Optimistic update, revert on error.
- Vitest render test covering: renders current class, fires the mutation,
  reverts on a rejected promise.

```bash
cd frontend && pnpm typecheck && pnpm test && pnpm lint
```

## Task 5.8 — MCP tool

Register `set_document_classification` in `backend/app/mcp_bridge/server.py`
using the existing project-scoped turn-token authority. It calls the Task 5.2
service directly.

Natural-language target: *"That heritage report is actually a planning
certificate."* → `basis=user`, `confidence=1.0`.

Test that the tool refuses a document outside the turn's project scope.

## Exit gate

- [ ] `alembic upgrade → downgrade → upgrade` all succeed
- [ ] Cross-project override returns 404
- [ ] Override survives re-ingest
- [ ] Override survives file move (or limitation documented)
- [ ] REST and MCP both call the same function (grep proves one implementation)
- [ ] Frontend: typecheck, test, lint all clean
- [ ] Null-`content_hash` path covered by a test
- [ ] No new backend failures vs. baseline
