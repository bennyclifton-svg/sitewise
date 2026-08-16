# Prompt 3 — after the brief lands

Upload [`01-brief/owners-project-brief.md`](../01-brief/owners-project-brief.md) first. Let it
route and settle. **Then wait a beat before typing** — the animation wants the moment where a
document sits there and nothing has happened yet.

---

> The owners have issued their brief. Pull the accommodation schedule out of it and update
> the project.

---

## What should happen

The accommodation schedule goes from **5 rows to 26**, of which 21 count toward the total.

| | Before | After |
|---|---|---|
| Rows | 5 | 26 |
| Rows with a parseable area | 1 | 26 |
| Demolished rows captured | 0 | 5 |
| External spaces captured | 1 | 4 |
| **Scheduled area** | 12 m² | **261 m²** |

### The four things worth watching

1. **Demolished spaces get recorded, not deleted.** The 1980s kitchen, bathroom, laundry,
   rear sitting room and verandah all land as rows with status `Demolished`. They are part
   of the scope — someone has to price removing them — but they are excluded from the
   scheduled-area total. A schedule that only lists what is being built is a schedule that
   loses the demolition scope.

2. **External spaces get recorded.** Covered deck, rear courtyard, plunge pool, side
   passage. The agent instruction calls this out explicitly, because the failure mode is
   treating "space" as "room".

3. **Scheduled area ≠ GFA.** The footer reads **261 m²**. The GFA is **175 m²**. The
   difference is the 86 m² of external space. The schedule does not pretend to be a floor
   area calculation and should not be reconciled against the profile's `gfa_sqm`.

4. **`TBC` survives.** Walk-in robe, bedroom 3, understair store, stair and landing all have
   an area but `TBC` characteristics, because the brief gives areas without describing them.
   Nothing invents a description to fill the cell.

---

## Then run Update PMP

The brief is new evidence against the existing baseline. What should move:

| Section | Change |
|---|---|
| Accommodation Schedule | 5 rows → 26, scheduled area 261 m² |
| Brief / scope | Party wall, drainage, unknown footings, access constraints now evidenced |
| FFE Schedule | Kitchen appliances, tapware finish, flooring, lighting intent recorded as owner preferences |
| Risks | Existing footings unknown, party wall, rear drainage, heritage setback, neighbour notification |
| Cost planning | $950,000 ceiling recorded; plunge pool flagged as the owner's first de-scope |
| Programme | January 2027 site start; owner paying rent during construction |

## What should **not** move

The consultant table. As of this step nobody has been appointed — the fee proposals arrive
in step 9 and the appointments in step 11. A brief from the owner is not engagement
evidence for a consultant.

If the consultant rows flip to appointed off the back of this document, that is a defect
worth catching before capture.

---

## The frame

The schedule expanding is the single best argument in the whole exercise, and it is
completely legible without narration: one column of five sparse rows, mostly `TBC`, becomes
a full schedule with a real total. That is a sketch becoming a brief.
