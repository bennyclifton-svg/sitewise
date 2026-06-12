#!/usr/bin/env python3
"""Generate benchmarks.seed.csv — the M0 ratio framework + tagged anchors.

DESIGN (PRD §9.7, §11):
  - Ratios and relationships are the durable layer (model knowledge ages well).
  - Absolute anchors are model_seed, confidence low/medium, and MUST be
    recalibrated against ABS/HIA/volume-builder/Rawlinsons data and the QS
    gate before any customer-facing use. The claim-strength rule enforces
    this at report time regardless.
  - All amounts AUD, GST-inclusive (consumer convention), cents in DB but
    dollars here for auditability; loader converts.

Schema: benchmark_key,state,region,build_type,spec_level,metric,
        p25,p50,p75,unit,source,provenance,confidence,effective_date
"""
import csv
from pathlib import Path

DST = Path(__file__).resolve().parent.parent / "benchmarks.seed.csv"
DATE = "2026-06-11"
PROV = "model_seed 2026-06-11; recalibrate per PRD 11.1 before customer use"

# State / region multipliers off Sydney-metro = 1.00 (durable relationships;
# levels uncertain -> low confidence on expanded absolutes).
STATE_MULT = {"NSW": 1.00, "VIC": 0.94, "QLD": 0.96}
REGION_MULT = {"metro": 1.00, "regional": 1.05}  # post-2021 regional labour premium

SPECS = ["builder_base", "mid", "high", "architectural"]

# ---------------------------------------------------------------- base rows
# (key, build_type, spec, metric, p25, p50, p75, unit, conf, expand_by_state)
R = []

def row(key, bt, spec, metric, p25, p50, p75, unit, conf, expand=False):
    R.append(dict(benchmark_key=key, build_type=bt, spec_level=spec,
                  metric=metric, p25=p25, p50=p50, p75=p75, unit=unit,
                  confidence=conf, expand=expand))

# --- Whole-of-build rates (per m2, complete excl. site abnormals/external) --
for spec, (a, b, c) in {"builder_base": (1900, 2200, 2600),
                        "mid": (2500, 2900, 3400),
                        "high": (3300, 3900, 4700),
                        "architectural": (4500, 5500, 7500)}.items():
    row("build.rate", "new_build", spec, "per_m2", a, b, c, "AUD/m2", "low", expand=True)
row("build.reno_premium", "renovation", "ALL", "ratio", 1.2, 1.4, 1.7, "x new-build rate", "medium")
row("build.addition_premium", "addition", "ALL", "ratio", 1.1, 1.25, 1.45, "x new-build rate", "medium")

# --- Group shares of contract (new build, mid spec; durable ratios) ---------
for key, (a, b, c) in {
    "prelim.share": (5.0, 6.5, 8.0), "site.share_flat": (2.0, 3.5, 6.0),
    "sub.share": (8.0, 10.0, 12.0), "frame.share": (10.0, 12.0, 14.0),
    "roof.share": (4.0, 5.5, 7.0), "walls.share": (6.0, 8.0, 10.0),
    "win.share": (4.0, 5.5, 8.0), "svc.share": (10.0, 12.5, 15.0),
    "lining.share": (4.0, 5.0, 6.5), "fix.share": (4.0, 5.5, 7.0),
    "kit.share": (4.0, 6.0, 9.0), "bath.share": (4.0, 6.0, 9.0),
    "paint.share": (2.0, 3.0, 4.0), "floor.share": (2.0, 3.0, 4.5),
    "ext.share": (3.0, 5.0, 8.0), "comm.margin_share": (18.0, 22.0, 28.0),
}.items():
    row(key, "new_build", "mid", "pct_of_build", a, b, c, "% of contract", "medium")

# --- Site & ground (the PS battleground) ------------------------------------
row("site.allowance_lump", "new_build", "ALL", "absolute", 15000, 25000, 40000, "AUD flat A/S block", "low", expand=True)
row("site.piering", "new_build", "ALL", "absolute", 15000, 25000, 45000, "AUD typical dwelling", "low", expand=True)
row("site.cut_fill", "new_build", "ALL", "absolute", 8000, 15000, 30000, "AUD moderate slope", "low", expand=True)
row("site.rock", "new_build", "ALL", "absolute", 5000, 12000, 30000, "AUD allowance", "low")
row("site.retaining", "ALL", "ALL", "absolute", 600, 900, 1400, "AUD/m2 wall face", "medium")
row("site.underpinning", "renovation", "ALL", "absolute", 15000, 30000, 60000, "AUD", "low")
row("sub.slab_upgrade", "new_build", "ALL", "ratio", 1.05, 1.15, 1.45, "x class-A slab (class-specific keys preferred)", "low")
row("sub.slab_upgrade_M", "new_build", "ALL", "ratio", 1.03, 1.06, 1.10, "x class-A slab", "medium")
row("sub.slab_upgrade_H", "new_build", "ALL", "ratio", 1.10, 1.18, 1.30, "x class-A slab", "medium")
row("sub.slab_upgrade_E", "new_build", "ALL", "ratio", 1.25, 1.45, 1.70, "x class-A slab", "low")
row("sub.slab", "new_build", "ALL", "per_m2", 220, 280, 360, "AUD/m2 slab area", "low", expand=True)
row("sub.termite", "new_build", "ALL", "absolute", 1200, 2000, 3500, "AUD", "medium")
row("sub.drop_edge", "new_build", "ALL", "absolute", 4000, 9000, 20000, "AUD sloping site", "low")

# --- Demolition & prep ------------------------------------------------------
row("demo.full_house", "ALL", "ALL", "absolute", 18000, 25000, 38000, "AUD incl. clear", "medium", expand=True)
row("demo.strip_out", "renovation", "ALL", "absolute", 5000, 12000, 25000, "AUD", "low")
row("demo.asbestos", "ALL", "ALL", "absolute", 3000, 7000, 15000, "AUD typical domestic", "low")
row("demo.trees", "ALL", "ALL", "absolute", 1500, 4000, 10000, "AUD", "low")

# --- Prelims, frame, roof, walls, windows -----------------------------------
row("prelim.scaffold", "ALL", "ALL", "absolute", 6000, 12000, 22000, "AUD two-storey", "medium")
row("prelim.soil_report", "ALL", "ALL", "absolute", 600, 1000, 1800, "AUD", "medium")
row("prelim.survey", "ALL", "ALL", "absolute", 1200, 2200, 3500, "AUD", "medium")
row("prelim.energy_assessment", "ALL", "ALL", "absolute", 400, 700, 1200, "AUD", "medium")
row("prelim.engineering", "ALL", "ALL", "absolute", 2500, 4500, 8000, "AUD Class 1", "medium")
row("frame.steel", "ALL", "ALL", "absolute", 5000, 12000, 30000, "AUD where required", "low")
row("roof.metal_vs_tile", "new_build", "ALL", "ratio", 0.95, 1.05, 1.20, "metal x tile cost", "medium")
row("roof.skylights", "ALL", "ALL", "absolute", 1800, 3200, 5500, "AUD each installed", "medium")
row("win.glazing_upgrade", "new_build", "ALL", "pct_of_build", 1.0, 2.0, 3.5, "% of contract", "medium")
row("win.bal", "new_build", "ALL", "pct_of_build", 1.5, 3.0, 6.0, "% uplift BAL29+", "low")
row("garage.door", "ALL", "ALL", "absolute", 2200, 3200, 4800, "AUD sectional+motor", "medium")

# --- Services ---------------------------------------------------------------
row("svc.hot_water", "ALL", "ALL", "absolute", 2000, 3200, 5000, "AUD heat-pump class", "medium")
row("svc.water_tank", "ALL", "ALL", "absolute", 2500, 4000, 6500, "AUD tank+pump", "medium")
row("svc.points", "ALL", "ALL", "absolute", 85, 110, 150, "AUD per point", "medium")
row("svc.ac", "ALL", "ALL", "absolute", 11000, 16000, 26000, "AUD ducted typical", "low", expand=True)
row("svc.heating", "ALL", "ALL", "absolute", 6000, 10000, 16000, "AUD ducted gas/hydronic entry", "low")
row("svc.solar", "ALL", "ALL", "absolute", 5000, 7500, 12000, "AUD 6.6-10kW", "low")
row("svc.security", "ALL", "ALL", "absolute", 1500, 3000, 6000, "AUD", "low")

# --- PC allowances (mid spec realism bands) ---------------------------------
row("appl.package", "ALL", "mid", "absolute", 4000, 6500, 10000, "AUD", "medium")
row("appl.cooktop", "ALL", "mid", "absolute", 700, 1200, 2200, "AUD", "medium")
row("appl.oven", "ALL", "mid", "absolute", 1000, 1800, 3200, "AUD", "medium")
row("appl.rangehood", "ALL", "mid", "absolute", 400, 800, 1600, "AUD", "medium")
row("appl.dishwasher", "ALL", "mid", "absolute", 700, 1100, 1900, "AUD", "medium")
row("appl.lights", "ALL", "mid", "absolute", 1500, 2800, 5000, "AUD whole house", "low")
row("appl.window_furnishings", "ALL", "mid", "absolute", 3000, 6000, 12000, "AUD whole house", "low")
row("kit.benchtop", "ALL", "mid", "absolute", 3500, 6000, 11000, "AUD stone-class", "medium")
row("kit.cabinetry", "ALL", "mid", "absolute", 12000, 18000, 28000, "AUD", "low")
row("kit.splashback", "ALL", "mid", "absolute", 800, 1500, 3000, "AUD", "medium")
row("kit.sink_tap", "ALL", "mid", "absolute", 600, 1100, 2200, "AUD", "medium")
row("kit.butlers", "ALL", "mid", "absolute", 4000, 8000, 15000, "AUD", "low")
row("bath.tapware", "ALL", "mid", "absolute", 800, 1400, 2500, "AUD per bathroom", "medium")
row("bath.vanities", "ALL", "mid", "absolute", 800, 1500, 3000, "AUD each", "medium")
row("bath.baths", "ALL", "mid", "absolute", 700, 1300, 2800, "AUD", "medium")
row("bath.screens", "ALL", "mid", "absolute", 700, 1200, 2200, "AUD each", "medium")
row("bath.toilets", "ALL", "mid", "absolute", 350, 600, 1200, "AUD each", "medium")
row("bath.laundry", "ALL", "mid", "absolute", 800, 1800, 4000, "AUD", "low")
row("bath.wall_tiling", "ALL", "ALL", "absolute", 35, 55, 90, "AUD/m2 tile supply", "medium")
row("floor.tiles", "ALL", "mid", "absolute", 90, 130, 190, "AUD/m2 supplied+laid", "medium")
row("floor.carpet", "ALL", "mid", "absolute", 55, 80, 120, "AUD/m2 supplied+laid", "medium")
row("floor.timber", "ALL", "mid", "absolute", 110, 160, 240, "AUD/m2 supplied+laid", "medium")
row("floor.hybrid", "ALL", "mid", "absolute", 60, 85, 120, "AUD/m2 supplied+laid", "medium")
row("floor.polished_concrete", "ALL", "mid", "absolute", 80, 120, 180, "AUD/m2", "low")

# --- External works ----------------------------------------------------------
row("ext.driveway", "ALL", "ALL", "absolute", 95, 120, 160, "AUD/m2 plain conc.", "medium")
row("ext.driveway_exposed", "ALL", "ALL", "absolute", 130, 165, 210, "AUD/m2 exposed agg", "medium")
row("ext.fencing", "ALL", "ALL", "absolute", 90, 130, 200, "AUD/lm timber/Colorbond", "medium")
row("ext.decks", "ALL", "ALL", "absolute", 350, 550, 900, "AUD/m2", "low")
row("ext.pergolas", "ALL", "ALL", "absolute", 5000, 10000, 20000, "AUD", "low")
row("ext.landscaping", "new_build", "ALL", "pct_of_build", 1.0, 2.5, 5.0, "% of contract", "low")
row("ext.turf", "ALL", "ALL", "absolute", 15, 22, 35, "AUD/m2 supplied+laid", "medium")
row("ext.letterbox_line", "ALL", "ALL", "absolute", 400, 700, 1200, "AUD combined", "medium")

# --- Connections & statutory -------------------------------------------------
row("conn.power", "new_build", "ALL", "absolute", 1500, 3500, 8000, "AUD", "low")
row("conn.water", "new_build", "ALL", "absolute", 1000, 2000, 4000, "AUD", "low")
row("conn.sewer", "new_build", "ALL", "absolute", 1500, 3000, 7000, "AUD", "low")
row("conn.stormwater", "new_build", "ALL", "absolute", 2000, 5000, 15000, "AUD OSD-dependent", "low")
row("conn.gas", "new_build", "ALL", "absolute", 800, 1500, 3000, "AUD where available", "low")
row("conn.nbn", "new_build", "ALL", "absolute", 300, 600, 1500, "AUD", "low")
row("stat.home_warranty", "ALL", "ALL", "pct_of_build", 0.5, 0.9, 1.4, "% of contract [VERIFY state schemes]", "low")
row("stat.certifier", "ALL", "ALL", "absolute", 1800, 3000, 5500, "AUD", "medium")
row("stat.lsl", "ALL", "ALL", "pct_of_build", 0.25, 0.35, 0.55, "% of contract [VERIFY rates]", "low")
row("comm.ps_aggregate", "new_build", "ALL", "pct_of_build", 2.0, 5.0, 10.0, "% of contract; higher invites scrutiny", "medium")
row("comm.margin_variations", "ALL", "ALL", "pct_of_build", 15.0, 20.0, 25.0, "% margin on variations (HIA convention)", "medium")

# Coverage stubs: keys referenced by taxonomy but intentionally priced at QS
# gate (too project-specific for a model seed). Emitted with empty bands so
# the validator sees full key coverage and the QS sheet lists what to price.
STUBS = [
    "prelim.approvals", "prelim.drawings", "prelim.supervision", "demo.trees",
    "sub.subfloor", "sub.suspended_slab", "frame.walls", "frame.roof",
    "frame.upper_floor", "roof.tiles", "roof.metal", "roof.fascia_gutter",
    "walls.brick", "walls.render", "walls.cladding_light", "walls.cladding_premium",
    "win.standard", "win.entry_door", "win.sliders", "svc.plumbing",
    "svc.electrical", "energy.insulation", "energy.compliance_package",
    "lining.plaster", "lining.ceiling_height", "lining.feature", "fix.doors",
    "fix.skirting", "fix.robes", "fix.stairs", "fix.joinery", "bath.floor_tiling",
    "paint.internal", "paint.external", "ext.paths", "ext.pool",
    "stat.contributions", "comm.pc_aggregate", "comm.contingency",
]

def main():
    out = []
    def emit(d, state, region):
        m = STATE_MULT.get(state, 1.0) * REGION_MULT.get(region, 1.0)
        scale = m if (d["metric"] in ("per_m2", "absolute") and state != "ALL") else 1.0
        conf = "low" if (scale != 1.0 and d["confidence"] != "low") else d["confidence"]
        out.append([d["benchmark_key"], state, region, d["build_type"], d["spec_level"],
                    d["metric"],
                    round(d["p25"] * scale, 2), round(d["p50"] * scale, 2),
                    round(d["p75"] * scale, 2), d["unit"], "model_seed", PROV,
                    conf, DATE])
    for d in R:
        if d["expand"]:
            for st in STATE_MULT:
                for rg in REGION_MULT:
                    emit(d, st, rg)
        else:
            emit(d, "ALL", "ALL")
    for key in STUBS:
        out.append([key, "ALL", "ALL", "ALL", "ALL", "absolute", "", "", "",
                    "PRICE AT QS GATE", "model_seed", PROV, "low", DATE])
    with open(DST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["benchmark_key", "state", "region", "build_type", "spec_level",
                    "metric", "p25", "p50", "p75", "unit", "source", "provenance",
                    "confidence", "effective_date"])
        w.writerows(out)
    print(f"{len(out)} benchmark rows -> {DST.name} ({len(STUBS)} QS-gate stubs)")

if __name__ == "__main__":
    main()
