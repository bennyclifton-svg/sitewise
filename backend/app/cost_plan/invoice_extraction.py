from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.cost_plan.invoice_candidates import InvoiceCandidate, is_invoice_document
from app.cost_plan.schemas import ExtractedInvoice, InvoiceLineInput


class InvoiceExtractionError(ValueError):
    pass


_SUPPLIER_RE = re.compile(
    r"^\*\*([^*\n]+?)\*\*\s*\|\s*ABN\s+([0-9 ]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_SUPPLIER_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_ABN_FIELD_RE = re.compile(
    r"^\*\*ABN\*\*\s+([0-9 ]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FIELD_RE = re.compile(
    r"^\*\*{label}:\*\*\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TABLE_FIELD_RE = re.compile(
    r"^\|\s*\*\*{label}\*\*\s*\|\s*(.+?)\s*\|\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
_TOTAL_LABELS = {
    "total amount payable",
    "total due",
    "total incl gst",
    "total including gst",
}
_SUBTOTAL_LABELS = {
    "taxable supply",
    "subtotal",
    "total ex gst",
    "subtotal excl gst",
    "subtotal ex gst",
}


def extract_invoice(candidate: InvoiceCandidate) -> ExtractedInvoice:
    content = candidate.content
    if not is_invoice_document(
        filename=candidate.filename,
        content=content,
        document_class=None,
        document_metadata=None,
    ):
        raise InvoiceExtractionError(f"{candidate.relative_path} is not an invoice")

    supplier_name, supplier_abn = _supplier(content)
    invoice_number = _field(content, r"invoice\s+(?:number|no\.?)")
    invoice_date_text = _field(content, "invoice date")
    due_date_text = _field(content, "due date")
    if not supplier_name:
        raise InvoiceExtractionError(
            f"Supplier name and ABN are missing from {candidate.relative_path}"
        )
    if not invoice_number:
        raise InvoiceExtractionError(
            f"Invoice number is missing from {candidate.relative_path}"
        )
    if not invoice_date_text:
        raise InvoiceExtractionError(
            f"Invoice date is missing from {candidate.relative_path}"
        )

    table_rows = _table_rows(content)
    header_index = next(
        (
            index
            for index, (cells, _) in enumerate(table_rows)
            if cells
            and _normalize(cells[0]) in {"description", "progress claim"}
            and any("amount" in _normalize(cell) for cell in cells[1:])
        ),
        None,
    )
    if header_index is None:
        raise InvoiceExtractionError(
            f"Invoice line table is missing from {candidate.relative_path}"
        )

    lines: list[InvoiceLineInput] = []
    gst: Decimal | None = None
    total_including_gst: Decimal | None = None
    for cells, source_line in table_rows[header_index + 1 :]:
        if len(cells) < 2:
            continue
        label = _strip_markdown(cells[0])
        normalized_label = _normalize(label)
        amount = _money(cells[-1])
        if normalized_label == "gst" or normalized_label.startswith("gst "):
            gst = amount
            continue
        if any(marker in normalized_label for marker in _TOTAL_LABELS):
            total_including_gst = amount
            if gst is not None:
                break
            continue
        if normalized_label in _SUBTOTAL_LABELS:
            continue
        if amount is None:
            continue
        treatment = "taxable"
        if len(cells) >= 3 and "gst free" in _normalize(cells[-2]):
            treatment = "gst_free"
        lines.append(
            InvoiceLineInput(
                description=label,
                amount_ex_gst=amount,
                gst_treatment=treatment,
                source_locators=[
                    {
                        "type": "markdown_table_row",
                        "line": source_line,
                        "source_document_id": str(candidate.source_document_id),
                    }
                ],
            )
        )

    if not lines:
        raise InvoiceExtractionError(
            f"No priced invoice lines were found in {candidate.relative_path}"
        )
    if gst is None or total_including_gst is None:
        raise InvoiceExtractionError(
            f"GST or inclusive total is missing from {candidate.relative_path}"
        )
    subtotal = sum((line.amount_ex_gst for line in lines), Decimal("0")).quantize(
        Decimal("0.01")
    )
    invoice_number_line = _field_line(content, r"invoice\s+(?:number|no\.?)")
    payload = {
        "supplier_name": supplier_name,
        "supplier_abn": supplier_abn,
        "invoice_number": invoice_number,
        "invoice_date": _date(invoice_date_text),
        "due_date": _date(due_date_text) if due_date_text else None,
        "po_number": _field(content, r"(?:po|purchase order)(?:\s+number|\s+no\.?)?"),
        "related_reference": _field(
            content,
            r"(?:related\s+(?:proposal|building proposal|contract)|our\s+reference)",
        ),
        "subtotal_ex_gst": subtotal,
        "gst": gst,
        "total_including_gst": total_including_gst,
        "lines": [line.model_dump(mode="json") for line in lines],
        "provenance": {
            "extractor": "deterministic_markdown_v1",
            "source_document_id": str(candidate.source_document_id),
            "source_path": candidate.relative_path,
            "source_content_hash": candidate.content_hash,
            "fields": {
                "invoice_number": {
                    "source": "header_regex",
                    "locator": f"line {invoice_number_line}" if invoice_number_line else "header",
                    "confidence": 0.82,
                },
                "supplier_name": {
                    "source": "header_regex",
                    "locator": "supplier heading",
                    "confidence": 0.8,
                },
                "invoice_date": {
                    "source": "header_regex",
                    "locator": "invoice date",
                    "confidence": 0.8,
                },
            },
        },
    }
    try:
        return ExtractedInvoice.model_validate(payload)
    except ValueError:
        return ExtractedInvoice.model_validate(payload, context={"strict": False})


def extract_invoice_secondary(candidate: InvoiceCandidate) -> dict[str, str | None]:
    """Second deterministic parse: table-cell labels instead of bold headers."""
    content = candidate.content
    invoice_number = _table_field(content, r"invoice\s+(?:number|no\.?)")
    invoice_date = _table_field(content, "invoice date")
    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "supplier_name": _supplier(content)[0],
    }


def _supplier(content: str) -> tuple[str | None, str | None]:
    match = _SUPPLIER_RE.search(content)
    if match:
        return " ".join(match.group(1).split()), re.sub(r"\s+", "", match.group(2))
    heading = _SUPPLIER_HEADING_RE.search(content)
    abn = _ABN_FIELD_RE.search(content)
    if heading is None:
        return None, None
    return (
        " ".join(heading.group(1).split()),
        re.sub(r"\s+", "", abn.group(1)) if abn else None,
    )


def _field(content: str, label: str) -> str | None:
    value, _line = _field_match(content, label)
    return value


def _field_line(content: str, label: str) -> int | None:
    _value, line = _field_match(content, label)
    return line


def _field_match(content: str, label: str) -> tuple[str | None, int | None]:
    for template in (_FIELD_RE, _TABLE_FIELD_RE):
        pattern = re.compile(template.pattern.format(label=label), template.flags)
        match = pattern.search(content)
        if match:
            value = " ".join(_strip_markdown(match.group(1)).split())
            line = content[: match.start()].count("\n") + 1
            return value, line
    return None, None


def _table_field(content: str, label: str) -> str | None:
    pattern = re.compile(_TABLE_FIELD_RE.pattern.format(label=label), _TABLE_FIELD_RE.flags)
    match = pattern.search(content)
    if match is None:
        return None
    return " ".join(_strip_markdown(match.group(1)).split())


def _date(value: str):
    normalized = " ".join(value.replace(",", " ").split())
    for format_string in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(normalized, format_string).date()
        except ValueError:
            continue
    raise InvoiceExtractionError(f"Unsupported invoice date {value!r}")


def _table_rows(markdown: str) -> list[tuple[list[str], int]]:
    rows: list[tuple[list[str], int]] = []
    for line_number, raw in enumerate(markdown.splitlines(), start=1):
        stripped = raw.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(_TABLE_SEPARATOR_RE.match(cell) for cell in cells):
            continue
        rows.append((cells, line_number))
    return rows


def _money(value: str) -> Decimal | None:
    cleaned = _strip_markdown(value).replace("$", "").replace(",", "").strip()
    match = re.fullmatch(r"\(?(-?\d+(?:\.\d{1,2})?)\)?", cleaned)
    if match is None:
        return None
    try:
        amount = Decimal(match.group(1))
        if cleaned.startswith("("):
            amount = -amount
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _strip_markdown(value).lower()).strip()


def _strip_markdown(value: str) -> str:
    return re.sub(r"(?:\*\*|__|`)", "", value).strip()
