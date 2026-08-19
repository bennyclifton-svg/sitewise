# Stages 9–22 — Downstream index

Wave 2 expansion (19 Aug 2026) turned Stages **9–12** into packet files.
Wave 3 expansion (19 Aug 2026, after Stage 12 `[x]`) turned Stages
**13–22** into the same format. Stage E stays a card: it is unlocked by
measurements, not by a predecessor SHA.

Product rationale: [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §§7–10.
Doctrine: [`00-doctrine.md`](./00-doctrine.md). Ledger: [`TRACKER.md`](./TRACKER.md).

**Expansion vs implementation.** Packets existing is not permission to
start. 13 may be implemented now. 14 waits on 13 `[x]`. 15–19 wait on
**Gate 3**. 20–22 wait on Stage 19 `[x]`.

| Stage | File | Expand after | Implement after |
|---|---|---|---|
| 9 | [`stage-09-consumer-behavior.md`](./stage-09-consumer-behavior.md) | Gate 2 — **expanded** | done |
| 10 | [`stage-10-invoice-foundation.md`](./stage-10-invoice-foundation.md) | Gate 2 + 9.5 — **expanded** | done |
| 11 | [`stage-11-invoice-validation.md`](./stage-11-invoice-validation.md) | Stage 10 — **expanded** | done |
| 12 | [`stage-12-invoice-workflow.md`](./stage-12-invoice-workflow.md) | Stage 11 — **expanded** | done |
| 13 | [`stage-13-project-event-spine.md`](./stage-13-project-event-spine.md) | Stage 12 — **expanded** | Stage 12 `[x]` |
| 14 | [`stage-14-pulse-mvp.md`](./stage-14-pulse-mvp.md) | Stage 13 — **expanded** | Stage 13 `[x]` |
| 15 | [`stage-15-email-foundation.md`](./stage-15-email-foundation.md) | Gate 3 — **expanded** | Gate 3 signature |
| 16 | [`stage-16-email-intake.md`](./stage-16-email-intake.md) | Gate 3 — **expanded** | Stage 15 `[x]` |
| 17 | [`stage-17-email-matching.md`](./stage-17-email-matching.md) | Gate 3 — **expanded** | Stage 16 `[x]` |
| 18 | [`stage-18-email-intelligence.md`](./stage-18-email-intelligence.md) | Gate 3 — **expanded** | Stage 17 `[x]` |
| 19 | [`stage-19-email-mcp-drafts.md`](./stage-19-email-mcp-drafts.md) | Gate 3 — **expanded** | Stage 18 `[x]` |
| 20 | [`stage-20-closed-loop-procurement.md`](./stage-20-closed-loop-procurement.md) | Stage 19 — **expanded** | Stage 19 `[x]` |
| 21 | [`stage-21-advanced-pulse.md`](./stage-21-advanced-pulse.md) | Stage 19 — **expanded** | Stage 19 `[x]` |
| 22 | [`stage-22-project-email-aliases.md`](./stage-22-project-email-aliases.md) | Stage 19 — **expanded** | Stage 19 `[x]` |
| E | card below | accuracy measurements | measurements in TRACKER |

---

## Stage 9 — Consumer behaviour — expanded

Largely absorbed into Stage 8.3 mechanically. Packets 9.1–9.8 are
*behavioural*: filters, chunking, consultant/PMP/cost discovery, transmittals.
Start at 9.0 (refresh stale `01-ground-truth.md`). Details in the stage file.

---

## Stages 10–12 — Invoice review — expanded (implemented)

Extend `backend/app/cost_plan/`. A new `invoice/` package is a D8 violation.
Do not add Azure Document Intelligence. Do not re-open 10–12 to "fix"
the historical bugs below — they were the *pre-stage* holes; TRACKER
records them as closed.

Was (Aug 2026, before 10–12): `processing_status` only `booked|needs_review|void`;
`InvoiceFieldsUpdate` overwrote machine scalars; `reconcile_totals` raised;
UI was a ledger line. Now: `machine_extraction` + `review_state` +
`decide_invoice` + three-pane review + `invoice.*` verbs.

---

## Stage 13 — Project event spine — expanded

Packets 13.1–13.7. Reuse `activity_events`; freeze `ProjectVerb`; add
idempotent `deduplication_key`. Do not touch `project_events`. Details in
the stage file.

---

## Stage 14 — Pulse MVP — expanded

Packets 14.1–14.7. Derived signals, no `pulse_*` table, no feature flag
(OD-4). UI failure mode is a vitest, not a slogan. Pulse cards **open**
existing review surfaces; they do not one-click `decide_invoice` (OD-17).
Details in the stage file.

---

## Stages 15–19 — Email — expanded

**Implement after Gate 3.** Packets:

| Stage | One-line |
|---|---|
| 15 | Raw store + FakeProvider; Graph/Gmail stubs |
| 16 | Attachments call inbox ingest — **equivalence test** |
| 17 | `match_project` + user link + threads |
| 18 | 14 message categories; `email.*` verbs; candidates do not mutate |
| 19 | MCP search/read/draft/link; send needs `actor_id` |

**The single most important rule is unchanged:**

> Email does not get its own attachment pipeline.

---

## Stages 20–22 — Closed loop — expanded

**Implement after Stage 19 `[x]`.**

| Stage | One-line |
|---|---|
| 20 | Issue procurement via approved send; link submissions; no `tender/` imports |
| 21 | `since=` + cross-domain chain cards |
| 22 | `PROJECTCODE@in.sitewise.au` inbound webhook; last |

---

## Stage E — Model fallback (not numbered; unlocked by measurement)

Not built until these are measured on real usage and recorded in
`TRACKER.md` § Accuracy measurements:

```text
unknown classification rate
user override rate, by class and by subject
deterministic filename accuracy
deterministic content accuracy
```

Stage 5 overrides are the labelled set. Fallback only where deterministic
classification demonstrably fails. Closed vocabularies + structured output.

---

## Multi-agent operating rules

**Parallelise consumers, never foundational interfaces.** Single-owner seams:

```text
ingest/types.py            shared enums            alembic migration ordering
RetrievalFilters           MCP tool registration   project-event vocabulary
workflow registration      CostInvoice.review_state
PulseSignalType            email MessageCategory   EmailProvider protocol
```

If an interface is insufficient, **file an Integration note. Do not edit the
shared contract.**

Suggested worktrees (after packets exist):

```text
worktree/retrieval        worktree/invoice-core   worktree/pulse-backend
worktree/pmp-cost         worktree/invoice-ui     worktree/pulse-ui
worktree/procurement      worktree/email-core     worktree/email-gmail
worktree/programme        worktree/email-intake   worktree/email-microsoft
```

**The highest-risk mistake is several agents refactoring classification,
inbox, evidence, workflows and MCP at the same time.** Stages 9.1, 10.1, 13
and 14.1 are sequential single-owner for that reason. Email 15 is
single-owner for the raw schema; 16's adapter is sequential after 15.
