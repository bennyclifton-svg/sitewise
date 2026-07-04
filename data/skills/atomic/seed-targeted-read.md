# Skill: seed-targeted-read

> **STATUS: superseded-by-runtime.** In the hosted product this contract is
> implemented by `backend/app/sitewise/knowledge_catalog.py` (selection +
> section loading, driven by seed frontmatter) and exposed to the agent via the
> `list_platform_knowledge` / `read_platform_knowledge` MCP tools. The
> Step 1/Step 2 tables below are now generated truth in seed frontmatter
> (`tier`, `loaded_by`, `topics`); this file remains the design rationale.

**Job:** Load only the seed guides that match the task. Never load all of `../../01-seed/` by default. Loading is driven by the project's three-overlay declaration (`archetype`, `user_role`, `state`) plus the task subject.

This skill is the gatekeeper for `doctrine.md §seed-consultation-discipline`. Every other skill that needs domain coverage calls this skill first.

## Caller passes

- **Task subject** (e.g. "draft progress claim assessment", "tender evaluation for framing package", "BASIX compliance check at IFC")
- Optional: explicit seed list to load (skips topic matching)

## Pre-flight — the gate

Before loading any seed, confirm the project `README.md` frontmatter declares all three overlays:

- `archetype:` ∈ { `new-dwelling`, `renovation`, `multi-dwelling`, `ancillary`, `small-commercial` }
- `user_role:` ∈ { `owner-builder`, `architect-pm`, `builder`, `d-and-c` }
- `state:` ∈ { `NSW`, `VIC`, `QLD`, `SA`, `WA`, `TAS`, `NT`, `ACT` }

**If any is missing, blank, or `TBC`:** **stop, do not load any seed, do not draft.** Return a stop-and-ask response to the caller:

> Cannot proceed: the project `README.md` is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before any phase-gate work. See `../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`.

Do not guess the missing value from project name, address, budget, site, or any other proxy.

## Steps (once the gate passes)

### Step 1 — Always load the overlay seeds

These are mandatory for every phase-gate task:

| Declaration | Seed loaded |
|---|---|
| `archetype: new-dwelling` | `../../01-seed/new-dwelling-guide.md` |
| `archetype: renovation` | `../../01-seed/renovation-guide.md` |
| `archetype: multi-dwelling` | `../../01-seed/multi-dwelling-guide.md` |
| `archetype: ancillary` | `../../01-seed/ancillary-guide.md` |
| `archetype: small-commercial` | `../../01-seed/small-commercial-guide.md` |
| `user_role: owner-builder` | `../../01-seed/role-owner-builder.md` |
| `user_role: architect-pm` | `../../01-seed/role-architect-pm.md` |
| `user_role: builder` | `../../01-seed/role-builder.md` |
| `user_role: d-and-c` | `../../01-seed/role-d-and-c.md` |

`state:` does not load a separate seed in v1. NSW is the deep default in every seed; non-NSW triggers inline graceful-degradation callouts. If `state:` is not NSW and the task touches a state-specific instrument (HOW, LSL, BASIX, planning pathway) with no callout in the loaded seed, **flag the gap** in the output rather than silently extending NSW guidance.

### Step 2 — Match task subject to cross-cutting topic seeds

If the caller named specific seed files, load only those. Otherwise match by topic:

| Task signal | Cross-cutting seed(s) to consider |
|---|---|
| Cost, budget, contingency, claim, variation pricing | `cost-management-principles.md` |
| Programme, critical path, lead times, residential cycle times | `program-scheduling-guide.md` |
| Risk register, risk review, mitigation, escalation | `program-scheduling-guide.md`, `setup-and-commission-guide.md` |
| Tender, procurement, market response, RFQ, quoting | `procurement-quoting-guide.md` |
| Variations, EOTs, instructions, contract clause interpretation | `contract-administration-guide.md` |
| Setup, mobilisation, commission, statutory instrument check | `setup-and-commission-guide.md` |
| NCC / BCA compliance pathway, Class 1 / Class 10 reference | `ncc-reference-guide.md` |
| Australian Standards reference (AS 2870, AS 1684, AS 4055, AS 3959, AS 3500, etc.) | `as-standards-reference.md` |
| Trade interface coordination, scope-gap risk between trades | `trade-interfaces-coordination-guide.md` |
| Structural — footing, frame, slab classification, wind, BAL | `structural-residential.md` |
| MEP — HW, gas, electrical, NBN, mechanical ventilation | `mep-residential.md` |
| Civil — site cut/fill, OSD, stormwater, sewer, driveway | `civil-residential.md` |
| Finishes — brick, render, plaster, tile, joinery, glazing, paint | `finishes-residential.md` |
| BASIX, NatHERS, insulation, glazing, HW, PV, sustainability | `sustainability-energy-guide.md` |
| Defects, DLP, residential defect catalogue, warranty obligations | `defects-and-dlp-guide.md` |

Multiple matches are normal — load all matched seeds.

### Step 3 — Load and record

Load the matched seeds as task evidence. Cite the seed in any output that uses its content.

Every output written from this seed set must include `seed_consulted:` in frontmatter, listing every seed loaded (overlay + cross-cutting). Empty or omitted `seed_consulted:` on a phase-gate deliverable is a failure per `doctrine.md §seed-consultation-discipline`.

### Step 4 — Cross-archetype tasks

Where a task touches a secondary archetype (e.g. a `new-dwelling` project that adds an `ancillary` granny flat partway through), load the secondary archetype seed task-loaded for that session and record both archetypes in `seed_consulted:`. Primary archetype focus is not lost — the secondary seed is overlaid, not substituted.

## Rule

Seed informs prompts and domain coverage. **Seed does not override project evidence.** If seed and project evidence conflict, project evidence wins per `../AGENTS.md §1`.

This skill **does not draft anything**. It loads the right seed set. Drafting is the caller's job, using the seeds this skill provides.

## See also

- `../AGENTS.md §1` — authority stack
- `../AGENTS.md §2` — three-overlay declaration gate
- `../AGENTS.md §3` — seed loading rules
- `../../00-doctrine/doctrine.md §seed-consultation-discipline` — gating rationale
- `../../00-doctrine/doctrine.md §state-handling` — state callout behaviour
