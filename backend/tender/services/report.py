from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.storage.project_files import upload_project_file
from tender.models import (
    ReportLanguageEntry,
    TaxonomyCell,
    TenderAnalysisResult,
    TenderCellStatus,
    TenderComparison,
    TenderFlag,
    TenderJob,
    TenderProjectTrade,
    TenderQuote,
    TenderReport,
)
from tender.schemas import LedgerItem, MatrixQuoteTotal, QuoteLedgerResponse
from tender.services import qa
from tender.services.artefact_publisher import tender_artefact_publisher
from tender.services.ledger import build_quote_ledger
from tender.services.totals import load_quote_totals

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "report_templates"
NARRATIVE_KEYS = ("executive_summary_intro", "risk_notes_intro")
GLYPHS = {
    "included": "✓",
    "pc": "◷",
    "ps": "◷",
    "excluded_explicit": "✕",
    "silent_ambiguous": "○",
    "bundled": "○",
    "not_required": "–",
    "mixed": "◑",
}


class WeasyPrintUnavailable(RuntimeError):
    pass


class ReportLifecycleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReportQuote:
    id: uuid.UUID
    builder_name: str
    stated_total_cents: int | None
    stated_total_source: str | None = None


@dataclass(frozen=True, slots=True)
class ReportCellStatus:
    quote_id: uuid.UUID
    status: str
    amount_cents: int | None
    evidence: dict[str, Any] = field(default_factory=dict)
    parent_name: str | None = None


@dataclass(frozen=True, slots=True)
class ReportMatrixCell:
    code: str
    name: str
    group: str
    statuses: list[ReportCellStatus] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReportFlag:
    builder_name: str
    cell_name: str
    flag_type: str
    severity: str
    headline: str
    detail: str | None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReportData:
    comparison_id: uuid.UUID
    project_title: str
    context: dict[str, Any]
    quotes: list[ReportQuote]
    ledgers: list[dict[str, Any]]
    matrix: list[ReportMatrixCell]
    flags: list[ReportFlag]
    questions: list[str]
    totals: list[MatrixQuoteTotal] = field(default_factory=list)
    quote_ledgers: list[QuoteLedgerResponse] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReportArtifacts:
    markdown: str
    html: str
    pdf_bytes: bytes


@dataclass(frozen=True, slots=True)
class ReportLifecycleResult:
    report_id: uuid.UUID
    comparison_id: uuid.UUID
    draft_id: uuid.UUID
    version: int
    html_path: str | None
    pdf_path: str | None
    status: str
    approved_at: datetime | None = None
    delivered_at: datetime | None = None


async def get_report_state(
    session: AsyncSession, *, comparison_id: uuid.UUID, version: int | None = None
) -> tuple[ReportLifecycleResult | None, dict[str, Any] | None]:
    if version is None:
        record = await _latest_report(session, comparison_id=comparison_id)
    else:
        record = (
            await session.execute(
                select(TenderReport).where(
                    TenderReport.comparison_id == comparison_id,
                    TenderReport.version == version,
                )
            )
        ).scalar_one_or_none()
    if record is None:
        return None, None
    draft_payload = await tender_artefact_publisher().read_projection(
        session, draft_id=record.draft_id
    )
    status = "delivered" if record.delivered_at else "approved" if record.approved_at else "draft"
    lifecycle = _lifecycle_result(record, status=status)
    return lifecycle, draft_payload


async def assemble_report_draft(session: AsyncSession, job: TenderJob) -> None:
    if job.comparison_id is None:
        raise ValueError("assemble_report_draft job requires comparison_id")
    comparison = await session.get(TenderComparison, job.comparison_id)
    if comparison is None:
        raise ReportLifecycleError(f"unknown comparison: {job.comparison_id}")
    await build_report_draft(
        session,
        comparison_id=job.comparison_id,
        user_id=comparison.created_by,
    )


async def build_report_draft(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ReportLifecycleResult:
    await qa.assert_no_pending_review(session, comparison_id=comparison_id)
    comparison = await _comparison(session, comparison_id)
    project = await _project(session, comparison.project_id)
    latest = await _latest_report(session, comparison_id=comparison_id)
    previous_markdown = await _previous_markdown(session, latest)
    version = (latest.version if latest is not None else 0) + 1
    language = await load_report_language(session)
    artifacts = assemble_report_artifacts(
        await load_report_data(session, comparison_id=comparison_id),
        language=language,
        previous_markdown=previous_markdown,
        draft=True,
        # Local Windows often lacks GTK; still ship HTML + markdown draft.
        require_pdf=False,
    )
    draft_id = await tender_artefact_publisher().publish_draft(
        session,
        project=project,
        comparison_id=comparison_id,
        report_version=version,
        title=f"{language_value(language, 'report.title')} v{version:02d}",
        workspace_path=_draft_workspace_path(project, version),
        author_user_id=user_id,
        markdown=artifacts.markdown,
    )
    html_path, pdf_path = await _store_artifacts(
        project=project,
        comparison_id=comparison_id,
        version=version,
        artifacts=artifacts,
        final=False,
    )
    report = TenderReport(
        comparison_id=comparison_id,
        draft_id=draft_id,
        version=version,
        html_path=html_path,
        pdf_path=pdf_path,
    )
    session.add(report)
    comparison.status = "report_draft"
    await session.flush()
    return _lifecycle_result(report, status=comparison.status)


async def approve_report(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ReportLifecycleResult:
    comparison = await _comparison(session, comparison_id)
    project = await _project(session, comparison.project_id)
    report = await _required_latest_report(session, comparison_id=comparison_id)
    draft_markdown = await tender_artefact_publisher().read_markdown(
        session, draft_id=report.draft_id
    )
    if draft_markdown is None:
        raise ReportLifecycleError(f"report draft not found: {report.draft_id}")
    language = await load_report_language(session)
    artifacts = assemble_report_artifacts(
        await load_report_data(session, comparison_id=comparison_id),
        language=language,
        previous_markdown=draft_markdown,
        draft=False,
    )
    html_path, pdf_path = await _store_artifacts(
        project=project,
        comparison_id=comparison_id,
        version=report.version,
        artifacts=artifacts,
        final=True,
    )
    report.html_path = html_path
    report.pdf_path = pdf_path
    report.approved_by = user_id
    report.approved_at = datetime.now(timezone.utc)
    comparison.status = "approved"
    await tender_artefact_publisher().publish_approved(
        session,
        draft_id=report.draft_id,
        comparison_id=comparison_id,
        report_version=report.version,
        approved_by=user_id,
        html_path=html_path,
        pdf_path=pdf_path,
    )
    await session.flush()
    return _lifecycle_result(report, status=comparison.status)


async def mark_report_delivered(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    delivery_note: str | None,
) -> ReportLifecycleResult:
    comparison = await _comparison(session, comparison_id)
    report = await _required_latest_report(session, comparison_id=comparison_id)
    report.delivered_at = datetime.now(timezone.utc)
    report.delivery_note = delivery_note
    comparison.status = "delivered"
    await session.flush()
    return _lifecycle_result(report, status=comparison.status)


async def load_report_language(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(select(ReportLanguageEntry))
    return _nested_language(
        {entry.key_path: entry.value for entry in result.scalars()}
    )


async def load_report_data(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> ReportData:
    comparison = await _comparison(session, comparison_id)
    project = await _project(session, comparison.project_id)
    quote_result = await session.execute(
        select(TenderQuote)
        .where(TenderQuote.comparison_id == comparison_id)
        .order_by(TenderQuote.created_at)
    )
    quotes = [
        ReportQuote(
            id=quote.id,
            builder_name=quote.builder_name,
            stated_total_cents=quote.stated_total_cents,
            stated_total_source=quote.stated_total_source,
        )
        for quote in quote_result.scalars()
    ]
    analysis_result = await session.execute(
        select(TenderAnalysisResult).where(
            TenderAnalysisResult.comparison_id == comparison_id
        )
    )
    analysis = analysis_result.scalar_one_or_none()
    matrix = await _report_matrix(session, comparison_id=comparison_id)
    flags = await _report_flags(session, comparison_id=comparison_id)
    totals = await load_quote_totals(session, comparison_id)
    quote_ledgers = [
        await build_quote_ledger(
            session, comparison_id=comparison_id, quote_id=quote.id
        )
        for quote in quotes
    ]
    return ReportData(
        comparison_id=comparison_id,
        project_title=project.title,
        context=comparison.context,
        quotes=quotes,
        ledgers=analysis.ledgers if analysis is not None else [],
        matrix=matrix,
        flags=flags,
        questions=analysis.questions if analysis is not None else [],
        totals=totals,
        quote_ledgers=quote_ledgers,
    )


def load_report_language_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError("report language file must contain a mapping")
    return data


def assemble_report_artifacts(
    data: ReportData,
    *,
    language: Mapping[str, Any],
    draft: bool,
    previous_markdown: str | None = None,
    pdf_renderer: Callable[[str], bytes] | None = None,
    require_pdf: bool = True,
) -> ReportArtifacts:
    narratives = default_narratives(language)
    narratives.update(extract_narratives(previous_markdown or ""))
    view = report_view(data, language=language, narratives=narratives)
    markdown = render_draft_markdown(
        view, language=language, narratives=narratives
    )
    html = render_report_html(
        view, language=language, narratives=narratives, draft=draft
    )
    renderer = pdf_renderer or render_pdf_bytes
    try:
        pdf_bytes = renderer(html)
    except WeasyPrintUnavailable:
        if require_pdf:
            raise
        pdf_bytes = b""
    return ReportArtifacts(markdown=markdown, html=html, pdf_bytes=pdf_bytes)


def render_pdf_bytes(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as exc:  # pragma: no cover - depends on host native libraries
        raise WeasyPrintUnavailable(
            f"WeasyPrint native dependencies are unavailable: {exc}"
        ) from exc
    return HTML(string=html).write_pdf()


def default_narratives(language: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: str(language_value(language, f"report.default_narratives.{key}") or "")
        for key in NARRATIVE_KEYS
    }


def extract_narratives(markdown: str) -> dict[str, str]:
    narratives: dict[str, str] = {}
    for key in NARRATIVE_KEYS:
        pattern = re.compile(
            rf"<!-- tcm:narrative:{re.escape(key)}:start -->\n(.*?)\n<!-- tcm:narrative:{re.escape(key)}:end -->",
            re.DOTALL,
        )
        match = pattern.search(markdown)
        if match:
            narratives[key] = match.group(1).strip()
    return narratives


def render_draft_markdown(
    view: dict[str, Any],
    *,
    language: Mapping[str, Any],
    narratives: Mapping[str, str],
) -> str:
    section_titles = _section_titles(language)
    labels = _labels(language)
    lines = [
        f"# {language_value(language, 'report.title')}",
        "",
        f"## {section_titles['executive_summary']}",
        _narrative_block("executive_summary_intro", narratives),
        "",
        f"## {section_titles['price_comparison']}",
        _totals_markdown(view, labels),
        "",
        f"## {section_titles['comparison_matrix']}",
        _matrix_markdown(view),
        "",
        f"## {section_titles['allowances']}",
        _allowances_markdown(view, labels),
        "",
        f"## {section_titles['risk_notes']}",
        _narrative_block("risk_notes_intro", narratives),
        _flags_markdown(view),
        "",
        f"## {section_titles['methodology']}",
        str(language_value(language, "report.legal.disclaimer")),
        "",
        f"## {section_titles['quote_ledgers']}",
        _quote_ledgers_markdown(view, labels),
    ]
    return "\n".join(lines).strip() + "\n"


def render_report_html(
    view: dict[str, Any],
    *,
    language: Mapping[str, Any],
    narratives: Mapping[str, str],
    draft: bool,
) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
    )
    template = env.get_template("base.html")
    return template.render(
        title=language_value(language, "report.title"),
        draft=draft,
        draft_label=language_value(language, "report.draft_label"),
        project_title=view["project_title"],
        section_titles=_section_titles(language),
        labels=_labels(language),
        legal={
            "disclaimer": language_value(language, "report.legal.disclaimer"),
            "not_itemised": language_value(language, "report.legal.not_itemised"),
        },
        narratives=narratives,
        quotes=view["quotes"],
        ledgers=view["ledgers"],
        matrix=view["matrix"],
        allowances=view["allowances"],
        flags=view["flags"],
        questions=view["questions"],
        totals=view["totals"],
        totals_by_quote=view["totals_by_quote"],
        quote_ledgers=view["quote_ledgers"],
    )


def report_view(
    data: ReportData,
    *,
    language: Mapping[str, Any],
    narratives: Mapping[str, str],
) -> dict[str, Any]:
    quotes = [
        {
            "id": str(quote.id),
            "builder_name": quote.builder_name,
            "stated_total": money(quote.stated_total_cents),
        }
        for quote in data.quotes
    ]
    builder_by_id = {quote.id: quote.builder_name for quote in data.quotes}
    matrix = [
        {
            "code": cell.code,
            "name": cell.name,
            "group": cell.group,
            "by_quote": {
                str(status.quote_id): _cell_view(cell, status, language)
                for status in cell.statuses
            },
        }
        for cell in data.matrix
    ]
    allowances = [
        {
            "builder_name": builder_by_id.get(status.quote_id, ""),
            "cell_name": cell.name,
            "amount": money(status.amount_cents),
        }
        for cell in data.matrix
        for status in cell.statuses
        if status.status in {"pc", "ps"}
    ]
    totals = [_total_view(total, builder_by_id, language) for total in data.totals]
    return {
        "project_title": data.project_title,
        "context": data.context,
        "quotes": quotes,
        "ledgers": [
            {
                "builder_name": str(row.get("builder_name", "")),
                "cell_name": str(row.get("cell_name", "")),
                "adjustment": money(row.get("adjustment_cents")),
                "provenance": str(row.get("provenance", "")),
            }
            for row in data.ledgers
        ],
        "matrix": matrix,
        "allowances": allowances,
        "flags": [
            {
                "builder_name": flag.builder_name,
                "headline": flag.headline,
                "phrase": language_value(
                    language,
                    f"flag_phrases.{flag.flag_type}",
                ),
            }
            for flag in data.flags
        ],
        "questions": data.questions,
        "narratives": dict(narratives),
        "totals": totals,
        "totals_by_quote": {total["quote_id"]: total for total in totals},
        "quote_ledgers": [
            _quote_ledger_view(ledger, language) for ledger in data.quote_ledgers
        ],
    }


def _cell_view(
    cell: ReportMatrixCell,
    status: ReportCellStatus,
    language: Mapping[str, Any],
) -> dict[str, str]:
    phrase = status_phrase(cell, status, language)
    amount = money(status.amount_cents)
    # Included cells read as their price; every other status keeps its
    # claim-strength phrase (which embeds the amount for pc/ps allowances).
    display = amount if status.status == "included" and amount else phrase
    return {
        "glyph": glyph_for_status(status.status),
        "phrase": phrase,
        "amount": amount,
        "display": display,
    }


def _total_view(
    total: MatrixQuoteTotal,
    builder_by_id: Mapping[uuid.UUID, str],
    language: Mapping[str, Any],
) -> dict[str, Any]:
    if total.reconciliation == "match":
        variance = str(language_value(language, "report.labels.matches_stated"))
    elif total.reconciliation == "not_stated":
        variance = str(language_value(language, "report.labels.total_not_stated"))
    else:
        variance = signed_money(total.delta_cents)
    stated_native = total.stated_native_cents
    residual = total.residual_cents
    counted = None if stated_native is None else stated_native - residual
    return {
        "quote_id": str(total.quote_id),
        "builder_name": builder_by_id.get(total.quote_id, ""),
        "computed_total": money(total.computed_total_cents),
        "stated_total": money(total.stated_total_cents),
        "reconciliation": total.reconciliation,
        "variance": variance,
        "non_comparable": total.non_comparable,
        "stated_native": money(stated_native),
        "counted": money(counted),
        "residual": money(residual),
        "residual_nonzero": residual != 0,
        "has_stated_native": stated_native is not None,
    }


def _quote_ledger_view(
    ledger: QuoteLedgerResponse,
    language: Mapping[str, Any],
) -> dict[str, Any]:
    labels = _labels(language)
    nested = [
        _ledger_item_view(item, labels=labels, depth=0) for item in ledger.items
    ]
    return {
        "quote_id": str(ledger.quote_id),
        "builder_name": ledger.builder_name,
        "stated_total": money(ledger.stated_total_cents),
        "stated_basis": ledger.stated_basis or "",
        "status": ledger.status,
        "residual": money(ledger.residual_cents),
        "residual_nonzero": ledger.residual_cents != 0,
        "computed_ex_gst": money(ledger.computed_ex_gst_cents),
        "rows": _flatten_ledger_items(nested),
    }


def _ledger_item_view(
    item: LedgerItem,
    *,
    labels: Mapping[str, str],
    depth: int,
) -> dict[str, Any]:
    markers: list[str] = []
    if item.duplicate_of_id is not None:
        markers.append(labels["reprint"])
    if item.is_rollup:
        markers.append(labels["rollup"])
    return {
        "description": item.description_raw,
        "page": item.page_no,
        "role": item.role or "",
        "amount": money(item.amount_cents),
        "amount_ex_gst": money(item.amount_ex_gst_cents),
        "counted": item.counted_in_total,
        "duplicate": item.duplicate_of_id is not None,
        "markers": markers,
        "depth": depth,
        "children": [
            _ledger_item_view(child, labels=labels, depth=depth + 1)
            for child in item.children
        ],
    }


def status_phrase(
    cell: ReportMatrixCell,
    status: ReportCellStatus,
    language: Mapping[str, Any],
) -> str:
    status_key = status.status
    if status.status == "excluded_explicit" and _first_page(status.evidence) is None:
        status_key = "silent_ambiguous"
    template = str(language_value(language, f"status_phrases.{status_key}"))
    return template.format(
        page=_first_page(status.evidence) or "",
        amount=money(status.amount_cents),
        parent_name=status.parent_name or "",
        cell_name=cell.name,
    )


def glyph_for_status(status: str) -> str:
    return GLYPHS.get(status, "○")


def money(cents: Any) -> str:
    if cents is None:
        return ""
    dollars = int(cents) / 100
    return f"${dollars:,.0f}"


def signed_money(cents: int | None) -> str:
    if cents is None:
        return ""
    if cents == 0:
        return "$0"
    prefix = "+" if cents > 0 else "-"
    return f"{prefix}{money(abs(cents))}"


def language_value(language: Mapping[str, Any], key_path: str) -> Any:
    if key_path in language:
        return language[key_path]
    value: Any = language
    for part in key_path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise KeyError(f"missing report language key: {key_path}")
        value = value[part]
    return value


def _nested_language(flat_language: Mapping[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key_path, value in flat_language.items():
        target = nested
        parts = key_path.split(".")
        for part in parts[:-1]:
            child = target.setdefault(part, {})
            if not isinstance(child, dict):
                raise ValueError(f"conflicting report language key: {key_path}")
            target = child
        target[parts[-1]] = value
    return _restore_language_lists(nested)


def _restore_language_lists(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    restored = {key: _restore_language_lists(child) for key, child in value.items()}
    if restored and all(_language_list_key(key) for key in restored):
        return [restored[key] for key in sorted(restored, key=int)]
    return restored


def _language_list_key(value: str) -> bool:
    return value.isdigit()


def _section_titles(language: Mapping[str, Any]) -> dict[str, str]:
    raw = language_value(language, "report.section_titles")
    return {str(key): str(value) for key, value in raw.items()}


def _labels(language: Mapping[str, Any]) -> dict[str, str]:
    raw = language_value(language, "report.labels")
    return {str(key): str(value) for key, value in raw.items()}


def _narrative_block(key: str, narratives: Mapping[str, str]) -> str:
    return (
        f"<!-- tcm:narrative:{key}:start -->\n"
        f"{narratives.get(key, '').strip()}\n"
        f"<!-- tcm:narrative:{key}:end -->"
    )


def _totals_markdown(view: Mapping[str, Any], labels: Mapping[str, str]) -> str:
    rows = [
        f"| {labels['builder']} | {labels['computed_total']} | "
        f"{labels['stated_total']} | {labels['variance']} |",
        "| --- | --- | --- | --- |",
    ]
    for total in view["totals"]:
        rows.append(
            f"| {total['builder_name']} | {total['computed_total']} | "
            f"{total['stated_total']} | {total['variance']} |"
        )
        if total.get("non_comparable"):
            rows.append(f"|  | {labels['cost_plus_non_comparable']} |  |  |")
        if total.get("has_stated_native"):
            rows.append(
                f"|  | {labels['stated_native']}: {total['stated_native']} · "
                f"{labels['counted']}: {total['counted']} · "
                f"{labels['residual']}: {total['residual']} |  |  |"
            )
        elif total.get("reconciliation") == "not_stated":
            rows.append(f"|  | {labels['total_not_stated']} |  |  |")
    return "\n".join(rows)


def _allowances_markdown(view: Mapping[str, Any], labels: Mapping[str, str]) -> str:
    rows = [
        f"| {labels['item']} | {labels['builder']} | {labels['amount']} |",
        "| --- | --- | --- |",
    ]
    for allowance in view["allowances"]:
        rows.append(
            f"| {allowance['cell_name']} | {allowance['builder_name']} | "
            f"{allowance['amount']} |"
        )
    return "\n".join(rows)


def _matrix_markdown(view: Mapping[str, Any]) -> str:
    quotes = view["quotes"]
    header = "| Item | " + " | ".join(quote["builder_name"] for quote in quotes) + " |"
    separator = "| --- | " + " | ".join("---" for _ in quotes) + " |"
    rows = [header, separator]
    for cell in view["matrix"]:
        values = []
        for quote in quotes:
            status = cell["by_quote"].get(quote["id"])
            values.append(f"{status['glyph']} {status['display']}" if status else "")
        rows.append(f"| {cell['name']} | " + " | ".join(values) + " |")
    return "\n".join(rows)


def _quote_ledgers_markdown(
    view: Mapping[str, Any], labels: Mapping[str, str]
) -> str:
    blocks: list[str] = []
    for ledger in view["quote_ledgers"]:
        blocks.append(f"### {ledger['builder_name']}")
        blocks.append(
            f"{labels['ledger_status']}: {ledger['status']} · "
            f"{labels['stated_total']}: {ledger['stated_total']}"
            + (
                f" ({ledger['stated_basis']})"
                if ledger.get("stated_basis")
                else ""
            )
        )
        blocks.append(
            f"| {labels['description']} | {labels['page']} | {labels['role']} | "
            f"{labels['native_amount']} | {labels['ex_gst']} |"
        )
        blocks.append("| --- | --- | --- | --- | --- |")
        for item in ledger["rows"]:
            indent = "  " * int(item["depth"])
            marker = (
                f" ({', '.join(item['markers'])})" if item["markers"] else ""
            )
            blocks.append(
                f"| {indent}{item['description']}{marker} | "
                f"{item['page'] if item['page'] is not None else ''} | "
                f"{item['role']} | {item['amount']} | {item['amount_ex_gst']} |"
            )
        blocks.append(
            f"{labels['residual']}: {ledger['residual']}"
        )
        blocks.append("")
    return "\n".join(blocks).strip()


def _flatten_ledger_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for item in items:
        flat.append(item)
        flat.extend(_flatten_ledger_items(item.get("children") or []))
    return flat


def _flags_markdown(view: Mapping[str, Any]) -> str:
    if not view["flags"]:
        return ""
    rows = ["| Builder | Flag |", "| --- | --- |"]
    for flag in view["flags"]:
        rows.append(f"| {flag['builder_name']} | {flag['headline']} |")
    return "\n".join(rows)


def _first_page(evidence: Mapping[str, Any]) -> int | None:
    refs = evidence.get("page_refs")
    if not isinstance(refs, list) or not refs:
        return None
    page = refs[0].get("page") if isinstance(refs[0], Mapping) else None
    return int(page) if page is not None else None


async def _comparison(
    session: AsyncSession,
    comparison_id: uuid.UUID,
) -> TenderComparison:
    comparison = await session.get(TenderComparison, comparison_id)
    if comparison is None:
        raise ReportLifecycleError(f"unknown comparison: {comparison_id}")
    return comparison


async def _project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise ReportLifecycleError(f"unknown project: {project_id}")
    return project


async def _latest_report(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> TenderReport | None:
    result = await session.execute(
        select(TenderReport)
        .where(TenderReport.comparison_id == comparison_id)
        .order_by(TenderReport.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _required_latest_report(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> TenderReport:
    report = await _latest_report(session, comparison_id=comparison_id)
    if report is None:
        raise ReportLifecycleError(f"report has not been built: {comparison_id}")
    return report


async def _previous_markdown(
    session: AsyncSession,
    report: TenderReport | None,
) -> str | None:
    if report is None:
        return None
    return await tender_artefact_publisher().read_markdown(
        session, draft_id=report.draft_id
    )


async def _report_matrix(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> list[ReportMatrixCell]:
    trade_result = await session.execute(
        select(TenderProjectTrade)
        .where(TenderProjectTrade.comparison_id == comparison_id)
        .order_by(TenderProjectTrade.sort_order, TenderProjectTrade.code)
    )
    trades = list(trade_result.scalars())
    if trades:
        return await _report_trade_matrix(
            session, comparison_id=comparison_id, trades=trades
        )
    return await _report_cell_matrix(session, comparison_id=comparison_id)


async def _report_trade_matrix(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    trades: list[TenderProjectTrade],
) -> list[ReportMatrixCell]:
    status_result = await session.execute(
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == comparison_id,
            TenderCellStatus.project_trade_id.is_not(None),
        )
    )
    cells: dict[uuid.UUID, ReportMatrixCell] = {}
    for trade in trades:
        cells[trade.id] = ReportMatrixCell(
            code=trade.code,
            name=trade.name,
            group=trade.group_label or "Other",
        )
    for status in status_result.scalars():
        report_cell = cells.get(status.project_trade_id)  # type: ignore[arg-type]
        if report_cell is None:
            continue
        report_cell.statuses.append(
            ReportCellStatus(
                quote_id=status.quote_id,
                status=status.status,
                amount_cents=status.amount_cents,
                evidence=status.evidence or {},
                parent_name=status.bundled_into_cell,
            )
        )
    return list(cells.values())


async def _report_cell_matrix(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> list[ReportMatrixCell]:
    result = await session.execute(
        select(TenderCellStatus, TaxonomyCell)
        .join(TaxonomyCell, TaxonomyCell.code == TenderCellStatus.cell_code)
        .where(TenderCellStatus.comparison_id == comparison_id)
        .order_by(TaxonomyCell.sort_order, TenderCellStatus.cell_code)
    )
    cells: dict[str, ReportMatrixCell] = {}
    for status, cell in result.all():
        report_cell = cells.setdefault(
            cell.code,
            ReportMatrixCell(code=cell.code, name=cell.name, group=cell.grp),
        )
        report_cell.statuses.append(
            ReportCellStatus(
                quote_id=status.quote_id,
                status=status.status,
                amount_cents=status.amount_cents,
                evidence=status.evidence or {},
                parent_name=status.bundled_into_cell,
            )
        )
    return list(cells.values())


async def _report_flags(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> list[ReportFlag]:
    result = await session.execute(
        select(TenderFlag, TenderQuote)
        .join(TenderQuote, TenderQuote.id == TenderFlag.quote_id)
        .where(
            TenderFlag.comparison_id == comparison_id,
            TenderFlag.include_in_report.is_(True),
        )
    )
    rows = list(result.all())
    trade_result = await session.execute(
        select(TenderProjectTrade).where(
            TenderProjectTrade.comparison_id == comparison_id
        )
    )
    trade_name_by_code = {
        trade.code: trade.name for trade in trade_result.scalars()
    }
    taxonomy_codes = {
        flag.cell_code
        for flag, _quote in rows
        if flag.cell_code and flag.cell_code not in trade_name_by_code
    }
    cell_name_by_code: dict[str, str] = {}
    if taxonomy_codes:
        cell_result = await session.execute(
            select(TaxonomyCell).where(TaxonomyCell.code.in_(taxonomy_codes))
        )
        cell_name_by_code = {cell.code: cell.name for cell in cell_result.scalars()}

    flags: list[ReportFlag] = []
    for flag, quote in rows:
        cell_name = ""
        if flag.cell_code:
            cell_name = trade_name_by_code.get(
                flag.cell_code,
                cell_name_by_code.get(flag.cell_code, flag.cell_code),
            )
        flags.append(
            ReportFlag(
                builder_name=quote.builder_name,
                cell_name=cell_name,
                flag_type=flag.flag_type,
                severity=flag.severity,
                headline=flag.headline,
                detail=flag.detail,
                evidence=flag.evidence or {},
            )
        )
    return flags


async def _store_artifacts(
    *,
    project: Project,
    comparison_id: uuid.UUID,
    version: int,
    artifacts: ReportArtifacts,
    final: bool,
) -> tuple[str, str | None]:
    suffix = "final" if final else "draft"
    base = f"{project.id}/tender/reports/{comparison_id}/v{version:02d}"
    html_path = f"{base}/{suffix}.html"
    await asyncio.to_thread(
        upload_project_file,
        storage_key=html_path,
        content=artifacts.html.encode("utf-8"),
        filename=f"{suffix}.html",
    )
    if not artifacts.pdf_bytes:
        return html_path, None
    pdf_path = f"{base}/{suffix}.pdf"
    await asyncio.to_thread(
        upload_project_file,
        storage_key=pdf_path,
        content=artifacts.pdf_bytes,
        filename=f"{suffix}.pdf",
    )
    return html_path, pdf_path


def _draft_workspace_path(project: Project, version: int) -> str:
    return (
        f"{project.workspace_path}/05-procurement/"
        f"tender-comparison-report-v{version:02d}.md"
    )


def _lifecycle_result(
    report: TenderReport,
    *,
    status: str,
) -> ReportLifecycleResult:
    return ReportLifecycleResult(
        report_id=report.id,
        comparison_id=report.comparison_id,
        draft_id=report.draft_id,
        version=report.version,
        html_path=report.html_path,
        pdf_path=report.pdf_path,
        status=status,
        approved_at=report.approved_at,
        delivered_at=report.delivered_at,
    )
