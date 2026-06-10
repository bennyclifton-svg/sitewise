# Synthetic mobilisation evidence — test packs

Markdown fixtures for **Create PMP** hybrid compiler testing. Copy files into a project workspace (e.g. `04-projects/<slug>/02-consultant/…`) and re-index / rerun Create PMP.

Each pack tests a different evidence shape so tuning does not overfit to Chen Residence alone.

---

## Pack A — Chen Residence (baseline mobilisation)

**Project overlays:** `new-dwelling`, `architect-pm`, `NSW`  
**Use when:** Regression baseline — post-engagement, engagement letter + fee proposal only.

| File | Filing path (suggested) |
| --- | --- |
| `01-engagement-letter-harrison-clarke-studio.md` | `02-consultant/architect/01-engagement-letter-harrison-clarke-studio.md` |
| `02-fee-proposal-harrison-clarke-studio.md` | `02-consultant/architect/02-fee-proposal-harrison-clarke-studio.md` |

**Expected PMP posture:** Evidence on file = engagement + fee proposal. Gaps = owner brief sign-off, construction budget, geotech, certifier, master programme. Linden conflict disclosure. Target DA September 2026.

---

## Pack B — Chen Residence (Stage 1 progressed)

**Same overlays as Pack A.**  
**Use when:** Testing evidence enrichment — gaps should close as documents accrue.

Drop in **numeric order** (simulate mobilisation timeline):

| Stage | Files | What it tests |
| --- | --- | --- |
| Mobilisation | `01`, `02` | Baseline (Pack A) |
| Brief + budget | `03`, `04` | Owner project brief signed; construction budget confirmed |
| Due diligence | `05`, `06`, `07`, `08` | Survey, geotech, dilapidation, Sydney Water — due diligence rows can upgrade |
| Advice | `09`, `10` | Planning pathway memo; stormwater consultant quote + owner escalation format |
| Programme | `11` | Master programme on file |
| Approvals | `12` | Principal certifier appointed |

**Expected PMP posture (full pack):** Brief and budget **Grounded**. Geotech **Grounded**. Master programme **Grounded**. Certifier **Grounded**. Remaining gaps: none of the five standard mobilisation gaps. Narrative should **not** require Linden-style conflict rows on other projects — on Chen, conflict disclosure remains in fee proposal.

---

## Pack C — Walsh Terrace Renovation

**Project overlays:** `renovation`, `architect-pm`, `NSW`  
**Folder:** `walsh-renovation/`  
**Use when:** Different archetype, different appointee, **no tender conflict**, CDC-not-assumed DA pathway, live-occupancy context.

| File | Content |
| --- | --- |
| `01-engagement-letter-atelier-north.md` | Architect-PM appointment, renovation scope |
| `02-fee-proposal-atelier-north.md` | Terrace addition + internal reconfiguration; no conflict disclosure |
| `03-owner-project-brief-walsh-house.md` | Signed brief + construction budget confirmed |
| `04-email-builder-preliminary-cost-advice.md` | Early builder conversation — ROM $920k, latent conditions caveat |
| `05-email-heritage-advisor-desktop.md` | Heritage advisor desktop — terrace in heritage streetscape |

**Expected PMP posture:** Renovation due diligence checklist. No Linden / conflict register pressure. Builder ROM is **not** a formal construction budget in the extractor — budget comes from owner brief.

---

## Pack D — Nguyen Dual Occupancy (multi-dwelling)

**Project overlays:** `multi-dwelling`, `architect-pm`, `NSW`  
**Folder:** `nguyen-dual-occ/`  
**Use when:** Multi-dwelling archetype, different fee structure, CDC pathway assumed, no September-2026-style date.

| File | Content |
| --- | --- |
| `01-engagement-letter-studio-koa.md` | Dual occupancy / two-dwelling scope |
| `02-fee-proposal-studio-koa.md` | CDC pathway assumed; two invited builders; no conflict section |
| `03-feasibility-budget-memo-studio-koa.md` | Feasibility ROM and construction budget confirmed |

**Expected PMP posture:** Multi-dwelling programme sub-milestones / staged OC language. CDC assumed — judgements should **not** invent DA-only pathway. No conflict disclosure requirements.

---

## Pack E — Engagement letter only (minimal)

**Project overlays:** `new-dwelling`, `architect-pm`, `NSW`  
**Folder:** `engagement-only/`  
**Use when:** Partial evidence — fee proposal not yet indexed.

| File | Content |
| --- | --- |
| `01-engagement-letter-only-harbour-design.md` | Engagement only; no fee proposal companion |

**Expected PMP posture:** Appointment grounded from letter. Fee staging may be partial. Planning pathway / conflict / project understanding **Partial** or **Not evidenced**. Do not claim fee proposal on file.

---

## How to test in Clerk

1. Create or select a test project with matching **archetype**, **user_role**, and **state**.
2. Copy pack files into the project workspace under sensible paths (`02-consultant/`, `03-design/01-due-diligence/`, etc.).
3. Re-index project evidence (ingest / file watcher).
4. Run **Create PMP** (or **Update PMP** if a baseline draft exists).
5. Compare gaps, evidence map, and internal audit to the **Expected posture** above.

## Automated tests

Harrison Clarke baseline (`01` + `02`) is wired in `backend/tests/workflows/hybrid_pmp_fixtures.py`. Additional packs are for manual / future parametrized tests.
