# Platform Knowledge Coverage

This is the maintenance contract for SiteWise platform seeds and cost
references. The canonical project axes are `building_class`, `work_type`,
`subclasses`, and `work_scope`. Legacy `archetype` files remain compatibility
inputs only.

## Routing policy

- Class overlays describe recurring delivery conditions for one building class.
- Work-type overlays exist only where the delivery model changes materially
  across classes (`advisory` and building `remediation`).
- Discipline guides are cross-class and are loaded by the relevant consultant
  procurement profile or topic search.
- Cost references define breakdown structure and pricing returnables. They are
  platform guidance, never active-project evidence or a substitute for rates.
- Subclass and work-scope filters must be used when a guide would otherwise
  overclaim coverage. Unknown specialist scope stays unsupported.

## Implemented first-pass coverage

| Class/work family | Required delivery guide | Cost reference |
| --- | --- | --- |
| Class 1 house/townhouse | `residential-construction-guide.md` | `nsw-residential-cost-breakdown-reference.md` |
| Apartments/BTR/student/social-affordable | `multi-residential-apartments-guide.md` | `nsw-multi-residential-cost-breakdown-reference.md` |
| Commercial office/retail base building | `commercial-construction-guide.md` | `nsw-commercial-base-building-cost-breakdown-reference.md` |
| Commercial office/coworking fit-out | `commercial-construction-guide.md` | `nsw-commercial-fitout-cost-breakdown-reference.md` |
| Industrial warehouse/logistics | `industrial-construction-guide.md` | `nsw-industrial-warehouse-cost-breakdown-reference.md` |
| Industrial manufacturing/process | `industrial-construction-guide.md` | `nsw-industrial-process-facility-cost-breakdown-reference.md` |
| Industrial cold-chain | `industrial-construction-guide.md` | `nsw-industrial-cold-chain-cost-breakdown-reference.md` |
| Data centre | `industrial-construction-guide.md` | `nsw-data-centre-cost-breakdown-reference.md` |
| Building rectification | `building-remediation-rectification-guide.md` | `nsw-building-remediation-cost-breakdown-reference.md` |
| Contaminated land | `remediation-due-diligence-guide.md` | Not supported for Cost Plan |
| Advisory | `advisory-services-guide.md` | Construction Cost Plan not applicable |

The Cost Plan capability matrix in
`backend/app/sitewise/cost_plan_coverage.py` is the runtime source of truth for
supported families. A reference file alone does not authorize workflow support.

## Reconciliation and deletion ledger

| Existing file | Decision | Reason / deletion gate |
| --- | --- | --- |
| `new-dwelling-guide.md` | Retain as legacy | Delete only after all legacy-archetype projects and decision-catalog consumers migrate to taxonomy routing. |
| `renovation-guide.md` | Retain as legacy | Same gate; unique renovation decisions still feed compatibility flows. |
| `multi-dwelling-guide.md` | Retain as legacy | Same gate; Class 1 townhouse compatibility remains live. |
| `ancillary-guide.md` | Retain as legacy | Same gate; ancillary archetype compatibility remains live. |
| `small-commercial-guide.md` | Retain as legacy | Delete after `small-commercial` migration and reduced-confidence fallback removal. |
| `mep-residential.md` | Retain, narrowed | It remains the domestic integrated-services overview. Deep scopes route to mechanical, hydraulic, electrical, and ICT/AV/security guides. |
| `structural-residential.md` | Retain | Class 1 footing, framing, wind and BAL detail is not duplicated by a cross-class guide. |
| `civil-residential.md` | Retain | Residential OSD, sewer, crossover and subdivision detail remains distinct. |
| `sustainability-energy-guide.md` | Retain, residential only | BASIX/NatHERS content no longer claims commercial or mixed-use coverage. |
| `commercial-construction-guide.md` | Retain, commercial only | Industrial scope moved to the industrial guide; institution/mixed remain second-pass gaps. |
| `remediation-due-diligence-guide.md` | Retain, contamination only | Building-defect rectification moved to the building-remediation guide. |

No existing seed is safe to delete in this pass. The five legacy archetype files
are still referenced by compatibility code and project templates; the four
residential discipline/topic files contain non-duplicated Class 1 guidance.

## Intentional second-pass gaps

- Retirement living and residential aged care
- Hotel and food-and-beverage commercial work
- Dangerous-goods, pharmaceutical/GMP, cleanroom, battery-manufacturing and
  waste-to-energy industrial work
- Institutional, mixed-use and infrastructure class overlays
- Contaminated-land rate/cost reference

These remain explicit unsupported Cost Plan families until a governed reference,
renderer taxonomy, capability rule and regression fixture are added together.
