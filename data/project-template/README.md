# SiteWise Project Template

Purpose: standard folder convention for each SiteWise project. The project folder is the **evidence base** — the agent reads project data first (per `../AGENTS.md §1`), then applies SiteWise doctrine and seed knowledge as reasoning context.

To start a new project: copy this folder, rename it to your project slug, and populate the `README.md` frontmatter below.

## Project metadata (required frontmatter)

Every project's `README.md` opens with the metadata block below. The agent reads this on first task in the project, before drafting any deliverable. It drives the **three-overlay declaration** (`archetype`, `user_role`, `state`) per `../AGENTS.md §2`.

**If `archetype`, `user_role`, or `state` is missing, blank, or `TBC`, the agent stops and asks.** It does not guess from project name, address, budget, or any other proxy. See `../00-doctrine/doctrine.md §seed-consultation-discipline`.

```yaml
---
project_slug:    <slug>                                # required — matches the folder name
client:          <Client Name>                         # required — for owner-builder, the owner-builder's own name
site:            <street address>                      # required

archetype:       <new-dwelling | renovation | multi-dwelling | ancillary | small-commercial>  # required — drives Tier 2 seed loading
user_role:       <owner-builder | architect-pm | builder | d-and-c>                            # required — drives Tier 3 role overlay loading
state:           <NSW | VIC | QLD | SA | WA | TAS | NT | ACT>                                  # required — drives state-specific callouts

ncc_class:       <1a | 1b | 10a | 10b | 2 | etc.>      # required — TBC permitted at mobilisation; must be confirmed by CC
planning_pathway: <CDC | DA | CC-only | exempt | TBC>  # required at concept; TBC permitted at mobilisation

status:          <active | dormant | completed | archived>   # required
budget_total:    <AUD figure or TBC>                          # optional at mobilisation; required by concept endorsement
phases:          [<phase>, <phase>, ...]                      # required — e.g. [mobilisation, design, planning, construction, dlp]
---
```

### How the three overlays drive seed loading

| Declaration | Tier | Loads |
|---|---|---|
| `archetype:` | Tier 2 | `../01-seed/{archetype}-guide.md` (one of: new-dwelling-guide, renovation-guide, multi-dwelling-guide, ancillary-guide, small-commercial-guide) |
| `user_role:` | Tier 3 | `../01-seed/role-{role}.md` (one of: role-owner-builder, role-architect-pm, role-builder, role-d-and-c) |
| `state:` | inline | NSW is the deep default; non-NSW triggers graceful-degradation callouts inside the loaded seeds (no separate state seed in v1) |

Cross-cutting topic seeds (`cost-management-principles.md`, `program-scheduling-guide.md`, `contract-administration-guide.md`, etc.) are loaded by task subject via the `seed-targeted-read` atomic skill.

**Cross-archetype projects** (e.g. a new dwelling with a granny flat addition) declare the primary archetype here. Secondary archetype seeds load task-loaded for the relevant sessions and are recorded in the deliverable's `seed_consulted:` frontmatter. See `../00-doctrine/doctrine.md §seed-consultation-discipline`.

## Standard project folder structure

```text
projects/<project-slug>/
  README.md                           # frontmatter declaration (mandatory before phase-gate work)
  00-brief-pmp/                       # brief, role setup pack, statutory instrument evidence
  01-cost/                            # cost plan, claims, variations, contingency
  02-consultant/                      # consultant appointments and coordination
  03-design/
    <discipline>/                     # discipline-first design evidence, e.g. architect, structural, surveyor
      01-due-diligence/               # site, survey, dilapidation, soil, BAL/flood/bushfire
      02-scheme/                      # scheme options, planning feasibility
      03-detail/                      # developed and detailed design
      04-ifc/                         # issued-for-construction set
      05-as-built/                    # as-built / record drawings
  04-planning-and-authorities/        # BASIX, CC, BPA, Sydney Water, LSL, OSD, consent conditions
  05-procurement/
    <package-name>/
      01-eoi/
      02-tender-pack/
      03-rfi-addendum/
      04-submissions/
      05-evaluation/
      06-recommendation/
  06-programme/                       # master programme, milestone tracker, lookahead, delay register
  07-construction/
    01-loi/                           # letter of intent / pre-contract correspondence
    02-fioa-contract/                 # fully-executed contract and amendments
    03-insurance-bgs/                 # contract works, public liability, bank guarantees
    04-management-plans/              # CMP, WMP, TMP
    05-progress-claims/               # claims and assessments
    06-variations/                    # variation register and pricing
    07-programme-eot/                 # programme updates and EOT claims
    08-rfi-notices/                   # site RFIs and formal contractual notices
    09-cc-pc-oc/                      # CC, PC, OC certificates and inspections
    10-commissioning/                 # appliance, HW, mechanical, PV commissioning records
    11-defects/                       # defects identified during construction and at PC
    12-reports/                       # site, inspection (structural, BASIX) reports
    13-photos/                        # dated site photos
  08-meetings-reporting/              # minutes, action register, decision register, owner updates
  09-handover-dlp/                    # handover plan, PC checklist, defects, O&M, DLP close-out
  99-archive/                         # superseded or historical material
```

Subfolders are **advisory**; small projects (especially owner-builder) need not populate all of them. Empty subfolders are fine — they signal where evidence will land when it arrives.

## Folder purpose summary

- `00-brief-pmp/` — what's being built, on what basis, under what role, with what statutory instruments. Role-specific setup pack lives here.
- `01-cost/` — cost plan, claims, variations, forecasts, contingency, payment recommendations.
- `02-consultant/` — consultant appointments, proposals, scopes, coordination. Use one subfolder per consultant discipline where known.
- `03-design/` — design documentation by discipline first; maturity folders (due diligence → scheme → detail → IFC → as-built) sit under the relevant discipline where useful.
- `04-planning-and-authorities/` — planning approvals, BASIX, CC, BPA, utility approvals, LSL, consent conditions.
- `05-procurement/` — procurement strategy, tender / quote packs, evaluations, recommendations. One subfolder per package.
- `06-programme/` — master programme, milestones, lookaheads, delay register.
- `07-construction/` — contract administration: claims, variations, EOTs, RFIs, defects, inspections, commissioning.
- `08-meetings-reporting/` — agendas, minutes, action and decision registers, monthly reports.
- `09-handover-dlp/` — PC, handover, defects through DLP, compliance evidence pack, close-out.
- `99-archive/` — superseded or historical material retained for reference.

For folder-aligned doctrine (what the project lead must do / must not do in each folder), see `../00-doctrine/doctrine.md`.

## File-type convention

- **Markdown** — agent-readable summaries, decision logs, registers (where lightweight), drafts, source notes.
- **Excel** — registers, cost trackers, programme trackers, tender comparisons. Source of truth for numeric data. Use `excel-safe-edit` / `excel-verify` atomic skills.
- **Word** — formal reports, minutes, correspondence where Word is the convention.
- **PDF** — source-of-truth executed documents (contracts, approvals, certificates). Read-only.

## Source-of-truth rule

- Original signed / executed documents (PDF, Word, Excel as appropriate) remain authoritative.
- Markdown summaries are aids for retrieval and reasoning, not substitutes for source documents.
- Agent outputs are saved as **drafts** until reviewed by the project lead (per `../AGENTS.md §5`).

## Deliverable frontmatter

Every deliverable the agent writes carries a frontmatter block. Minimum fields:

```yaml
---
status: draft                                          # draft | reviewed | superseded
author: agent
date: 2026-05-27                                       # ISO short form
seed_consulted: [archetype-seed.md, role-seed.md, ...]  # required — audit trail of seeds loaded
evidence_refs: [<file paths or document IDs>]
---
```

The `seed_consulted:` field is the discipline that proves the agent loaded the right seeds for this task. Empty `seed_consulted:` on a phase-gate deliverable is a failure — it indicates the agent drafted from general LLM knowledge instead of the practice's curated guidance.

## Agent use rule

For any task in this project, the agent:

1. reads the project `README.md` frontmatter and confirms `archetype`, `user_role`, `state` are declared (stops and asks if not);
2. loads the matching Tier 2 archetype seed and Tier 3 role overlay seed;
3. uses `seed-targeted-read` to identify cross-cutting topic seeds the task needs;
4. reads available project evidence in the active project folder;
5. applies `../00-doctrine/doctrine.md` as the judgement layer;
6. uses `../02-skills/` for repeatable workflow patterns;
7. flags missing evidence, assumptions, and conflicts;
8. drafts the output into the correct folder with `status: draft` and the `seed_consulted:` audit trail.
