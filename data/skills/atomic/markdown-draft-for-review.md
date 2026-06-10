# Skill: markdown-draft-for-review

**Job:** Wrap any markdown deliverable with the §5 frontmatter block, save it to the correct folder, and enforce the §6 folder-driven voice register match between the chosen folder and the draft's voice. Every agent-produced markdown output passes through this skill — the §5 output discipline is non-optional.

This skill ensures agent outputs land as **drafts for review** rather than as silent commits to source-of-truth records, and it ensures the draft's voice register matches the folder it lives in (so the voice register test in this slice's acceptance criteria passes downstream).

## When called

Called by:
- system skills that produce narrative deliverables (e.g. `contract-setup-system` calls this skill for the ready-to-start checklist, the contract summary, the role-specific brief);
- atomic skills that produce a narrative aside (e.g. a follow-up note alongside a register row);
- the agent directly, when the user asks for a draft, note, summary, or memo.

This skill is **not** called for register rows (those go through `register-row-draft`) or for source-of-truth records (executed contracts, certificates, signed forms — these do not pass through agent drafting and are filed directly).

## Caller passes

- **Active project folder path** — required.
- **Target folder** — the relative path within the project where the draft will be saved (e.g. `00-brief-pmp/`, `07-construction/08-rfi-notices/`, `08-meetings-reporting/`). Required.
- **Target filename** — required (the caller knows the file name; the skill does not invent one).
- **Draft content** — the markdown body. Required.
- **Caller-asserted voice register** — one of `contractual` or `stakeholder`. Required.
- **Seed list consulted** — list of seed filenames the caller loaded for this draft. Required (per §5).
- **Evidence references** — list of project file paths or document identifiers underlying the draft. Required (may be empty for genuinely novel drafts, but should not be — the §evidence-discipline expectation is that drafts are evidence-grounded).
- **Author** — defaults to `agent`. Can be overridden where a human is co-authoring.
- **Date** — defaults to today's date in ISO short form.
- **Status** — defaults to `draft`. Valid values: `draft`, `reviewed`, `superseded`.

## Pre-flight — voice / folder match check

Before writing, verify the caller-asserted voice matches the §6 default for the target folder.

The §6 folder-driven voice defaults are:

| Folder pattern | Default voice |
|---|---|
| `01-cost/cost-plan*`, `01-cost/cost-report*`, `01-cost/*claim-assessment*`, `01-cost/*variation-pricing*` | contractual |
| `02-consultant/**` | contractual |
| `03-design/**` | contractual |
| `06-programme/**` | contractual |
| `04-planning-and-authorities/**` | contractual |
| `05-procurement/01-eoi/**`, `05-procurement/02-tender-pack/**`, `05-procurement/03-rfi-addendum/**`, `05-procurement/04-submissions/**` | contractual |
| `05-procurement/05-evaluation/evaluation-matrix*`, `05-procurement/05-evaluation/*tender*`, `05-procurement/05-evaluation/price_evaluation*`, `05-procurement/05-evaluation/non_price_evaluation*` | contractual |
| `05-procurement/05-evaluation/*comparison*`, `05-procurement/05-evaluation/*subcontractor*`, `05-procurement/05-evaluation/*trade*`, `05-procurement/05-evaluation/*subbie*` | stakeholder (builder-internal informal quote comparison) |
| `05-procurement/06-recommendation/recommendation-to-owner*`, `05-procurement/06-recommendation/owner-*`, `05-procurement/06-recommendation/*owner*` | stakeholder (owner-facing recommendation summary) |
| `05-procurement/06-recommendation/tender_recommendation*`, `05-procurement/06-recommendation/recommendation-report*` | contractual (formal recommendation report) |
| `05-procurement/**` (any other path) | contractual (default for procurement folder) |
| `07-construction/02-fioa-contract/**` | contractual (and typically source-of-truth, not agent-drafted — flag if agent is drafting here) |
| `07-construction/05-progress-claims/**` | contractual |
| `07-construction/06-variations/**` | contractual |
| `07-construction/07-programme-eot/**` | contractual |
| `07-construction/08-rfi-notices/**` | contractual |
| `07-construction/09-cc-pc-oc/**` | contractual (mostly source-of-truth) |
| `07-construction/12-reports/site-inspection*` | contractual |
| `08-meetings-reporting/owner-update*` | stakeholder |
| `08-meetings-reporting/owner-programme*`, `08-meetings-reporting/owner-risk*`, `08-meetings-reporting/*owner*programme*`, `08-meetings-reporting/*owner*risk*` | stakeholder |
| `08-meetings-reporting/*monthly*owner*` | stakeholder |
| `08-meetings-reporting/park-for-decision*`, `08-meetings-reporting/*park*decision*` | stakeholder (owner-builder self-decision queue; still a dated register record) |
| `09-handover-dlp/owner*`, `09-handover-dlp/handover-letter*` | stakeholder |
| `09-handover-dlp/PC*checklist*` | stakeholder (owner-readable) but contractual evidence references |
| `00-brief-pmp/owner*`, `00-brief-pmp/client*` | stakeholder |
| `08-meetings-reporting/minutes*`, `08-meetings-reporting/action-register*`, `08-meetings-reporting/decision-register*` | contractual (factual, dated record) — but a meeting *agenda* sent externally may be stakeholder; judge by audience |

For folders not in the table, the default is contractual (formal Australian English).

**If the caller-asserted voice does not match the folder default:**
- If the role overlay specifies otherwise (e.g. an owner-builder writing for themselves), the role overlay wins — proceed with caller's choice.
- If the role overlay does not specify otherwise, the skill **flags the mismatch** and asks the caller to either change the folder or change the voice. The skill does not silently accept a mismatch — the voice register test depends on the match holding.

**If the target folder is `07-construction/02-fioa-contract/` or `07-construction/09-cc-pc-oc/`:**
- These folders are source-of-truth document repositories (executed contracts, CC certificates, PC certificates, OC certificates). Agent drafts here are unusual. The skill flags and asks for confirmation — typically the right destination is `00-brief-pmp/contract-summary.md` (for a contract summary) or a sibling note in the meeting / report folder rather than the source-of-truth folder.

## Steps

### Step 1 — Run pre-flight

Voice / folder match per the table above. Source-of-truth folder check. If gaps, return the gap report and do not write.

### Step 2 — Construct frontmatter

Generate the §5 frontmatter block:

```yaml
---
status: <status, default draft>
author: <author, default agent>
date: <date, default today ISO>
seed_consulted: [<seed1>, <seed2>, ...]
evidence_refs: [<ref1>, <ref2>, ...]
voice_register: <contractual | stakeholder>
folder: <target folder>
---
```

The `voice_register:` and `folder:` fields are this skill's additions beyond the doctrine's §5 minimum. They make the voice-register test instrumented — a future quality check can read the frontmatter and verify the match.

If `seed_consulted:` is empty and the target folder is one of the phase-gate folders (`01-cost/`, `04-planning-and-authorities/`, `05-procurement/`, `07-construction/05-progress-claims/`, `06-variations/`, `07-programme-eot/`), the skill **flags the gap**. An empty `seed_consulted:` on a phase-gate deliverable is a §seed-consultation-discipline failure (per `../../00-doctrine/doctrine.md`).

### Step 3 — Validate the draft body against the asserted voice

Quick sanity-check pass on the draft body against the asserted voice. This is heuristic, not enforcement:

- **Contractual register signals** — formal Australian English, clause numbers cited verbatim, ISO short-form dates (YYYY-MM-DD) in registers and long form ("27 May 2026") in correspondence, AUD with `$` symbol, no contractions, active voice, short sentences. Sentences typically reference contractual mechanisms.
- **Stakeholder register signals** — plain English, leads with "what this means for you" / "what we need from you" (where applicable, per §owner-communication), technical terms explained inline once, no clause numbers in the body (clauses go below a fold or in attachments), recommendation present where options exist.

Signals that contradict the asserted voice are flagged as warnings, not blockers. The author is responsible for the body content; this skill enforces the wrapper and the folder match, not the prose.

### Step 4 — Concatenate frontmatter + body

Frontmatter block on top, blank line, then the draft body. Standard markdown.

### Step 5 — Write to the target folder + filename

If the target folder does not exist within the active project, the skill flags before creating — folder creation in the active project is typically intentional but worth surfacing in case the caller meant a different existing folder.

If the target filename already exists:
- **Default behaviour:** save as a new file with a suffix (e.g. `ready-to-start-v2.md`) and flag to the caller.
- If the caller explicitly passed an `overwrite_with_supersede` flag, mark the existing file with `status: superseded` (update its frontmatter) and write the new file with a link back to the superseded version. The superseded file is **not deleted** — the §decision-discipline append-only rule extends to drafts that have become Decisions in practice.
- If the caller explicitly passed an `overwrite_in_place` flag, overwrite. This flag is reserved for rapid iteration before any review has occurred — never use after `status: reviewed` has been applied.

### Step 6 — Return the result

Return:
- the path written;
- the frontmatter block;
- any flags or warnings raised (voice / folder mismatch, source-of-truth folder, missing seeds, etc.);
- a one-line summary suitable for a register row, decision log entry, or commit message.

## Rule

This skill produces **drafts**, not committed records. Every output carries `status: draft` until a human reviewer explicitly changes it to `status: reviewed`. The agent does not flip its own draft to reviewed.

This skill enforces the §5 frontmatter wrapper and the §6 voice / folder match. **It does not author content** — the body is what the caller passes in. The skill is the discipline check on the wrapper, not the writing.

This skill respects the AGENTS.md §11 active-project boundary — writes only inside the active project folder.

This skill does not handle Excel destinations. For Excel outputs, the caller routes to `excel-safe-edit` (which must be preceded by an approved markdown produced by this skill) and `excel-verify`. This skill is markdown-only.

## See also

- `../../AGENTS.md §5` — output discipline (the frontmatter block this skill enforces)
- `../../AGENTS.md §6` — voice register (the folder mapping this skill enforces)
- `../../AGENTS.md §11` — active-project boundary
- `../../00-doctrine/doctrine.md §voice-and-style` — two-register split rationale
- `../../00-doctrine/doctrine.md §evidence-discipline` — Fact / Assumption / Judgement / Recommendation labelling expected in the body
- `../../00-doctrine/doctrine.md §seed-consultation-discipline` — why `seed_consulted:` is non-optional on phase-gate deliverables
- `../../00-doctrine/doctrine.md §owner-communication` — the stakeholder-register format this skill expects in owner-facing drafts
- `seed-targeted-read.md` — typically called before this skill, produces the seed list this skill records
- `evidence-sweep.md` — typically called before this skill, produces the evidence references this skill records
- `register-row-draft.md` — handles register-row deliverables; this skill handles narrative deliverables
- `../systems/contract-setup-system.md` — primary caller for narrative outputs (contract summary, ready-to-start checklist, role brief)
