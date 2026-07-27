---
tier: topic
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
applies_to_classes: [industrial]
applies_to_subclasses: [data_centre]
applies_to_work_types: [new, refurb, extend]
topics: [industrial, data-centre, mission-critical, electrical, cooling, commissioning, cost, taxonomy, consultant-procurement]
summary: "Practice-level taxonomy for early NSW data-centre cost plans: site, shell, electrical, cooling, controls, security and integrated-systems-testing packages. Structure only—never capacity design, market rates or active-project evidence."
required_by: {create-pmp: 2, create-cost-plan: 2, consultant-procurement: 2}
status: reference
author: agent
date: 2026-07-26
scope: practice guidance only—structure and pricing returnables; no rate pack and no mission-critical design
---

# NSW Data Centre Cost Breakdown Reference

This reference supplies a practice-level cost structure for NSW data-centre
projects. It separates site and shell works from electrical, cooling, controls,
security, information-technology, utility, vendor and commissioning packages.

The project team must establish the IT capacity basis, deployment stages,
resilience topology, concurrent-maintainability requirements, utility strategy,
energy and water targets, technology scope, security requirements and
acceptance criteria from active-project evidence. A `data_centre` taxonomy
selection does not establish a tier, load, topology or performance target.

This is structure only. It is not a rate pack, benchmark, mission-critical
design, project budget, tender recommendation, active-project evidence or
source-of-truth cost plan. Amounts, quantities, rates, percentages, capacities
and programme effects must be evidenced or marked TBC.

## Workbook-Ready Groups

Use these top-level groups:

- fees, investigations and statutory charges;
- site, shell and architectural construction;
- mission-critical power, cooling, controls and security systems;
- utility, operator, tenant and vendor-direct packages;
- integrated testing, contingency and explicit allowances.

Maintain stage or hall identifiers throughout the breakdown. Keep shell,
powered-shell, technology and customer/tenant packages separate. State whether
vendor pricing includes freight, currency exposure, installation, controls,
consumables, spares, testing and commissioning.

## Site and Shell Cost Families

| Family | Typical cost item labels and boundaries |
| --- | --- |
| Preliminaries and project controls | Site establishment, supervision, insurances, security, logistics, heavy lifts, temporary services, permit controls, staging and live-facility procedures |
| Investigations, demolition and enabling works | Surveys, geotechnical and environmental investigations, demolition, diversions, temporary capacity, protection, decommissioning and early works |
| Civil, earthworks and utility corridors | Cut/fill, ground improvement, retention, roads, heavy-duty pavements, drainage, utility routes, service yards and environmental controls |
| Substructure and equipment foundations | Footings, slabs, plant bases, generator and transformer foundations, pits, trenches, plinths, embeds, vibration interfaces and fuel-system civil works |
| Superstructure and envelope | Concrete, precast, structural steel, roof, cladding, doors, louvres, blast or security provisions where evidenced, weatherproofing and access systems |
| Data halls and technical spaces | White-space shell, cages or partitions where in scope, ceilings where specified, raised access floor where specified, containment supports, loading and fit-out interfaces |
| Administration and support areas | Offices, meeting, amenities, loading, storage, workshops, network rooms and operational-support fit-out |
| External and site works | Parking, fencing, vehicle controls, lighting, landscaping, acoustic or visual screening, drainage, tanks, utility compounds and authority handbacks |

## Mission-Critical Systems Cost Families

| Family | Typical cost item labels and boundaries |
| --- | --- |
| Utility and high-voltage intake | Utility applications and project works, substations, transformers, HV switchgear, protection, metering, cabling, earthing and authority interfaces |
| Standby generation and fuel | Generators, controls, synchronisation, load banks where in scope, fuel storage and distribution, treatment, exhaust, acoustic systems and testing |
| Uninterruptible power | UPS modules, batteries or other storage, switchboards, static transfer, bypass, controls, monitoring, containment, ventilation and safety systems |
| Low-voltage distribution | Main and distribution boards, busway, cables, rack power interfaces, protection, metering, earthing and testing |
| Mechanical cooling and heat rejection | Chillers or other plant as designed, pumps, heat rejection, computer-room units, pipework, valves, water treatment, refrigerant systems and acoustic treatment |
| Air or liquid distribution | Air paths, containment interfaces, ductwork, fans, pipework, manifolds, leak detection, drainage and rack/technology connection points as evidenced |
| Water and hydraulic systems | Domestic and process water interfaces, cooling make-up, drainage, tanks, treatment, pumps and water-monitoring systems |
| Fire and life safety | Detection, warning, suppression where designed, hydrants, sprinklers, smoke-control interfaces, fire stopping, cause-and-effect testing and certification |
| Controls and monitoring | Building and electrical monitoring, controls, data-centre infrastructure management where specified, sensors, gateways, licences, integration and cybersecurity responsibilities |
| ICT, carrier and technology interfaces | Carrier rooms and pathways, meet-me rooms, backbone systems, timing or network interfaces and tenant/customer demarcations; active IT equipment remains separate unless expressly included |
| Physical security | Perimeter, barriers, gates, guard systems, access control, CCTV, intrusion detection, interlocks, screening and security-management integration |
| Integrated systems testing | Component, factory and site tests, pre-functional and functional tests, load testing, failure-mode and sequence testing, integrated systems testing, records and issue close-out |
| Operations readiness and handover | Training, standard operating and emergency procedures where commissioned, as-builts, O&M manuals, asset data, spares, warranties and operational-readiness support |
| Specialist technology package (gap) | Active compute, storage, network, customer racks, proprietary liquid-cooling technology or tenant fit-out—separate and define from evidence |

## Stage, Capacity and Interface Structure

For each stage, hall or capacity block, identify the documented basis for:

- planned and installed IT load;
- electrical and mechanical capacity and redundancy;
- shell versus fitted or energised scope;
- day-one works versus future provision;
- shared plant and allocation between stages;
- utility, operator, customer and vendor battery limits;
- commissioning level and acceptance criteria.

Future capacity is not current construction cost. Show future provisions,
deferred fit-out and option packages separately.

## Consultant and Tender Pricing Returnables

Requests should separately price:

- basis-of-design verification and utility investigations;
- concept, developed, approval and construction documentation stages;
- site, architectural, structural, power, cooling, controls, fire and security
  coordination;
- utility and vendor interfaces;
- design reviews, failure-mode analysis and commissioning planning where
  evidenced;
- tender support and construction services stated by duration and attendance;
- factory testing, site testing, integrated systems testing and operational
  readiness;
- disbursements, exclusions, options and approved-variation hourly rates.

Require respondents to declare the capacity, staging, topology, owner-supplied
equipment, utility advice and vendor data assumed by their fee.

## Cost-Control Prompts

PMPs and cost plans should identify:

- the approved cost limit and shell/critical-system/technology boundaries;
- the capacity and staging basis behind each subtotal;
- utility application, augmentation and energisation responsibilities;
- currency, freight, tax and escalation treatment for major equipment;
- long-lead procurement, factory testing and vendor-data dates;
- live-facility, security, shutdown and temporary-capacity assumptions;
- commissioning, load-bank, fuel, water and testing-consumable responsibilities;
- contingency, future provision and interface-risk treatment.

All capacity normalisation, totals, currency conversions, contingencies and
option comparisons must be calculated deterministically from approved inputs.

## Use Rules

- Treat these families as a starting taxonomy, not a mission-critical design.
- Preserve project stage, hall, system and vendor-package identifiers where
  they are stable and evidenced.
- Keep shell, critical systems, active technology and owner/vendor packages
  separately totalled.
- Keep GST, currency, freight and utility-augmentation bases explicit.
- Prefer TBC or a documented provisional allowance to invented capacities,
  quantities or rates.
- Describe topology, resilience and performance positions as evidence gaps
  until established by competent project sources.

## Boundary

This reference intentionally excludes:

- capacity design, tier certification, topology selection, failure-mode
  conclusions and performance guarantees;
- active IT equipment, customer systems or tenant fit-out unless project
  evidence expressly includes them;
- market rates, benchmark $/MW or $/m² figures, equipment prices or trade
  percentages;
- assumed utility capacity, connection dates or authority outcomes;
- any instruction to use another project as evidence.
