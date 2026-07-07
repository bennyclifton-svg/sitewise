# Walsh Terrace Renovation pack

## Follow-on synthetic packages

These files extend the Walsh renovation scenario without changing the original five-document mobilisation fixture:

- `p02-00-pack-additional-fees-correspondence.md` - additional consultant fee proposals and correspondence for PMP / cost-plan updates.
- `p03-00-pack-builder-quotes.md` - three synthetic builder quotes for Tender Comparison Module testing.

The `p02-*` and `p03-*` files are intentionally not numbered `06`, `07`, etc. so automated tests that load the original numbered fixture continue to exercise the same mobilisation baseline.

**Overlays:** `renovation`, `architect-pm`, `NSW`

| File | Suggested path |
| --- | --- |
| `01-engagement-letter-atelier-north.md` | `02-consultant/architect/` |
| `02-fee-proposal-atelier-north.md` | `02-consultant/architect/` |
| `03-owner-project-brief-walsh-house.md` | `00-brief-pmp/` |
| `04-email-builder-preliminary-cost-advice.md` | `05-procurement/` or correspondence |
| `05-email-heritage-advisor-desktop.md` | `03-design/01-due-diligence/` |

**Tests:** No conflict disclosure. Two invited builders. Live occupation. ROM email is **not** formal budget — brief confirms budget.
