# X1 Doctrine — Invariants

> Always in context. ~120 lines. If a packet instruction contradicts this file,
> this file wins — except where root `AGENTS.md` contradicts *both*, in which
> case `AGENTS.md` wins.

## D1 — One canonical interpretation

Each document has exactly one `document_class` + `document_subject`. Ingest,
Sort Files, invoice discovery, tender discovery and email attachments all read
the same row. No subsystem may hold a private opinion.

## D2 — Extract once

A file is downloaded and parsed **once**. Downstream consumers read persisted
extraction. `sort_service` must not re-download to sniff a preview
(it currently does — `_file_previews`, `backend/app/intake/sort_service.py:119`).

## D3 — Classification never removes evidence

Classification decides *routing and chunker choice*. It must never decide
whether text is indexed.

**"Useful text" is defined as:** `len(normalized_content.strip()) >= 200`.
Use this exact threshold everywhere. Do not invent a second definition.

```text
extract → useful text? ─ yes → persist + chunk + index
                       └ no  → register/metadata row only
```

Never `if document_class == "drawing": skip_indexing`.

## D4 — Human override outranks the machine

A user correction sets `basis="user"`, `confidence=1.0` and survives
re-ingestion, reclassification, file moves, workflow reruns, classifier
upgrades and email re-sync. Keyed by `(project_id, content_hash)`.

## D5 — Evidence and interpretation are separate layers

Never overwrite a machine-observed value with a corrected one. Keep
`machine` / `reviewed` distinct. This applies to invoices, email and
classification alike.

## D6 — Models propose, Python verifies

LLMs may classify, extract, map, summarise, draft. Deterministic Python owns:
arithmetic, validation, canonical mutation, revision handling, permissions,
MCP authorisation, project scoping.

(This restates a binding rule already in root `AGENTS.md`.)

## D7 — No autonomous sending or posting

Email sending and invoice posting require explicit user approval. Read, search,
classify, link, summarise and draft are permitted.

## D8 — Converge, do not layer

Forbidden filenames: `classifier_v2.py`, `new_classifier.py`,
`pulse_classifier.py`, `email_classifier.py`, `invoice_pipeline_v2.py`,
`document_router_v2.py`.

**Measurable gate.** Production classification/routing LOC must not materially
increase. Measure with the exact command in `stage-00-baseline.md` §Task 0.6 and
compare against the number recorded in `TRACKER.md`.

## D9 — Reconciliation with root `AGENTS.md`

The original plan proposed six feature flags and temporary compatibility shims.
Root `AGENTS.md` says *"No speculative feature flags"* and *"No backwards-compat
shims unless explicitly asked for."* Resolution:

- **No feature flags.** Stages 1–8 are narrow enough to land directly behind
  tests. Flags are re-considered only at Stage 14 (Pulse) and Stage 15 (email),
  where an external provider makes a kill-switch an operational need, and only
  with explicit sign-off recorded in `TRACKER.md`.
- **Compat reads are permitted only inside Stage 8**, must be listed in
  `TRACKER.md` § *Shims outstanding*, and must be deleted before Gate 2 closes.
  A shim with no tracker entry is a defect.

## D10 — Scope discipline for agents

One bounded behavioural change per packet.

- Bad: *"Refactor classification and Pulse."*
- Good: *"Stop `should_persist_chunks` returning False purely because
  `document_class == 'drawing'`."*

Before adding code, state what becomes redundant. Before finishing, report:
files added / changed / deleted, production LOC delta, tests added, tests run.

## D11 — The tracker is the memory

No agent may assume another agent's context. Everything the next agent needs
lives in `TRACKER.md`. Conversation history is not a handoff mechanism.

---

## Canonical vocabularies (frozen at Stage 3)

`document_class` — closed set of 11:

```text
drawing  specification  report  certificate  correspondence  contract
commercial  schedule  statutory_instrument  photo  unknown
```

`document_subject` — closed set of 16:

```text
planning heritage structural services hydraulic fire geotechnical survey
cost programme contract_admin defects sustainability access acoustic none
```

`basis` — closed set of 6, cheapest-to-most-expensive:

```text
user  structural  filename  content  model  default
```

`confidence` bands:

| Range | Meaning |
|---|---|
| 0.90–1.00 | very high |
| 0.75–0.89 | high |
| 0.65–0.74 | usable, reviewable |
| < 0.65 | needs review |

Low confidence **never** blocks ingestion or indexing (see D3).

Non-class metadata lives in `document_metadata` JSONB, not in new columns:
`subject`, `discipline`, `commercial_type`, `procurement_stage`, `confidence`,
`basis`.

`commercial_type`: `invoice quote fee_proposal tender cost_plan progress_claim variation`
`procurement_stage`: `tep eoi rft addendum submission evaluation trr`
