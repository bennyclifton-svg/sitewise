# Prompt 2 — owner corrects the profile

The point of this step is that **the profile is corrected, not filled in**. Some of it is
done by hand in the taxonomy picker and scale fields; one part is typed into chat.

---

## By hand, in the profile panel

| Field | Change | Why it matters on screen |
|---|---|---|
| Site address | → `41 Georgina Street, Newtown NSW 2042` | Was empty. User supplies it. |
| Storeys | confirm `2` | Agent got this right — confirming is a distinct gesture from correcting. |
| Bedrooms | → `4` | Was empty. |
| GFA | → `175` m² | Was empty. |
| Garage spaces | → `0` | Newtown semi, no off-street parking. A deliberate zero, not a blank. |

## Typed into chat

> Add a plunge pool in the rear courtyard, about 12 square metres. Site is 232 square
> metres, 6.4 metre frontage. The semi is attached on the eastern side to number 43.

---

## What this should do

- Add one `accommodation_space` row: **Plunge Pool · External · 12 m² · New**
- Record the party wall / attached-boundary fact, which the structural and planning scopes
  later depend on
- Leave everything else alone

## Accommodation schedule after this step — five rows

| Space | Level | Area | Characteristics | Status |
|---|---|---|---|---|
| Master Bedroom | First | TBC | TBC | New |
| Parents' Retreat | First | TBC | TBC | New |
| Kitchen | Ground | TBC | TBC | New |
| Living / Dining | Ground | TBC | open plan | New |
| Plunge Pool | External | 12 m² | rear courtyard | New |

**Scheduled area: 12 m²** — because it is the only row with a parseable area. That is a
genuinely good frame: the total is honest about how little it currently knows.

## The capture

The plunge pool row appearing is the "you do the judgement" beat in miniature. The system
built the profile; the owner knew about the pool. Neither could have done it alone.
