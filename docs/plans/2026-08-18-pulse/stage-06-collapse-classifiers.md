# Stage 6 — Collapse the Duplicate Classifiers

**Goal:** One semantic decision engine. `app/intake/classifier.py` stops deciding
*what a document is* and becomes a pure routing function over `Classification`.

**This is the stage most likely to go wrong.** `classify_inbox_destination` holds
real institutional knowledge (`INBOX_PACKAGE_DESTINATIONS`, discipline
inference). Deleting it wholesale would lose filing accuracy that took months to
tune. **Port, then delete. Never delete first.**

**Ownership:** `backend/app/intake/classifier.py`, `backend/ingest/classify.py`.
**Forbidden:** `ingest/types.py`, `sort_service.py` behaviour (Stage 7).

**Predecessor:** Stage 4 `[x]`.

**Reading list:**
- [`01-ground-truth.md`](./01-ground-truth.md) §"The two classifiers"
- `backend/app/intake/classifier.py` (full — ~290 lines)
- `backend/ingest/classify.py` (post-Stage-4)
- `backend/tests/workflows/test_sort_files.py`

---

## Task 6.1 — Signal inventory (do this before touching code)

Produce `docs/acceptance/x1/classifier-signal-inventory.md`. One row per signal
family in `app/intake/classifier.py`:

| Signal family | Kind | Disposition |
|---|---|---|
| `INBOX_PACKAGE_DESTINATIONS` (37 entries) | **routing** — folder→folder | **Keep in filing.** Not semantic. |
| `_AUTHORITY_FILENAME_PATTERNS` | semantic | Port → `certificate` / `statutory_instrument` + `planning` |
| `_PREVIEW_AUTHORITY_PATTERNS` | semantic (content) | Port → Stage D markers |
| `_CONSULTANT_COMMERCIAL_PATTERNS` | semantic | Port → `commercial`, `commercial_type=fee_proposal` |
| `_BRIEF_FILENAME_PATTERNS` | semantic | Port → `report` + brief marker |
| `_DUE_DILIGENCE_FILENAME_PATTERNS` | semantic | Port → `report` + subject (geotech/survey/heritage) |
| `_PROGRAMME_PATTERNS` | semantic | Port → `schedule` + `programme` |
| `_PREVIEW_QUOTE_PATTERNS` | semantic (content) | Port → `commercial`, `commercial_type=quote` |
| `_FILENAME_DESTINATION_PATTERNS` | **mixed** | Split: `^S\d{3}` is discipline routing; `\b(invoice\|cost)\b` is semantic |
| `_infer_discipline_slug` | **routing** | Keep — maps discipline → folder |
| `is_intake_manifest` | routing | Keep |

**The distinction that matters:** a signal is *semantic* if it answers "what is
this document"; *routing* if it answers "given what this is, where does it live".
Routing stays. Semantic moves.

Get this table reviewed before Task 6.2. Record the reviewer in `TRACKER.md`.

## Task 6.2 — Port semantic signals into `classify.py`

For each row marked *Port*, add the pattern to the Stage 4 scoring or marker
table. Each port gets a test case in the Stage 4.3 matrix **before** the source
pattern is deleted.

Work one family per commit. Ten small commits beat one large one — if filing
accuracy drops, bisect finds the family.

## Task 6.3 — `filing_destination(Classification)`

New pure function in `backend/app/intake/classifier.py`:

```python
def filing_destination(
    classification: Classification,
    *,
    workspace_path: str,
    filename: str,
    project_workspace_path: str,
) -> str | None:
    """Route a classified document to a lifecycle folder. Makes no semantic
    judgement — it only reads the canonical Classification."""

    # 1. Explicit inbox package folder still wins (user-declared intent).
    package = inbox_package_folder(workspace_path, project_workspace_path)
    if package and (dest := INBOX_PACKAGE_DESTINATIONS.get(unquote(package).upper())):
        return dest

    # 2. Canonical class + subject.
    return _ROUTES.get((classification.document_class, classification.document_subject)) \
        or _ROUTES_BY_CLASS.get(classification.document_class)
```

The routing table:

```python
_ROUTES: dict[tuple[str, str], str] = {
    ("commercial", "cost"):          "01-cost",
    ("commercial", "contract_admin"):"01-cost/variations",
    ("report", "structural"):        "03-design/structural",
    ("report", "geotechnical"):      "03-design/01-due-diligence",
    ("report", "survey"):            "03-design/01-due-diligence",
    ("report", "heritage"):          "03-design/01-due-diligence",
    ("report", "planning"):          "04-planning-and-authorities",
    ("certificate", "planning"):     "04-planning-and-authorities",
    ("schedule", "programme"):       "06-programme",
    ("schedule", "cost"):            "01-cost",
}

_ROUTES_BY_CLASS: dict[str, str] = {
    "statutory_instrument": "04-planning-and-authorities",
    "certificate":          "04-planning-and-authorities",
    "contract":             "02-consultant",
    "correspondence":       "08-meetings-reporting",
    "photo":                "07-construction/photos",
    "drawing":              None,        # discipline decides — see below
    "specification":        None,
    "commercial":           None,
    "schedule":             None,
    "unknown":              None,
}
```

`None` means "fall through to discipline routing" — `_infer_discipline_slug`,
now fed from `classification.document_metadata["discipline"]` rather than
re-parsing the filename.

Procurement stage overrides class routing:

```python
if classification.document_metadata.get("procurement_stage"):
    return "05-procurement"
```

## Task 6.4 — Delete

Only after 6.2's tests are green. Delete from `app/intake/classifier.py` every
family marked *Port* in the inventory. `classify_inbox_destination` itself is
deleted; `sort_service.py` calls `filing_destination` instead (Stage 7 wires it —
here, just leave the old call compiling against a thin adapter and note the shim
in `TRACKER.md`).

Delete the corresponding tests in `backend/tests/` that asserted destinations via
filename regex. Replace with `filing_destination` tests.

## Task 6.5 — Routing test matrix

`backend/tests/intake/test_filing_destination.py` — every `(class, subject)` pair
that appears in `_ROUTES`, plus the procurement-stage override, plus the
inbox-package precedence, plus `unknown → None`.

Add the **precedence** test explicitly:

```python
def test_inbox_package_beats_classification():
    """A user who dropped a file in _inbox/STRUCTURAL/ meant it."""
    # classification says commercial/cost, package says STRUCTURAL
    # -> 03-design/structural
```

## Task 6.6 — LOC gate (D8)

```bash
cd "d:/AI Projects/clerk"
find backend/ingest backend/app/intake -name '*.py' \
  -not -path '*/__pycache__/*' -not -name 'test_*' \
  -exec wc -l {} + | tail -1
```

Compare with the Stage 0.6 number in `TRACKER.md`.

**Pass:** total is ≤ baseline, or exceeds it by <10% with a written justification
in `TRACKER.md`.
**Fail:** you added a parallel implementation. Find it and delete it before
marking this packet `[x]`.

## Exit gate

- [ ] Signal inventory committed and reviewed
- [ ] Every ported signal has a test that predates its deletion
- [ ] `filing_destination` is pure — takes no I/O, does no file reads
- [ ] `grep -rn "classify_inbox_destination" backend/` returns only the shim
- [ ] Routing matrix passes, including precedence test
- [ ] LOC gate result recorded in `TRACKER.md`
- [ ] `test_sort_files.py` still passes
- [ ] No new failures vs. baseline
