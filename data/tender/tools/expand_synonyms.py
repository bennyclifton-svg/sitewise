#!/usr/bin/env python3
"""Expand synonyms.base.csv -> synonyms.seed.csv with deterministic variants.

Variants are meaningful for T0 exact/fuzzy matching, not noise:
  - "&" <-> "and"
  - hyphen <-> space
  - plural toggle on the final word (conservative)
  - curated spelling/usage pairs (AU construction vernacular)
  - "supply & install / supply and lay" prefixes for coverings & fixtures
Dedupe on normalised form. Output is sorted and stable for clean diffs.
"""
import csv, re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC, DST = HERE / "synonyms.base.csv", HERE / "synonyms.seed.csv"

PAIRS = [
    ("colorbond", "colourbond"), ("aircon", "air con"),
    ("downlights", "down lights"), ("gyprock", "plaster board"),
    ("benchtop", "bench top"), ("splashback", "splash back"),
    ("rangehood", "range hood"), ("hot water system", "HWS"),
    ("air conditioning", "A/C"), ("power points", "powerpoints"),
    ("flyscreens", "fly screens"), ("set-out", "setout"),
    ("rough-in", "rough in"), ("fit-off", "fit off"),
    ("walk-in", "walk in"), ("built-in", "built in"),
]
# cells where "supply & install"-style prefixes are how quotes actually read
PREFIX_CELLS = {
    "17.01", "17.02", "17.03", "17.04", "15.01", "15.02", "14.02", "14.03",
    "18.06", "19.05", "11.01", "11.02", "06.01", "06.02", "07.03",
}
PREFIXES = ["supply & install", "supply and install", "supply & lay", "supply and fix"]

def norm(p: str) -> str:
    return re.sub(r"\s+", " ", p.strip().lower())

def variants(phrase: str):
    out = {phrase}
    for a, b in (("&", "and"), ("and", "&")):
        if f" {a} " in phrase:
            out.add(phrase.replace(f" {a} ", f" {b} "))
    for p in list(out):
        if "-" in p:
            out.add(p.replace("-", " "))
    for p in list(out):  # conservative plural toggle on last word
        words = p.split()
        last = words[-1]
        if last.isalpha() and len(last) > 3:
            if last.endswith("s") and not last.endswith("ss"):
                out.add(" ".join(words[:-1] + [last[:-1]]))
            elif not last.endswith(("s", "y", "x")):
                out.add(" ".join(words[:-1] + [last + "s"]))
    for a, b in PAIRS:
        for p in list(out):
            if a in p:
                out.add(p.replace(a, b))
            if b in p:
                out.add(p.replace(b, a))
    return out

def main():
    rows, seen = [], set()
    with open(SRC, newline="") as f:
        base = [(r["cell_code"], r["phrase"]) for r in csv.DictReader(f)]
    for code, phrase in base:
        vs = variants(phrase)
        if code in PREFIX_CELLS:
            for v in list(vs):
                for pre in PREFIXES:
                    vs.add(f"{pre} {v}")
        for v in vs:
            key = (code, norm(v))
            if key not in seen:
                seen.add(key)
                src = "seed" if norm(v) == norm(phrase) else "seed_expanded"
                rows.append((code, v, src))
    rows.sort()
    with open(DST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell_code", "phrase", "source"])
        w.writerows(rows)
    print(f"{len(base)} base -> {len(rows)} seed rows -> {DST.name}")

if __name__ == "__main__":
    main()
