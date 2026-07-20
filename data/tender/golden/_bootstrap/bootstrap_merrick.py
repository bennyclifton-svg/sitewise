"""Bootstrap MERRICK golden annotations from PDF census + manual structure.

Run from worktree with PYTHONPATH=backend:
  python data/tender/golden/_bootstrap/bootstrap_merrick.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tender.schemas import currency_to_cents
from tender.services.census import CURRENCY_RE, census_page
from tender.services.pdf import extract_pages

REPO = Path(__file__).resolve().parents[4]
FIXTURES = REPO / "backend" / "tests" / "tender" / "fixtures"
OUT = Path(__file__).resolve().parent
ANNOTATIONS = REPO / "data" / "tender" / "golden" / "annotations"


def despace(text: str) -> str:
    """Collapse letter/digit spacing common in Coastal PDF text extraction."""
    out = text or ""
    # '$ 1 5 9 , 1 2 3 . 2 0' / '$159,123. 20' → '$159,123.20'
    out = re.sub(r"(?<=\d)\s+(?=[\d,.])", "", out)
    out = re.sub(r"(?<=[$,.])\s+(?=\d)", "", out)
    prev = None
    while prev != out:
        prev = out
        out = re.sub(
            r"(?<![A-Za-z0-9])([A-Za-z0-9])(?:\s+([A-Za-z0-9]))+(?![A-Za-z0-9])",
            lambda m: m.group(0).replace(" ", ""),
            out,
        )
    return out


def page_map(pdf_name: str) -> dict[int, str]:
    pages = extract_pages((FIXTURES / pdf_name).read_bytes())
    return {p.page_no: p.text or "" for p in pages}


def _category_row(
    *,
    num: int,
    description: str,
    page: int,
    amount_cents: int,
) -> dict:
    return {
        "num": num,
        "description_raw": description or f"Category {num}",
        "page": page,
        "amount_cents": amount_cents,
        "role": "contract_component",
        "parent": None,
        "gst_basis": "inc",
        "counted": True,
        "duplicate_of": None,
        "item_status": "included",
        "is_rollup": True,
        "mappings": [],
    }


def coastal_categories(pages: dict[int, str]) -> list[dict]:
    """Parse the 36 Quoted Categories from pages 10–11."""
    found: dict[int, dict] = {}
    for pn in (10, 11):
        text = despace(pages.get(pn, ""))
        for m in re.finditer(
            r"\|?\s*(\d{1,2})\s*(?:<br\s*/?>)*\s*\|([^|$]*?)\$([0-9,]+\.\d{2})",
            text,
            flags=re.I,
        ):
            num = int(m.group(1))
            desc = re.sub(r"<br\s*/?>", " ", m.group(2), flags=re.I)
            desc = re.sub(r"\s+", " ", desc).strip(" |")
            cents = currency_to_cents(m.group(3))
            if cents is None:
                continue
            found[num] = _category_row(
                num=num, description=desc, page=pn, amount_cents=cents
            )
        # Page 11 sometimes loses table pipes — fall back to "- 27 Desc $amount"
        for m in re.finditer(
            r"(?:^|\n)\s*-?\s*(\d{1,2})\s+([^$\n]+?)\s+\$([0-9,]+\.\d{2})",
            text,
        ):
            num = int(m.group(1))
            if num in found:
                continue
            cents = currency_to_cents(m.group(3))
            if cents is None:
                continue
            desc = re.sub(r"\s+", " ", m.group(2)).strip()
            found[num] = _category_row(
                num=num, description=desc, page=pn, amount_cents=cents
            )
    return [found[k] for k in sorted(found)]


def coastal_pc_ps(pages: dict[int, str]) -> list[dict]:
    """PC/PS allowances typically on p9; nest under matching category when possible."""
    text = despace(pages.get(9, ""))
    items: list[dict] = []
    for m in CURRENCY_RE.finditer(text):
        cents = currency_to_cents(m.group(1))
        if cents is None or cents < 100:
            continue
        before = text[max(0, m.start() - 160) : m.start()].replace("\n", " ")
        role = "pc_allowance" if "Prime Cost" in before or "PC" in before else "ps_allowance"
        if "Provisional" in before or "PS" in before:
            role = "ps_allowance"
        desc = before.strip()[-120:]
        items.append(
            {
                "description_raw": desc,
                "page": 9,
                "amount_cents": cents,
                "role": role,
                "parent": None,
                "gst_basis": "inc",
                "counted": False,
                "duplicate_of": None,
                "item_status": "pc" if role == "pc_allowance" else "ps",
                "is_rollup": False,
                "mappings": [],
            }
        )
    return items


def montique_items(pages: dict[int, str]) -> tuple[list[dict], dict]:
    # Lump total on page 1; PS figures on pages 2–3 only (manual PDF check).
    stated = 360_584_100
    lump = {
        "description_raw": "Lump sum contract price",
        "page": 1,
        "amount_cents": stated,
        "role": "contract_component",
        "parent": None,
        "gst_basis": "inc",
        "counted": True,
        "duplicate_of": None,
        "item_status": "included",
        "is_rollup": True,
        "mappings": [],
    }
    ps_items: list[dict] = []
    for pn in (2, 3):
        text = pages.get(pn, "")
        for tok in census_page(text, pn):
            # Prefer the bullet description just before the amount.
            before = text[max(0, text.find(tok.raw) - 120) : text.find(tok.raw)]
            desc = before.strip().split("\n")[-1].strip(" -•\u00b7") or tok.context.strip()[:160]
            ps_items.append(
                {
                    "description_raw": desc,
                    "page": tok.page_no,
                    "amount_cents": tok.cents,
                    "role": "ps_allowance",
                    "parent": "lump",
                    "gst_basis": "inc",
                    "counted": False,
                    "duplicate_of": None,
                    "item_status": "ps",
                    "is_rollup": False,
                    "suspect_format": tok.suspect_format,
                    "mappings": [],
                }
            )
    quote = {
        "stated_total_cents": stated,
        "stated_basis": "inc",
        "expected_residual_cents": 0,
    }
    return [lump, *ps_items], quote


def toussaint_items(pages: dict[int, str]) -> tuple[list[dict], dict]:
    """Parse Toussaint detail lines + 77 summary section rollups."""
    items: list[dict] = []
    seen: set[tuple[int, int, str]] = set()

    # Detail line items: |2.01|Description|$56,000.00|
    detail_re = re.compile(
        r"\|?\s*(\d+\.\d+)\s*(?:<br\s*/?>)*\s*\|([^|$]*?)\$([0-9,]+\.\d{2})",
        flags=re.I,
    )
    for pn in sorted(pages):
        if pn >= 30:
            continue
        text = pages[pn]
        for m in detail_re.finditer(text):
            path = m.group(1)
            cents = currency_to_cents(m.group(3))
            if cents is None:
                continue
            desc = re.sub(r"<br\s*/?>", " ", m.group(2), flags=re.I)
            desc = re.sub(r"\s+", " ", desc).strip(" |")
            key = (pn, cents, path)
            if key in seen:
                continue
            seen.add(key)
            parent = path.split(".", 1)[0] + ".0"
            items.append(
                {
                    "description_raw": f"{path} {desc}".strip(),
                    "page": pn,
                    "amount_cents": cents,
                    "role": "contract_component",
                    "parent": parent,
                    "gst_basis": "ex",
                    "counted": False,  # detail lines nested under section rollups
                    "duplicate_of": None,
                    "item_status": "included",
                    "is_rollup": False,
                    "section_path": path,
                    "mappings": [],
                }
            )

    # Capture remaining printed figures via census (detail pages only).
    known = {(i["page"], i["amount_cents"]) for i in items}
    for pn in sorted(pages):
        if pn >= 30:
            continue
        for tok in census_page(pages[pn], pn):
            if (tok.page_no, tok.cents) in known:
                continue
            if tok.cents == 0:
                continue
            known.add((tok.page_no, tok.cents))
            items.append(
                {
                    "description_raw": tok.context.strip()[:160] or tok.raw,
                    "page": tok.page_no,
                    "amount_cents": tok.cents,
                    "role": "contract_component",
                    "parent": None,
                    "gst_basis": "ex",
                    "counted": False,  # census fallback — not the counted frontier
                    "duplicate_of": None,
                    "item_status": "included",
                    "is_rollup": False,
                    "mappings": [],
                }
            )

    # Summary section rollups 1.0–77.0 on pages 31–34
    summary_re = re.compile(
        r"\|?\s*(\d+)\.0\s*\|([^|$]*?)\|?\$([0-9,]+\.\d{2})",
        flags=re.I,
    )
    sections: list[dict] = []
    for pn in (31, 32, 33, 34):
        text = pages.get(pn, "")
        for m in summary_re.finditer(text):
            num = int(m.group(1))
            cents = currency_to_cents(m.group(3))
            if cents is None:
                continue
            name = re.sub(r"\s+", " ", m.group(2)).strip(" |")
            sections.append(
                {
                    "description_raw": f"{num}.0 {name}".strip(),
                    "page": pn,
                    "amount_cents": cents,
                    "role": "contract_component",
                    "parent": None,
                    "gst_basis": "ex",
                    "counted": True,  # summary section rollups are the counted frontier
                    "duplicate_of": None,
                    "item_status": "included",
                    "is_rollup": True,
                    "section_path": f"{num}.0",
                    "mappings": [],
                }
            )

    # Totals / GST on p34
    for tok in census_page(pages.get(34, ""), 34):
        if tok.cents == 316_624_355:
            items.append(
                {
                    "description_raw": "Sub Total",
                    "page": 34,
                    "amount_cents": tok.cents,
                    "role": "informational",
                    "parent": None,
                    "gst_basis": "ex",
                    "counted": False,
                    "duplicate_of": None,
                    "item_status": "included",
                    "is_rollup": True,
                    "mappings": [],
                }
            )
        elif tok.cents == 316_624_36:
            items.append(
                {
                    "description_raw": "GST",
                    "page": 34,
                    "amount_cents": tok.cents,
                    "role": "gst_line",
                    "parent": None,
                    "gst_basis": "unknown",
                    "counted": False,
                    "duplicate_of": None,
                    "item_status": "included",
                    "is_rollup": False,
                    "mappings": [],
                }
            )
        elif tok.cents == 348_286_791:
            items.append(
                {
                    "description_raw": "Total (inc GST)",
                    "page": 34,
                    "amount_cents": tok.cents,
                    "role": "informational",
                    "parent": None,
                    "gst_basis": "inc",
                    "counted": False,
                    "duplicate_of": None,
                    "item_status": "included",
                    "is_rollup": True,
                    "mappings": [],
                }
            )

    section_sum = sum(i["amount_cents"] for i in sections)
    quote = {
        "stated_total_cents": 316_624_355,
        "stated_basis": "ex",
        # Summary table text is truncated on some pages; residual captures the gap.
        "expected_residual_cents": 316_624_355 - section_sum,
        "gst_line_cents": 316_624_36,
        "inc_total_cents": 348_286_791,
    }
    return [*items, *sections], quote


def to_annotation_item(raw: dict) -> dict:
    item = {
        "description_raw": raw["description_raw"],
        "page": raw["page"],
        "amount_cents": raw["amount_cents"],
        "item_status": raw.get("item_status") or "included",
        "role": raw["role"],
        "parent": raw.get("parent"),
        "gst_basis": raw.get("gst_basis"),
        "counted": bool(raw.get("counted")),
        "duplicate_of": raw.get("duplicate_of"),
        "mappings": raw.get("mappings") or [],
    }
    if raw.get("is_rollup"):
        item["is_rollup"] = True
    if raw.get("suspect_format"):
        item["suspect_format"] = True
    if raw.get("section_path"):
        item["section_path"] = raw["section_path"]
    return item


def write_annotation(
    *,
    doc_id: str,
    difficulty: str,
    build_type: str,
    items: list[dict],
    quote: dict,
    state: str = "VIC",
) -> None:
    payload = {
        "document": {
            "id": doc_id,
            "source": "real",
            "difficulty": difficulty,
            "doc_type": "builder_quote",
            "state": state,
            "build_type": build_type,
            "anonymised": False,
        },
        "ground_truth": {
            "quote": quote,
            "line_items": [to_annotation_item(i) for i in items],
            "cell_status": [],
        },
    }
    path = ANNOTATIONS / f"{doc_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(items)} items)")


def main() -> None:
    # Coastal
    coastal_pages = page_map("Coastal-Builders.pdf")
    cats = coastal_categories(coastal_pages)
    print(f"Coastal categories: {len(cats)} sum={sum(c['amount_cents'] for c in cats)}")
    assert len(cats) == 36, f"expected 36 categories, got {len(cats)}"
    assert sum(c["amount_cents"] for c in cats) == 354_749_500, "Coastal sum mismatch"
    extras = coastal_pc_ps(coastal_pages)
    write_annotation(
        doc_id="coastal",
        difficulty="hard",
        build_type="new_build",
        items=[*cats, *extras],
        quote={
            "stated_total_cents": 354_749_500,
            "stated_basis": "inc",
            "expected_residual_cents": 0,
        },
    )

    # Montique
    montique_pages = page_map("Montique.pdf")
    m_items, m_quote = montique_items(montique_pages)
    ps_count = sum(1 for i in m_items if i["role"] == "ps_allowance")
    print(f"Montique items={len(m_items)} ps={ps_count}")
    # Manual PDF check (2026-07-20): 12 PS on p2 + 30 PS on p3 = 42 currency PS
    # lines (plan's "45" was approximate). Exclude p4 $550 rate note.
    assert ps_count == 42, f"expected 42 PS figures from PDF, got {ps_count}"
    assert any(i.get("suspect_format") for i in m_items), "missing $9,5556.80 suspect"
    write_annotation(
        doc_id="montique",
        difficulty="hard",
        build_type="new_build",
        items=m_items,
        quote=m_quote,
    )

    # Toussaint
    toussaint_pages = page_map("Toussaint.pdf")
    t_items, t_quote = toussaint_items(toussaint_pages)
    sections = [
        i
        for i in t_items
        if i.get("is_rollup")
        and i.get("section_path")
        and re.fullmatch(r"\d+\.0", str(i["section_path"]))
    ]
    print(f"Toussaint items={len(t_items)} top sections={len(sections)}")
    assert len(sections) == 77, f"expected 77 summary sections, got {len(sections)}"
    assert t_quote["stated_total_cents"] == 316_624_355
    assert t_quote["gst_line_cents"] == 316_624_36
    write_annotation(
        doc_id="toussaint",
        difficulty="hard",
        build_type="new_build",
        items=t_items,
        quote=t_quote,
    )

    # Persist bootstrap summary for manual review
    summary = {
        "coastal": {
            "categories": len(cats),
            "sum_cents": sum(c["amount_cents"] for c in cats),
            "pc_ps": len(extras),
        },
        "montique": {"items": len(m_items), "ps": ps_count},
        "toussaint": {
            "items": len(t_items),
            "top_sections": len(sections),
            "stated_ex": t_quote["stated_total_cents"],
            "gst": t_quote["gst_line_cents"],
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
