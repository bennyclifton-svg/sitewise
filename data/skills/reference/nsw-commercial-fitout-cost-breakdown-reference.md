---
tier: topic
applies_to_roles: [architect-pm, builder, d-and-c]
applies_to_classes: [commercial]
applies_to_work_types: [refurb]
applies_to_subclasses: [office, serviced_office_coworking]
topics: [commercial, fitout, cost, taxonomy, consultant-procurement]
summary: "Practice-level taxonomy for early NSW commercial tenancy fit-out cost plans and consultant fee requests: workbook-ready groups, construction breakdown, interfaces and returnable pricing shape. Structure only — never market rates or active-project evidence."
required_by: {create-pmp: 2, create-cost-plan: 2, consultant-procurement: 2}
status: reference
author: agent
date: 2026-07-26
scope: practice guidance only — structure and pricing returnables; no rate pack
---

# NSW Commercial Fit-Out Cost Breakdown Reference

This is a practice-level taxonomy reference for early NSW commercial tenancy
fit-out and refurbishment projects. It is primarily shaped for Class 5 office
and serviced-office/coworking fit-outs. Class 6 retail, food-and-beverage,
hotel, medical, laboratory and other specialist premises remain outside this
reference's enabled workflow coverage. Their specialist systems and pricing
families require a separately governed reference and must not be inferred from
this one.

The reference supplies structure only. It is not a rate pack, market-rate
source, active-project evidence, project budget, tender recommendation, or
source-of-truth cost plan. Amounts, quantities, programme effects and scope
positions must come from active-project evidence or remain clearly marked TBC.

## Workbook-Ready Groups

Use these groups when shaping a commercial fit-out cost plan:

- Fees and statutory charges
- Consultants
- Tenant construction works
- Client-direct and landlord works
- Contingency / allowances

Keep the tenant, landlord, base-building and client-direct columns distinct.
Do not hide an unresolved interface by placing the whole amount under tenant
construction.

## Tenant Construction Taxonomy

The default NSW commercial fit-out breakdown should remain project-specific but
normally consider these item families:

| Family | Typical cost item labels |
| --- | --- |
| Preliminaries and occupied-building controls | Site establishment, supervision, insurances, hoarding, security, inductions, loading-dock bookings, lift protection, after-hours working, noise/dust controls, temporary services |
| Investigations, approvals and make-safe | Existing-condition surveys, services investigations, hazardous-materials allowance, authority/certifier fees, landlord review fees, isolations, make-safe works |
| Strip-out and demolition | Existing partitions, ceilings, finishes, joinery and redundant services; disposal; protection and making good |
| Structural and builder's work | Mezzanines, stairs, slab penetrations, equipment supports, trimming steel, fire stopping and builder's work in connection |
| Partitions, doors and glazing | Internal walls, acoustic partitions, operable walls, doors, hardware, glazed fronts and security interfaces |
| Ceilings and acoustic treatments | Suspended ceilings, feature ceilings, baffles, acoustic wall treatments, access panels and service coordination |
| Joinery and fixtures | Reception, workpoints, storage, kitchen/breakout joinery, utility points, lockers and specialist fixed furniture |
| Finishes | Floor preparation and coverings, wall finishes, paint, feature finishes, tiling and skirtings |
| Mechanical services | HVAC modifications, supplementary cooling, controls/BMS integration, outside-air and commissioning |
| Electrical and lighting | Distribution, sub-boards, final circuits, lighting and controls, emergency lighting, metering and testing |
| Hydraulic services | Amenities, kitchen/breakout plumbing, sanitary fixtures, drainage, hot water and authority/base-building connections |
| Fire and life-safety services | Sprinklers, detection/EWIS interfaces, smoke control, egress changes, fire stopping, essential-services testing and Performance Solution inputs |
| ICT, AV and security | Structured cabling, comms-room fit-out, Wi-Fi pathways, audiovisual systems, access control, CCTV and intercoms |
| Signage, wayfinding and statutory graphics | Tenant identity, room signs, accessibility signage, evacuation diagrams and directories |
| Testing, commissioning and handover | Integrated services testing, air balancing, commissioning records, training, as-builts, O&M manuals, warranties and defects close-out |
| Specialist tenant systems (gap) | Commercial kitchen, medical gases, laboratory services, compactus, broadcast, trading-floor, high-security or other specialist systems — flag as a gap unless evidenced |

## Client-Direct and Landlord Interfaces

Show these outside the tenant construction subtotal unless project evidence
expressly allocates them to the head contractor:

- loose furniture and workstations;
- IT hardware, software and carrier services;
- artwork, loose equipment and relocation costs;
- landlord base-building upgrades or contributions;
- authority, utility or landlord bonds and refundable deposits;
- lease incentive contributions and rent during delayed occupation;
- client legal, leasing and change-management costs.

For every shared item, state the current split and the document that will close
it. Common interface rows include HVAC capacity, electrical supply, fire-service
capacity, after-hours access, slab penetrations, riser access, lift use,
make-good obligations and landlord design-review fees.

## Consultant and RFP Pricing Structure

Consultant RFPs for a commercial fit-out should request a fee breakdown that is
comparable across respondents:

| Fee component | Returnable pricing requirement |
| --- | --- |
| Investigations and due diligence | Lump sum by investigation, with assumptions about existing records, surveys and destructive inspection |
| Concept / schematic design | Lump sum and named deliverables |
| Design development | Lump sum and coordination workshops included |
| Approval / certification support | Separate SSD, DA, CDC, CC or landlord-review allowance as applicable; do not assume a pathway |
| Tender documentation and procurement | Lump sum, tender queries/addenda allowance and number of tender assessments |
| Construction services | Monthly or visit-based fee with assumed duration, meeting frequency, inspections and reporting |
| Commissioning and handover | Lump sum for witnessing, defects, as-built/O&M review and close-out |
| Disbursements and exclusions | Itemised, with rates or caps where appropriate |
| Optional services | Separately priced options, not embedded in the base fee |
| Hourly rates | Role-based rates for approved variations only |

The RFP scope must also name coordination and document responsibilities.
Particularly test fire engineer/certifier, structural/mezzanine, acoustic,
mechanical, electrical, hydraulic, ICT/AV/security and landlord-consultant
interfaces where they are relevant to the evidence.

## PMP Cost-Control Prompts

For commercial fit-out PMPs, surface:

- the approved tenant budget and its GST basis;
- whether fees, furniture, IT, relocation, landlord works and contingency sit
  inside or outside that budget;
- the lease, possession, rent-free and occupation dates that create cost risk;
- design-freeze and landlord-approval gates before tender;
- occupied-building and after-hours premiums as separate tender returnables;
- base-building capacity and contribution decisions;
- the cost-plan review points at concept, design development, pre-tender,
  tender recommendation and post-contract forecast.

## Use Rules

- Treat this as a starting taxonomy, not a mandatory schedule.
- Preserve active-project cost item labels when a QS cost plan, builder ROM,
  tender schedule or schedule of values supplies better granularity.
- Keep exact approved cost item text stable for later invoices, variations and
  workbook reconciliation.
- Keep GST basis explicit; Create Cost Plan v1 uses ex-GST figures.
- Calculate contingency in Python against the approved base stated in the
  project cost-control decision.
- Prefer lump-sum TBC lines where quantities and rates would create fake
  precision.
- Disclose that no market-rate pack exists instead of inventing rates or
  percentage splits.

## Boundary

This reference intentionally excludes:

- market rates, benchmark $/m² figures or supplier pricing;
- residential BASIX, HBCF, kitchen-PC or footing taxonomy;
- specialist Class 6, hotel, health, laboratory or mission-critical detail
  beyond flagging it as a scope gap;
- any instruction to read another project folder as evidence.
