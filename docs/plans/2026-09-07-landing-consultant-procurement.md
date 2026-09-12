# Consultant procurement landing animation

The fifth project-navigation item now opens the consultant procurement scene, after
PMP, Cost Plan and Program in the demo loop. It reuses the existing shared shell,
word-by-word prompt, blue preparation outline, accumulated source selection,
subdued skeleton bars, staggered headings, row fades and seven-second result hold.
The register opens the civil/stormwater RFP, reveals its sections, then returns the
reading position to Services and deliverables. Manual inspection pauses playback.

## Saved content

Read from the configured canonical project database on 7 September 2026. The project
is Seven Hills Townhouse, `4d08f12a-78bb-4832-ab68-60f49d3a2538`. Its fictional status
is explicit in `docs/demo-corpus/seven-hills/README.md`; names, addresses, financial
figures and project documents in that corpus are fabricated demonstration evidence.

| RFP | Saved draft ID | Version |
| --- | --- | --- |
| Civil / stormwater engineer | `29e8f795-8bb7-408b-87c8-8edd4ec9def2` | 1 |
| Architect | `16f160dd-13c3-4027-81dd-1f34f1231402` | 1 |
| Electrical Services Engineer | `73964073-9c26-44e5-8708-0da5ca44f9b3` | 1 |
| Hydraulic engineer | `1a0076cf-5294-4bb0-a5ff-e77143ef5f8c` | 1 |

The civil draft was last updated on 27 August 2026 at 10:48:46 UTC. Export-body SHA-256:
`196738e3e96bf833e4ccb43d38509bdecb77f3febcd02a7c5b6f7ae46813a48b`.

The four `.md` files in `frontend/public/landing-assets/` preserve the saved wording,
dates, programme snapshot, fee stages, transmittal and source key. Only internal
`clerk:block` markers and the export-excluded Trace & QA section were removed.
The civil draft contains Programme v73; the earlier programme animation preserves
its separately supplied screenshot. These are intentionally different saved states.

The actual database contained these four generated RFPs, so only those four receive
draft icons and repository entries. Town planning and structural remain unissued
register rows. No replacement RFPs, proposals, firms, appointments or issue events
were invented to fill the initial five-discipline storyboard.

## Implementation

- `landing-procurement.js` owns the register, draft reader and procurement timeline.
- `landing-procurement.css` follows ProcurementStrategyGrid and ProcurementRequestPanel.
- `scripts/build-landing-rfp.mjs` converts the saved Markdown to escaped static section
  markup in `landing-rfp-data.js`. Run it from `frontend` after replacing captured files.
- Other RFPs render on demand. Civil is the automatic focus; every saved draft can
  be opened, copied or downloaded as Markdown. Citations open the draft's own key.
- The shared controller handles cancellation, replay, reduced motion and visibility.
  Automatic scrolling allows its layout/scroll transitions to settle; wheel, touch
  and keyboard inspection still pause immediately.

This is a local, synthetic animation. No project database writes, issue messages,
appointments or deployment are part of this change.

## Verification

Focused Vitest coverage includes source accumulation, phased register/draft creation,
the exact seven civil scope clauses, captured schedule and fee stages, citation keys,
individual draft navigation, replay/cancellation, reduced motion and offscreen pause.
The shared PMP and controls suites remain covered. Typecheck and lint pass.
Browser verification at desktop and 390px mobile confirmed automatic completion,
the final scope reading position, no RFP/page horizontal overflow and no console errors.
