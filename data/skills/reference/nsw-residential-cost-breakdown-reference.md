---
tier: topic
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
applies_to_archetypes: [new-dwelling, renovation, multi-dwelling, ancillary]
topics: [cost, taxonomy]
summary: "Practice-level taxonomy for early NSW residential cost plans: workbook-ready groups and the construction breakdown shape. Practice guidance only — never active-project evidence, a market-rate source, or a source-of-truth cost plan."
required_by: {create-cost-plan: 2}
status: reference
author: agent
date: 2026-05-30
source: sanitised taxonomy derived from 04-projects/hall-house/01-cost/L09-House-Price.xlsx
scope: practice guidance only
---

# NSW Residential Cost Breakdown Reference

This is a practice-level taxonomy reference for early NSW residential cost plans.
It was derived from a workbook used in prior practice material for the shape of
its construction breakdown only. It is not active-project evidence, a market-rate
source, a project budget, a tender recommendation, or a source-of-truth cost
plan.

Create Cost Plan workflows may cite this reference as practice guidance. They
must not load or cite the source project workbook, and they must not treat this
reference as evidence for any active project.

## Workbook-Ready Groups

Use these groups to shape Markdown cost plans that can later map into the
practice workbook structure:

- Fees and charges
- Consultants
- Construction
- Contingency / allowances

## Construction Taxonomy

The default NSW residential construction breakdown should remain project-specific
but normally consider these item families:

| Family | Typical cost item labels |
| --- | --- |
| Preliminaries | Preliminaries, authority fees, warranty and statutory levies, temporary services, site amenities, supervision |
| Consultants | Surveyor, geotechnical, structural, civil, hydraulic, energy, certifier or other consultant allowances where project evidence supports them |
| Site works | Site establishment, site clearing, demolition, earthworks, excavation, retaining, service lead-ins, temporary protection |
| Termite and ground treatment | Termite treatment, underslab treatment, pest management allowances |
| Foundations and concrete | Foundation piers, footings, slab, concrete works, reinforcement and concrete pumping allowances |
| Frame, roof and lockup | Wall framing, roof trusses, structural steel, craneage, windows, masonry, scaffolding, roof protection, roofing, external cladding, eaves, lockup |
| Internal works | Insulation, plasterboard, waterproofing, garage doors, tiling, joinery, stonework, tapware, fixtures, fittings, shower screens, mirrors, wardrobes, fixout carpentry |
| Appliances and equipment | Appliances, hot water systems and other equipment allowances where supplied through the builder contract |
| Services | Hydraulic services, electrical services, mechanical services, communications and service fitoff allowances |
| Finishes | Floor coverings, painting, joint sealing and caulking |
| External works | Softscape, hardscape, driveways, paths, fencing, gates, external services and final cleaning |

## Use Rules

- Treat the list as a starting taxonomy, not a mandatory schedule.
- Use project-specific `Cost Items` labels in the cost plan.
- Keep exact approved `Cost Items` text stable because later invoices and variations
  will use that text as a workbook lookup identity.
- Keep GST basis explicit. Create Cost Plan v1 uses ex-GST figures.
- Calculate construction contingency on construction cost only.
- Keep owner-side costs below the main workbook-mapping table.
- Separate owner-supplied items from PC sums and builder-contract costs.
- Prefer lump-sum lines where quantity and rate detail would create fake precision.

## Boundary

This reference intentionally excludes:

- project/client names, addresses, lot numbers or consultant names from the source workbook;
- source workbook rates, totals, contract values or variations;
- current market-rate advice;
- any instruction to read another project folder as evidence.
