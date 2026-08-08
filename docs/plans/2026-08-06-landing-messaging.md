# Landing page messaging — 2026-08-06

Scope: copy and terminology for `frontend/public/landing.html`. Companion to
`.impeccable/landing-surface-brief.md`, which owns the visual direction. Where the
two disagree about words, this document wins.

## The spine

> **You do the judgement. SiteWise does the assembly.**

Every section serves either the **left half** (what stays the reader's) or the
**right half** (what gets handed over). Test for any new line of copy: *which half
is this?* If neither, cut it.

Two consequences worth protecting:

- **"Editable working draft" is a promise, not a caveat.** It currently reads
  defensive — *sorry, you'll have to check it*. Under split-labour it is the
  handover completing. Same words, opposite feeling. Never apologise for it.
- **Source dots are the handover mechanism, not a trust badge.** You cannot
  exercise judgement on a line you cannot trace. That is why they are on the page.

The frame costs one thing: a division of labour is less dramatic than a
transformation. The hero graphic carries the drama; the words do not compete for it.

## Why not the alternatives

Considered and rejected, so they don't get re-litigated:

- **Transformation-led** (*From project noise to finished work*) — narrates the
  graphic. The picture already says unstructured-in / structured-out with total
  clarity; the headline saying it again wastes the viewport and reads as a
  document-processing utility.
- **Persona-led, senior** (*The senior PM that never loses the thread*) — best
  rhythm of any candidate, but the audience **is** the senior PM. It competes with
  the reader's own title and overclaims against a product that drafts rather than
  decides.
- **Pain-led** (*Stop assembling the same document by hand*) — strong hook, opens
  on a complaint.

## Hero

```
H1   You do the judgement.
     SiteWise does the assembly.

SUB  Drop in the drawings, specs, site notes and invoices as they land.
     SiteWise reads them, files them, and builds the plan, report or
     comparison you were going to write by hand — with every line still
     pointing back at the document it came from.

CTA  [ Open SiteWise ]   ·   See it working
```

- Set the two clauses as **separate lines**. The line break *is* the division of
  labour.
- Blue accent on **SiteWise** only, so the eye lands on the half being handed over.

## Terminology for the production-line graphic

Four labels, left to right. One syllable each, worksite-plain.

| Label | Detail line |
| --- | --- |
| `READ` | what's in the document |
| `SORT` | where it belongs |
| `RETRIEVE` | the right record for this job |
| `BUILD` | the artefact you asked for |

Banned words and why:

- **INGEST** — the only word on the shortlist a CM would never say, and the least
  interesting step. Nobody buys software for its uploading. Use `READ`.
- **GENERATE** — the AI word the boundary section exists to disown. Using it on the
  diagram contradicts *the model is never the source of a project fact*. Use
  `BUILD`, and let it be the only build verb.
- **CATEGORISE** — accurate but four syllables against three one-syllable
  neighbours. `SORT` holds the rhythm.

The conversational agent sits **above** the line, not in it: a single natural-language
instruction entering at the top, because that is the reader's one input. Everything
below the line is the handed-over half.

## Section copy

### Product proof — `#inside-sitewise`

> **This is the assembly.**
>
> The address is in the drawings. The scope is in the brief. The numbers are in the
> cost plan. SiteWise pulls them into one document and keeps each line tied to the
> file it came from, so you can check the ones that matter and move on.

The last clause is the real value: traceability is not for auditing everything, it
is for **spot-checking cheaply**.

Keep the three principles (Grounded / Deterministic / Editable) as built.

### Boundary — `#how-it-works`

> **Where the judgement actually happens.**
>
> Two kinds of judgement run this project. Yours, over what the document should say.
> The model's, over what a sentence means. Everything between them — finding,
> filtering, counting, checking — is ordinary software, and it runs the same way
> every time.

Both lanes stay exactly as built. The existing boundary note is already right and
does not change:

> The model is never the calculator and never the source of a project fact.

### Outputs — `#outputs`

> **You get a document, not an answer.**
>
> Six artefacts, built from the live project, ready to review and issue. Not a chat
> log you have to turn into work yourself.

The second sentence is the sharpest competitive line on the page — it names the
general-purpose chatbot without naming it. Do not soften it.

### Close

> **You've still got the last word.**
>
> Bring the documents. Say what needs doing. Review what comes out.

Three imperatives; the third is the reader's half.

## Metadata and chrome

| Element | Change |
| --- | --- |
| `<title>` | `SiteWise — you do the judgement, SiteWise does the assembly` |
| meta description | Invert. Lead with the artefact, not with "AI where judgement is needed". |
| footer tagline | `Construction work, properly grounded.` → `You keep the judgement.` |
| nav anchors | unchanged — *How it works / Inside SiteWise / What it makes* |

## Standing constraints

Carried from the surface brief, still binding:

- No invented metrics, customers, or testimonials.
- Australian spelling throughout (artefact, categorise, organise).
- `/login` for both primary actions.
- Only the six artefacts that actually exist may appear in the output register.
