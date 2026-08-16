# Prompt 5 — FFE extraction from product data

Upload the three documents in [`05-product-data/`](../05-product-data/). Then run these as
three separate turns so each extraction is its own capture.

---

## 5a · Kitchen appliances

> The Milette data sheet is in. Add the oven, microwave, cooktop, rangehood and dishwasher
> to the FFE schedule with their SKUs and models.

**Expected rows**

| Item | Location | Qty | Finish | Status | Notes |
|---|---|---|---|---|---|
| Oven — Milette MO-760-PY | Kitchen | 1 | Brushed stainless | Selected | 760 mm pyrolytic, Series 7 |
| Combi steam microwave — Milette MC-450-CS | Kitchen | 1 | Brushed stainless | Selected | Stacks above MO-760-PY, combined cut-out 1,040 mm |
| Induction cooktop — Milette MI-900-4Z | Kitchen | 1 | Black ceramic glass | Selected | 900 mm, 4 zone, dedicated 32 A circuit |
| Rangehood — Milette MR-900-UM | Kitchen | 1 | Brushed stainless | Selected | Undermount, ducted only, 150 mm duct |
| Dishwasher — Milette MD-600-IN | Kitchen | 1 | Custom panel — not supplied | Selected | Fully integrated, panel by joiner |

Two facts in that sheet change other trades and should not be lost: the cooktop needs a
**dedicated 32 A circuit**, and the rangehood is **ducted only — no recirculation**.

---

## 5b · Lighting

> Pull the light fittings out of the Lumenaire catalogue and add them to the FFE schedule.

**Expected rows**

| Item | Location | Qty | Finish | Status | Notes |
|---|---|---|---|---|---|
| Downlight — Lumenaire LM-DL90-TW | Throughout | TBC | Matt white | Selected | 90 mm cut-out, tuneable white, IP44 |
| Adjustable spotlight — Lumenaire LM-SP12-AD | Ground floor | TBC | Matt white | Selected | Gimbal, CRI 97 — owner preference over fixed downlights |
| LED strip — Lumenaire LM-ST24-IP | Kitchen overheads, stair | TBC | — | Selected | 24 V, driver required, max 5 m per feed |
| Wall light — Lumenaire LM-WL18-BR | Master Bedroom | 2 | Brushed brass | Selected | Up/down, either side of bed |
| External wall light — Lumenaire LM-XL30-EX | Covered Deck, Side Passage | 2 | Charcoal | Selected | IP65 |

Quantities stay `TBC` — the catalogue gives products, not a count. Only the wall lights and
external lights have quantities, because the **owner's brief** states them ("either side of
the bed", "at the deck and the side passage door"). Anything else counted is invented.

The owner's brief also says **no downlights in the bedrooms**. That belongs on the schedule
as a note, not silently dropped.

---

## 5c · Air conditioning

> Add the Kuroda ducted system to the FFE schedule.

**Expected row**

| Item | Location | Qty | Finish | Status | Notes |
|---|---|---|---|---|---|
| Ducted reverse cycle — Kuroda KCS-MS71-R32 | Whole dwelling | 1 | — | Selected | 7.1 kW cooling / 8.0 kW heating, R32, 2 zones, 48 dB(A) at 1 m |

The **48 dB(A)** figure is the one that matters. The owner's brief says the condenser must
not annoy No. 43, and the data sheet flags a boundary noise assessment where a neighbouring
window is within 3 m. That is a risk register entry, not just an FFE note.

---

## The check across all three

These are **product catalogues, not orders**. Nothing in them says how many downlights the
house needs or which finish was chosen. The right behaviour is to record the product,
record the specification, and leave quantity and finish `TBC` unless the owner's brief
supplies them.

If quantities appear for the downlights or the LED strip, something invented them.
