# Skill: evidence-sweep

**Job:** Scan the **active project folder** for relevant artefacts before drafting, and return a structured inventory the caller can use to ground the draft in real project evidence rather than assumption.

This skill is one of the §evidence-discipline enforcers. Together with `seed-targeted-read` (which loads doctrine and seed coverage), `evidence-sweep` ensures every draft starts from the §1 authority stack's top tier: project evidence in the **active** project folder.

This skill is read-only. It does not draft, edit, or move anything. It returns an inventory.

## When called

Called by:
- system skills at their first step (e.g. `contract-setup-system` calls `evidence-sweep` after `seed-targeted-read` to identify HBCF certificate, LSL receipt, insurance certificates already in the project);
- atomic skills that need to identify relevant evidence before producing a register row or markdown draft;
- the agent directly, when the user asks "what's in this project" or "what evidence do we have for X".

## Caller passes

- **Active project folder path** — the project root. Required. The skill operates **only within this folder** (per AGENTS.md §11 active-project boundary).
- **Task subject** — short description of what the caller is drafting, used to score artefact relevance. Optional but strongly recommended (a sweep without a subject returns the full inventory unranked).
- **Topic filters (optional)** — explicit folder or file-type filters (e.g. `folder:07-construction/03-insurance-bgs/`, `type:pdf`, `name:HBCF*` or `name:HOW*`).
- **Max results** — defaults to all; the caller can cap.

## Pre-flight — boundaries

Before any scan:

1. Confirm the active project folder path is the **single active project** in scope. If multiple project folders are siblings under a workspace, the active project is the one whose `README.md` is being read. The skill **does not** scan sibling project folders. This is an AGENTS.md §11 invariant.
2. Confirm the active project folder contains a `README.md`. If not, return a flag — the folder is not a SiteWise project.
3. Confirm the §2 three-overlay declaration in the README is complete. If not, the skill **still runs** (evidence-sweep is informational and does not require the declaration gate to have passed), but the caller is advised that downstream drafting will hit the §2 gate.

## Steps

### Step 1 — Walk the project folder tree

Walk all directories from the project root down. For each file encountered, capture:

- **path** — relative to the project root;
- **filename** — including extension;
- **type** — inferred from extension (markdown, excel, word, pdf, image, other);
- **size** — bytes;
- **modified date** — file modification timestamp;
- **folder** — the immediate parent folder relative to the project root (used for §6 voice-register inference and for topical grouping).

Skip:
- `99-archive/` by default (caller can opt in with explicit folder filter);
- hidden files (`.DS_Store`, `.git*`, `~$*` Office lock files);
- empty subfolders.

### Step 2 — Classify by folder topology

The 10-folder template is the topology. Each file is assigned a **topic class** based on its folder:

| Folder | Topic class |
|---|---|
| `00-brief-pmp/` | brief, role-setup, statutory-instrument |
| `01-cost/` | cost-plan, claim, variation-pricing, contingency |
| `02-consultant/` | consultant-appointment, consultant-scope |
| `03-design/01-due-diligence/` | site-survey, dilapidation, soil, BAL, flood, heritage |
| `03-design/02-scheme/` | scheme-design |
| `03-design/03-detail/` | detail-design |
| `03-design/04-ifc/` | ifc-set |
| `03-design/05-as-built/` | as-built |
| `04-planning-and-authorities/` | planning-approval, CC, BPA, BASIX, LSL, Sydney-Water, OSD, consent-condition, utility-approval |
| `05-procurement/**/01-eoi/` | procurement-eoi |
| `05-procurement/**/02-tender-pack/` | tender-pack |
| `05-procurement/**/03-rfi-addendum/` | tender-rfi |
| `05-procurement/**/04-submissions/` | tender-submission |
| `05-procurement/**/05-evaluation/` | tender-evaluation |
| `05-procurement/**/06-recommendation/` | tender-recommendation |
| `06-programme/` | programme, milestone, lookahead, delay |
| `07-construction/01-loi/` | letter-of-intent |
| `07-construction/02-fioa-contract/` | head-contract |
| `07-construction/03-insurance-bgs/` | contract-works-insurance, public-liability, workers-comp, bank-guarantee |
| `07-construction/04-management-plans/` | CMP, WMP, TMP |
| `07-construction/05-progress-claims/` | progress-claim |
| `07-construction/06-variations/` | variation |
| `07-construction/07-programme-eot/` | programme-update, eot |
| `07-construction/08-rfi-notices/` | rfi, contract-notice |
| `07-construction/09-cc-pc-oc/` | cc-certificate, pc-certificate, oc-certificate, inspection |
| `07-construction/10-commissioning/` | commissioning, BASIX-final |
| `07-construction/11-defects/` | defect |
| `07-construction/12-reports/` | site-report, inspection-report |
| `07-construction/13-photos/` | site-photo |
| `08-meetings-reporting/` | meeting-minutes, action-register, decision-register, owner-update, monthly-report |
| `09-handover-dlp/` | handover, PC-checklist, DLP, OM-warranty |

A file outside the standard topology gets topic class `unclassified` and is reported separately.

### Step 3 — Filename inference

In addition to folder topology, infer artefact type from filename patterns. Useful when a file is in a "wrong" folder or when the folder is generic.

Examples:

| Filename pattern | Inferred artefact |
|---|---|
| `*HOW*.pdf`, `*HBCF*.pdf` | HBCF / HOW certificate |
| `*LSL*.pdf`, `*Long Service*.pdf` | LSL receipt |
| `*BASIX*.pdf` | BASIX certificate |
| `*CC*Plans*.pdf`, `*CC plans*` | CC drawing set |
| `*CMP*.pdf`, `*Construction Management*.pdf` | Construction Management Plan |
| `*WMP*.pdf`, `*Waste Management*.pdf` | Waste Management Plan |
| `*TMP*.pdf`, `*Traffic Management*.pdf` | Traffic Management Plan |
| `*Sewer*.pdf`, `*Sydney Water*.pdf` | Sydney Water diagram or approval |
| `*Dilapidation*.pdf` | Dilapidation report |
| `*Conformance*.pdf`, `*CFT*.pdf` | Concrete conformance test |
| `*OSD*.pdf` | OSD certificate or drawing |
| `*Structural*Plans*.pdf` | Structural drawing set |
| `*Specification*.docx` | Specification |
| `Contract*.pdf`, `*Conditions*.pdf` | Contract or contract conditions |
| `*Finance*.xlsx`, `*Cost*.xlsx`, `*Budget*.xlsx` | Cost register / project finance workbook |
| `*Programme*.xlsx`, `*Schedule*.xlsx` | Programme |
| `*Register*.xlsx`, `*Register*.md` | Register (type inferred from filename specifics) |
| `*HIA*Specifications*.pdf`, `*HIA*Spec*.pdf` | HIA specifications document |

The inference table is not exhaustive — the goal is to surface common residential artefact types reliably. Where filename does not match any pattern, the inferred type is `unknown` and the folder topology is the primary signal.

### Step 4 — Relevance scoring against task subject

If the caller passed a task subject, score each artefact for relevance. Scoring is heuristic — match the task subject's keywords against:

- folder topic class;
- inferred artefact type;
- filename substrings.

Return scores qualitatively (high / medium / low / none) rather than numerically.

Example: task subject is "draft progress claim assessment for slab stage". High-relevance artefacts:
- anything in `07-construction/02-fioa-contract/` (head contract — defines stage and payment mechanism);
- anything in `07-construction/05-progress-claims/` (prior claims for context);
- `*CFT*.pdf` files in `07-construction/12-reports/` or `09-cc-pc-oc/` (concrete conformance for slab stage evidence);
- anything in `07-construction/09-cc-pc-oc/` (inspection records);
- anything in `01-cost/` (cost register for cumulative tracking);
- the project `README.md` (frontmatter — overlay declarations).

Medium-relevance: `BASIX*.pdf`, `Structural*Plans*.pdf` (referenced by inspections), `06-programme/*` (claim aligns to programme).

Low / none: planning approvals, dilapidation, owner-supplied schedules, photos.

### Step 5 — Return the structured inventory

Return a markdown-formatted inventory grouped by relevance (where a task subject was passed) or by folder topology (where no task subject). For each artefact:

- relative path;
- inferred artefact type;
- topic class;
- size and modified date;
- relevance (where applicable);
- one-line note where the filename or folder is ambiguous.

Also return:

- **count by folder** — how many files in each top-level folder;
- **gaps** — common artefacts the topology expects but did not find (e.g. for a `user_role: builder` project, expected and missing: HBCF certificate, LSL receipt, head contract, CWI certificate);
- **§2 declaration check result** — whether the project README has complete frontmatter.

The output is the **inventory only**. The skill does not interpret artefact contents (e.g. it does not open the PDF and read it). Content interpretation is the caller's job.

## Rule

The skill operates **only within the active project folder boundary** (AGENTS.md §11). Reading another project folder is a §1 authority-stack breach — the skill does not do it, even if the caller asks.

The skill does **not** modify files. It does not move, rename, copy, delete, or rewrite. It is read-only.

The skill returns **what is there**, not interpretation of what is there. The caller does the interpretation.

If the active project folder is empty (e.g. brand-new project at mobilisation), the skill returns an empty inventory and the §2 declaration check result. The caller decides what to do with the emptiness — typically run `contract-setup-system` to begin populating.

## Output frontmatter (when the inventory is saved as a deliverable)

If the caller saves the sweep output as a project deliverable (e.g. an evidence inventory under `08-meetings-reporting/`), the standard §5 frontmatter applies:

```yaml
---
status: draft
author: agent
date: <ISO date>
seed_consulted: []  # evidence-sweep does not load seeds itself
evidence_refs: [<paths returned in the inventory>]
sweep_task_subject: "<the task subject the sweep was run for>"
---
```

Most callers consume the sweep output without saving it — it is intermediate context, not a deliverable.

## See also

- `../../AGENTS.md §1` — authority stack (project evidence is tier 1)
- `../../AGENTS.md §11` — active-project boundary (the boundary this skill respects)
- `../../00-doctrine/doctrine.md §evidence-discipline` — why grounding drafts in real evidence matters
- `seed-targeted-read.md` — typically called before this skill, to load the right doctrine / seed coverage
- `register-row-draft.md` — frequently called after this skill, to draft register rows referencing the swept evidence
- `markdown-draft-for-review.md` — saves narrative deliverables that reference swept evidence
- `../systems/contract-setup-system.md` — primary caller, uses this skill to find existing statutory-instrument evidence at mobilisation
