# Stages 9–22 — Deferred Stage Cards

> **These are deliberately not decomposed into packets yet.**
>
> Every one of them depends on an interface that does not exist. Writing
> bite-sized TDD tasks for the email provider abstraction today would produce
> confident fiction: exact file paths for files nobody has designed, test
> assertions against a schema nobody has agreed. A small model executing that
> fiction fails worse than one executing an honest stage card.
>
> **Expansion rule:** when a stage's *Expand after* condition is met, a single
> agent expands that stage into a `stage-NN-*.md` packet file using the Stage
> 0–8 format, and links it from `TRACKER.md`. Expansion is itself a packet.

Product rationale, UX mocks and worked examples for all of these live in
[`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §§16–51. Read that when you
expand a card — not before.

---

## Stage 9 — Downstream consumer migration
**Expand after:** Gate 2. **Parallelism:** high — 7 agents.

Largely absorbed into Stage 8.3. What remains after Gate 2 is *behavioural*
improvement, not mechanical migration:

| Consumer | Change |
|---|---|
| Retrieval | filter on `subject` / `discipline` / `procurement_stage`, not just class |
| Chunking | clause-aware for `specification`, row-aware for `schedule`, bounded for `drawing` |
| Drawing Register | `document_class == "drawing"` + parsed title block |
| Consultant Facts | class + subject instead of the `_CERT_HINT` regex |
| Cost Plan | `commercial` + `commercial_type` |
| PMP | class+subject routing for planning / heritage / cost / programme evidence |
| Tender Comparison | `procurement_stage == "submission"`, no filename convention |
| Transmittals | drawing class + revision metadata |

**Conflict warning:** all seven touch `document_class` readers. Each agent takes
a bounded commit and consults the 14-file list in
[`01-ground-truth.md`](./01-ground-truth.md). Two agents in `retrieval/` at once
will conflict.

---

## Stages 10–12 — Invoice review
**Expand after:** Gate 2. **Parallelism:** 2 (backend + frontend).

**Extend `backend/app/cost_plan/`.** A new `invoice/` package is a D8 violation —
`invoice_extraction.py`, `invoice_mapping.py`, `invoice_service.py`,
`invoice_candidates.py` and `evidence_reconciliation.py` already exist.

- **10 — Foundation:** immutable machine-extraction snapshot; separate reviewed
  values; field provenance; reviewer + timestamps. Keep existing cost mapping.
  **Do not add Azure Document Intelligence** — the reference repo's use of it is
  not a reason. *Exit: changing a reviewed value never changes the raw value.*
- **11 — Validation & reconciliation:** normalise existing checks into coded
  issues (`TOTAL_MISMATCH`, `UNAPPROVED_VARIATION`, …) with severity. Adapt the
  existing validators — do not write new ones. Conditional secondary extraction
  only on missing/low-confidence/failed-arithmetic. *Never a second model call
  for a clean invoice.*
- **12 — Workflow & UI:** explicit states; three-pane review; disagreement
  highlighting; Hold/Reject/Approve; approval separate from posting.
  *Exit: no invoice reaches posted state without an authorised approval.*

Frontend works against mocked fixtures until the backend contract lands.

---

## Stage 13 — Project event spine
**Expand after:** Stage 12. **Parallelism:** 1 — shared vocabulary, single owner.

Reuse the existing project activity infrastructure. Define the event vocabulary
once (`document.*`, `invoice.*`, `email.*`, `project_signal.detected`).
Project-scoped, idempotent, deduplicated.

**Do not create a second Pulse database.** Events reference canonical state; they
do not copy it.

---

## Stage 14 — Pulse MVP
**Expand after:** Stage 13. **Parallelism:** 3 (backend / frontend / signals).

Pulse answers **"What changed?"**, not "what records exist?". If the UI ever
renders `48 emails · 26 documents · 12 events` without synthesis, it has failed.

Signal detectors: drawing revision, approval received, low-confidence
classification, invoice review needed, potential cost movement. Signals reference
source evidence and **never mutate project state**.

Card actions call existing domain services. No business logic in Pulse UI.

> This is the first stage where a kill-switch flag may be justified (OD-4). It
> requires explicit sign-off against `AGENTS.md`'s no-speculative-flags rule.

---

## Stages 15–19 — Email
**Expand after:** Gate 3 (Pulse stable in production). **Parallelism:** up to 6.

Provider-neutral domain code under `backend/app/email/` with
`providers/{base,microsoft_graph,gmail}.py`. Gmail and Microsoft agents work
independently behind one interface.

**The single most important rule in the email work:**

> Email does not get its own attachment pipeline.

Attachments enter canonical intake. Manual upload and email receipt of the same
invoice must produce byte-identical downstream behaviour. That equivalence is
Stage 16's exit test and it is non-negotiable.

Raw email is immutable (D5). Derived summary/classification/signals are separate.
Email body is `document_class = correspondence`; the 14 semantic categories
(`action_required`, `decision_required`, …) are **message metadata**, never
document classes.

Sending stays user-approved (D7). MCP exposes search/read/draft/link only.
Never `send_email_unattended`, `delete_email`, `change_mailbox_rules`,
`bulk_forward`.

---

## Stages 20–22 — Closed loop
**Expand after:** Stage 19.

- **20 — Closed-loop procurement:** RFT generation → recipients → draft cover
  email → approval → issue → track → detect returns → classify as
  `procurement_stage=submission` → Tender Comparison → follow up missing bidders.
  The email domain must not duplicate procurement logic.
- **21 — Advanced Pulse:** "Since yesterday", "Catch me up on Paddington",
  cross-domain chains (email → drawing revision → programme risk).
- **22 — Project email aliases:** `PROJECTCODE@in.sitewise.au`. Only after
  provider connections are stable. Project-scoped and abuse-resistant.

---

## Stage E — Model fallback (not numbered; unlocked by measurement)

Model classification is **not built until** the following are measured over real
usage and recorded in `TRACKER.md` § Accuracy measurements:

```text
unknown classification rate
user override rate, by class and by subject
deterministic filename accuracy
deterministic content accuracy
```

User corrections from Stage 5 are the labelled evaluation set. Build the
fallback only where the deterministic classifier demonstrably fails — and send it
the closed vocabularies, filename, metadata and bounded text, with structured
output required.

---

## Multi-agent operating rules (apply to every stage above)

**Parallelise consumers, never foundational interfaces.** Single-owner seams:

```text
ingest/types.py            shared enums            alembic migration ordering
workflow registration      MCP tool registration   project-event vocabulary
```

Each agent gets: owned paths · allowed interfaces · forbidden files · required
tests · expected deletions · exit criteria.

If an interface is insufficient, **file an Integration note. Do not edit the
shared contract.**

Suggested worktrees (one per bounded ownership area):

```text
worktree/retrieval        worktree/invoice-core   worktree/pulse-backend
worktree/pmp-cost         worktree/invoice-ui     worktree/pulse-ui
worktree/procurement      worktree/email-core     worktree/email-gmail
worktree/programme        worktree/email-intake   worktree/email-microsoft
```

Concurrency: Wave 1 ≈ 4 agents · Wave 2 6–10 · Pulse/email 4–8.

**The highest-risk mistake is several agents refactoring classification, inbox,
evidence, workflows and MCP at the same time.** That is why Stages 0–8 are almost
entirely sequential and single-owner.
