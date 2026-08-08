# Landing page — iteration beats + timestamped transcript — 2026-08-08

Scope: extends `docs/plans/2026-08-06-landing-messaging.md`. That doc set the spine
and the single-phase hero as built. This doc adds a **second dimension to the
story**: the hero currently describes one pass through the system; it needs to
describe the fact that a project throws information at SiteWise continually, and
the artefacts (PMP, cost plan, reports) get rebuilt many times, not issued once.

**Status: copy only, not yet implemented.** The current hero (`frontend/public/landing.html`
`#hero`) is a single scroll-jacked phase (`sw-mark-story` → one `sw-mark-story__copy`
block, one canvas animation, a 4-step rail: Read → Interpret → Run tools → Issue).
There is no second or third phase in the markup for beats 2 and 3 to occupy yet —
that structure is a Claude Design / animation task, downstream of this transcript.
Only beat 1's lede has a real home in the file today (see "What's implemented" below).

The spine is unchanged and still wins on any disagreement:

> **You do the judgement. SiteWise does the assembly.**

## The three beats

Beat 1 establishes the promise. Beat 2 compounds it under design complexity. Beat 3
cashes it in at the moment of decision (tender award). Only beat 3 makes a concrete
claim — beats 1–2 build trust in the capability, beat 3 is where it pays off.

### Beat 1 — the promise

> **You do the judgement. SiteWise does the assembly.**
>
> Drop in the drawings, specs, site notes and invoices as they land. SiteWise reads
> them, files them, and builds the plan, report or comparison you were going to
> write by hand — every detail considered, to shape your next move.

### Beat 2 — the iteration

> **Layer on the detail. More consultants, more design. SiteWise keeps up with your pace.**
>
> As the project evolves, so do the details and complexity. More consultants join,
> more drawings land, more interfaces to align. New information is weighed against
> what's already been decided. SiteWise doesn't tire of that. Two consultants or
> twenty, five drawings or five hundred, a ten-line cost plan or a thousand — it
> re-reads, re-checks and rebuilds every time something changes, staying current
> instead of catching up. Every detail shaping the next move.

### Beat 3 — the payoff (tender pivot)

> **Tender time, and the cheap number isn't always the safe one.**
>
> Every consultant, contractor and trade prices the same scope, and it's rarely
> obvious which quote is complete and which one quietly left something out.
> SiteWise already holds the detail — every drawing, spec and revision that built
> the design — so it checks each tender against that scope, not just against its
> price. Consultants, contractors, trades: one comparison engine, line by line,
> exclusions flagged. Evaluation in moments, grounded and traced.

**Open flag:** beat 3 broadens tender evaluation to consultants and contractors, not
just builders/trades. Confirm that comparison actually runs across all three before
this goes live — the copy is making a real scope claim.

## Timestamped transcript (first-pass pacing, placeholder)

Broken into reveal units at roughly clause/sentence granularity, since the stated
intent is to animate headings and individual lines, not whole paragraphs at once.
**Timings below are a proposed first pass only** — spacing to give each line room to
land, not a decision about animation speed. Claude Design should treat these as a
starting point and re-time against the actual motion, not as fixed marks.

| Time | Beat | Unit | Text |
| --- | --- | --- | --- |
| 0:00 | 1 | H1a | You do the judgement. |
| 0:02 | 1 | H1b | SiteWise does the assembly. |
| 0:05 | 1 | B1a | Drop in the drawings, specs, site notes and invoices as they land. |
| 0:08 | 1 | B1b | SiteWise reads them, files them, and builds the plan, report or comparison you were going to write by hand — |
| 0:12 | 1 | B1c | every detail considered, to shape your next move. |
| 0:16 | 2 | H2a | Layer on the detail. |
| 0:18 | 2 | H2b | More consultants, more design. |
| 0:20 | 2 | H2c | SiteWise keeps up with your pace. |
| 0:23 | 2 | B2a | As the project evolves, so do the details and complexity. |
| 0:26 | 2 | B2b | More consultants join, more drawings land, more interfaces to align. |
| 0:30 | 2 | B2c | New information is weighed against what's already been decided. SiteWise doesn't tire of that. |
| 0:34 | 2 | B2d | Two consultants or twenty, five drawings or five hundred, a ten-line cost plan or a thousand — |
| 0:38 | 2 | B2e | it re-reads, re-checks and rebuilds every time something changes, staying current instead of catching up. |
| 0:42 | 2 | B2f | Every detail shaping the next move. |
| 0:46 | 3 | H3 | Tender time, and the cheap number isn't always the safe one. |
| 0:50 | 3 | B3a | Every consultant, contractor and trade prices the same scope, and it's rarely obvious which quote is complete and which one quietly left something out. |
| 0:55 | 3 | B3b | SiteWise already holds the detail — every drawing, spec and revision that built the design — |
| 0:58 | 3 | B3c | so it checks each tender against that scope, not just against its price. |
| 1:02 | 3 | B3d | Consultants, contractors, trades: one comparison engine, line by line, exclusions flagged. |
| 1:06 | 3 | B3e | Evaluation in moments, grounded and traced. |

Total run ~1:10 across three beats, ~20–25s each. Adjust freely — the unit IDs
(H1a, B2c, etc.) are the stable handles for mapping animation keyframes, independent
of whatever timing ends up used.

## What's implemented vs. deferred

- **Implemented nowhere yet.** No file has been edited as part of this doc. Beat 1's
  ending clause (`with every line still pointing back at the document it came
  from` → `every detail considered, to shape your next move`) is a pending edit to
  `frontend/public/landing.html` lines 69–74, held until beats 2–3 have somewhere to
  go so the hero isn't shipped half-updated.
- **Deferred to animation build:** restructuring `#hero` from one phase to three,
  the mark-rail/canvas treatment for beats 2–3, and actual reveal timing.
