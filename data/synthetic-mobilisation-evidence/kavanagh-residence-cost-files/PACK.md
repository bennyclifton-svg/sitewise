# Kavanagh Residence — synthetic cost-file pack

**Status:** Synthetic test data only. Every person, entity, ABN, address, account reference, amount, and transaction in this folder is fabricated. Do not use for payment, tax, procurement, or legal purposes.

## Purpose

This pack exercises fee-proposal extraction, GST handling, invoice classification, stage-to-invoice reconciliation, and contract-progress analysis for a single Australian residential project.

**Project:** Kavanagh Residence — new detached dwelling and external works
**Site:** 8 Paperbark Lane, Northbridge NSW 2063
**Client:** Kavanagh Property Holdings Pty Ltd as trustee for the Kavanagh Family Trust (synthetic ABN 39 000 000 270)

## Documents

| Entity | Discipline | Fee proposal / contract value, ex GST | Invoices |
| --- | --- | ---: | --- |
| Quoin Architecture Pty Ltd | Architect | $96,000.00 | 5 |
| Catenary Structures Pty Ltd | Structural and civil engineer | $41,800.00 | 5 |
| Flowline Hydraulics Pty Ltd | Hydraulic services engineer | $32,500.00 | 5 |
| Vertex Cost Advisory Pty Ltd | Quantity surveyor / cost consultant | $45,000.00 | 5 |
| Ironbark Main Works Pty Ltd | Main works contractor | $1,234,000.00 | 5 |

All base professional fees and the base works contract reconcile to their related progress invoices before GST. The architect's and hydraulic engineer's invoice totals include separately identified GST-free statutory disbursements, which are excluded from their agreed professional fee totals.

## Suggested filing paths

| File group | Suggested project workspace path |
| --- | --- |
| `01`–`05` fee proposals / building proposal | `02-consultant/fees-and-appointments/` and `04-construction/tender-and-contract/` |
| `11`–`15` architect invoices | `05-commercial/invoices/architect/` |
| `21`–`25` structural invoices | `05-commercial/invoices/structural/` |
| `31`–`35` hydraulic invoices | `05-commercial/invoices/hydraulic/` |
| `41`–`45` cost consultant invoices | `05-commercial/invoices/cost-consultant/` |
| `51`–`55` contractor invoices | `05-commercial/invoices/main-works/` |

## Deliberate test conditions

- The four consultants use the same three-stage structure, but bill it over five invoices by splitting Detailed Design and Construction Services.
- The contractor's building proposal uses five construction stages: substructure/slab, framing, envelope and lock-up, internal fit-out, and completion.
- Some documents call the same activity by a near synonym: "Design Development" vs "Detailed Design", and "Envelope and Lock-up" vs "Lock-up".
- Architect invoice `12` includes a GST-free planning-portal disbursement. Hydraulic invoice `33` includes a GST-free authority enquiry disbursement. Neither is part of the agreed professional fee.
- Structural invoice `23` has a 30-day payment term, while that proposal's standard term is 14 days.
- Contractor invoice `54` refers to a revised payment schedule, but the original building proposal remains the only contract document in this pack.
- All amounts are AUD. Proposal and invoice headers state their GST basis explicitly; line calculations reconcile.

## Expected comparison posture

The extraction should identify five different suppliers and roles, separate consultant fees from construction cost, retain GST-free disbursements as pass-through charges, and match invoices to the relevant proposal stages without treating the invoice-term variation or contractor schedule reference as a new contract.
