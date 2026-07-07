# Prompt: create a new synthetic mobilisation evidence pack

Copy the block below into a new chat when you need another SiteWise test pack. Replace the bracketed placeholders before sending.

---

```
Create a synthetic mobilisation evidence pack for SiteWise testing in this repo.

## Location and naming

- Save all pack files under `data/synthetic-mobilisation-evidence/<project-slug>/`
- Use lowercase kebab-case for `<project-slug>` (e.g. `walsh-renovation`, `meridian-chambers-fitout`)
- Add or update `PACK.md` in that folder and add a short entry to `data/synthetic-mobilisation-evidence/README.md`

## Project parameters

- **Archetype / overlays:** [e.g. commercial-fitout, renovation, new-dwelling, multi-dwelling] + [architect-pm or other role] + [NSW or other state]
- **Project type:** [e.g. commercial office fit-out refurbishment, terrace renovation, dual occupancy]
- **Site:** [address, suburb, state]
- **Client / owner:** [names and entity]
- **Architect-PM:** [firm name — must differ from existing packs unless intentionally reusing]
- **Planning pathway:** [DA, CDC, SSD, exempt works — be explicit about what is and is not assumed]
- **Occupancy context:** [vacant, live occupation, partially occupied commercial building, etc.]

## Pack structure (three tranches, ~12–15 Markdown files)

### Tranche 1 — Initial profiling and briefing (numbered `01`–`05`)

Purpose: enough evidence to run **Create PMP** and **Create Cost Plan** for the first time.

Include a mix of:

- tenant-to-landlord or owner briefing correspondence
- town planner / planning consultant advice (pathway, constraints, timing)
- architect-PM engagement letter and fee proposal
- early ROM or informal cost advice that is **not** a formal construction budget
- one specialist desktop advice or due-diligence note relevant to the archetype

Do **not** include a signed owner brief with confirmed construction budget in Tranche 1 unless you deliberately want to test that edge case.

### Tranche 2 — Project establishment and enrichment (`p02-00` index + `p02-01`…)

Purpose: evidence to run **Update PMP** and **Update Cost Plan**.

Include:

- `p02-00-pack-additional-fees-correspondence.md` — index, filing paths, expected workflow posture
- signed owner / tenant project brief with **confirmed construction budget** and contingencies
- 2–4 consultant fee proposals (discipline-specific to the archetype)
- email from architect-PM updating PMP risks, cost-plan placeholders, and tender-scope instructions
- owner approval email expanding tender strategy (e.g. two builders → three) and owner-supplied allowances

Leave deliberate gaps the extractor should still report (e.g. no PCA, no geotech, no master programme) unless the scenario is meant to close all gaps.

### Tranche 3 — Builder tender quotes (`p03-00` index + three quotes)

Purpose: Tender Comparison Module and cost-plan reconciliation testing.

Three quotes from different builders, each from a different angle:

1. **Minimal** — lump sum, thin breakdown, aggressive exclusions, assumes favourable site conditions
2. **Mid** — elemental summary, explicit provisional sums and PC items, moderate risk treatment
3. **Detailed** — trade breakdown, reconciliation table, tender qualifications, premium positioning

All quotes must:

- reference the same project, scope, and tender drawing set
- use different GST presentation styles where safe (ex-GST primary vs mixed notes)
- price the same core scope but treat risk differently (after-hours, hazmat, services upgrades, landlord vs tenant interface, latent conditions)
- stay internally consistent with Tranche 1 and 2 facts (budget ceiling, planning pathway, consultant allowances, owner-supplied items)

## Edge cases to deliberately seed

Pick at least 8–10 from this list (adapt to archetype):

- ROM email explicitly **not** a formal budget; budget only from signed brief
- no tender conflict disclosure (or include one if testing conflict register)
- live / partial occupation cost risk
- landlord vs tenant scope split and base-building assumptions
- provisional sums vs PC items vs fixed inclusions named inconsistently across quotes
- consultant fees that must flow into cost plan but not close unrelated PMP gaps
- planning pathway language that must not be overridden (e.g. DA not CDC)
- programme dates in multiple formats (weeks, months, calendar targets)
- owner-held contingency separate from construction budget ceiling
- hazardous materials / latent conditions allowances
- reporting cadence stated in engagement letter (not default monthly)
- heritage, fire engineering, acoustic, or services capacity themes as applicable

## Formatting rules

- Plain Markdown only; realistic letter/email/report headers
- Australian construction context; AUD; ex-GST and incl-GST stated clearly
- Filenames: `01-…` for Tranche 1; `p02-…` and `p03-…` for follow-on packages (do not renumber original `01`–`05` when adding tranches)
- Each pack file should be self-contained and cite consistent parties, dates, and amounts
- `PACK.md` must list overlays, suggested workspace filing paths, expected PMP posture, and deliberate gaps

## Deliverables

1. All Markdown files in the new subfolder
2. Updated `PACK.md` and README pack entry
3. Brief summary of what each tranche tests and the expected extractor posture after each stage

Do not wire automated tests unless I ask — this pack is primarily for manual SiteWise iteration and future critique loops.
```

---

## After the pack exists

1. Create a test project with matching archetype, role, and state overlays.
2. Copy Tranche 1 files into the workspace; re-index; run Create PMP and Create Cost Plan.
3. Add Tranche 2; re-index; run Update PMP and Update Cost Plan.
4. Add Tranche 3; re-index; run tender comparison / evaluation workflows.
5. Critique outputs against `PACK.md` expected posture; feed gaps back into SiteWise code or prompts.
