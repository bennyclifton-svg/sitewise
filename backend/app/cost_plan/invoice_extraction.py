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
_FIELD_RE = re.compile(
    r"^\*\*{label}:\*\*\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


def extract_invoice(candidate: InvoiceCandidate) -> ExtractedInvoice:
    content = candidate.content
    if not is_invoice_document(filename=candidate.filename, content=content):
        raise InvoiceExtractionError(f"{candidate.relative_path} is not an invoice")

    supplier_match = _SUPPLIER_RE.search(content)
    supplier_name = (
        " ".join(supplier_match.group(1).split()) if supplier_match else None
    )
    supplier_abn = (
        re.sub(r"\s+", "", supplier_match.group(2)) if supplier_match else None
    )
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
        if normalized_label == "gst":
            gst = amount
            continue
        if "total amount payable" in normalized_label:
            total_including_gst = amount
            continue
        if normalized_label in {"taxable supply", "subtotal", "total ex gst"}:
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
    try:
        return ExtractedInvoice(
            supplier_name=supplier_name,
            supplier_abn=supplier_abn,
            invoice_number=invoice_number,
            invoice_date=_date(invoice_date_text),
            due_date=_date(due_date_text) if due_date_text else None,
            po_number=_field(content, r"(?:po|purchase order)(?:\s+number|\s+no\.?)?"),
            related_reference=_field(
                content,
                r"related\s+(?:proposal|building proposal|contract)",
            ),
            subtotal_ex_gst=subtotal,
            gst=gst,
            total_including_gst=total_including_gst,
            lines=lines,
            provenance={
                "extractor": "deterministic_markdown_v1",
                "source_document_id": str(candidate.source_document_id),
                "source_path": candidate.relative_path,
                "source_content_hash": candidate.content_hash,
            },
        )
    except ValueError as exc:
        raise InvoiceExtractionError(
            f"Invoice totals do not reconcile in {candidate.relative_path}: {exc}"
        ) from exc


def _field(content: str, label: str) -> str | None:
    pattern = re.compile(_FIELD_RE.pattern.format(label=label), _FIELD_RE.flags)
    match = pattern.search(content)
    return " ".join(_strip_markdown(match.group(1)).split()) if match else None


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
