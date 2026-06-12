#!/usr/bin/env python3
"""Cross-reference integrity for data/tender seeds. Run in CI."""
import csv, sys, yaml
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
errors = []

tax = yaml.safe_load(open(HERE / "taxonomy.yaml"))
cells = tax["cells"]
codes = {c["code"] for c in cells}
if len(codes) != len(cells):
    errors.append("duplicate taxonomy codes")
groups = set(tax["groups"])
for c in cells:
    if c["code"][:2] not in groups:
        errors.append(f"cell {c['code']} has no group")
    for p in c.get("bp", []):
        if p not in codes:
            errors.append(f"orphan bundling parent {p} in {c['code']}")
    if c.get("stage") not in {"prelim","base","lockup","fixing","completion","external","statutory"}:
        errors.append(f"bad stage in {c['code']}")
tax_bks = {c["bk"] for c in cells if "bk" in c}

exp = yaml.safe_load(open(HERE / "expectations.yaml"))["rules"]
rule_codes = [r["rule"] for r in exp]
if len(rule_codes) != len(set(rule_codes)):
    errors.append("duplicate rule codes")
for r in exp:
    if r["cell"] not in codes:
        errors.append(f"rule {r['rule']} -> orphan cell {r['cell']}")

syn = list(csv.DictReader(open(HERE / "synonyms.seed.csv")))
syn_orphans = {s["cell_code"] for s in syn} - codes
if syn_orphans:
    errors.append(f"synonym orphan codes: {sorted(syn_orphans)}")
norms = [(s["cell_code"], s["phrase"].strip().lower()) for s in syn]
if len(norms) != len(set(norms)):
    errors.append("duplicate synonym (cell, phrase) pairs")
cells_without_syn = codes - {s["cell_code"] for s in syn}
if cells_without_syn:
    errors.append(f"cells with zero synonyms: {sorted(cells_without_syn)}")

bm = list(csv.DictReader(open(HERE / "benchmarks.seed.csv")))
bm_keys = {b["benchmark_key"] for b in bm}
bm_stable_keys = [
    (
        b["benchmark_key"],
        b["state"],
        b["region"],
        b["build_type"],
        b["spec_level"],
        b["metric"],
    )
    for b in bm
]
if len(bm_stable_keys) != len(set(bm_stable_keys)):
    errors.append("duplicate benchmark stable keys")
missing = tax_bks - bm_keys
if missing:
    errors.append(f"taxonomy benchmark_keys with no benchmark row: {sorted(missing)}")
for b in bm:
    if b["p25"] and b["p50"] and b["p75"]:
        if not (float(b["p25"]) <= float(b["p50"]) <= float(b["p75"])):
            errors.append(f"non-monotonic percentiles: {b['benchmark_key']}/{b['state']}")
    if b["confidence"] not in ("low", "medium", "high"):
        errors.append(f"bad confidence: {b['benchmark_key']}")

rl = yaml.safe_load(open(HERE / "report_language.yaml"))
for s in ("excluded_explicit","silent_ambiguous","bundled","ps","pc","included","not_required"):
    if s not in rl["status_phrases"]:
        errors.append(f"missing status phrase: {s}")

if errors:
    print("FAIL"); [print(" -", e) for e in errors]; sys.exit(1)
print(f"OK: {len(cells)} cells | {len(exp)} rules | {len(syn)} synonyms "
      f"({len(cells_without_syn)} uncovered cells) | {len(bm)} benchmark rows "
      f"| taxonomy bk coverage complete")
