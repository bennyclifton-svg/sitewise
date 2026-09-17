"""Compact Markdown presentation shared by the viewer and existing issue exports."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.sitewise.pmp_citations import build_citation_index
from tender.review_schemas import ReviewSelection
from tender.services.review_facts import headline_spread
from tender.services.review_matrix import MatrixCell, build_price_matrix


def safe(value: Any) -> str:
    text = " ".join(str(value).split())
    return re.sub(r"([\\`*\[\]<>|])", r"\\\1", text)


def money(cents: int, currency: str = "AUD") -> str:
    return f"{'$' if currency == 'AUD' else currency + ' '}{Decimal(cents) / 100:,.2f}"


def render_review(
    *,
    package: str,
    profile: str,
    review_date: str,
    quotes: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    selection: ReviewSelection,
    calculations: dict[str, dict[str, Any]],
    language: dict[str, Any],
) -> str:
    lang = language["procurement_review"]
    by_fact = {fact["id"]: fact for fact in facts}
    by_quote = {quote["id"]: quote for quote in quotes}
    by_document = {doc["id"]: doc for doc in documents}
    index = build_citation_index([(doc["path"], doc["quote_id"]) for doc in documents])
    cited_paths: set[str] = set()
    matrix_lang = lang["additive_matrix"]
    matrix = build_price_matrix(
        selection, facts, quotes, calculations, other_label=matrix_lang["other_items"]
    )

    def citation(fact: dict[str, Any]) -> str:
        cited_paths.add(by_document[fact["document_id"]]["path"])
        return f"{index.token_for(by_document[fact['document_id']]['path'])} ({lang['page'].format(page=fact['page_no'])})"

    def cites(ids: list[str]) -> str:
        return " ".join(dict.fromkeys(citation(by_fact[value]) for value in ids))

    def matrix_cites(ids: list[str]) -> str:
        pages_by_document: dict[str, set[int]] = {}
        for value in ids:
            fact = by_fact[value]
            path = by_document[fact["document_id"]]["path"]
            cited_paths.add(path)
            pages_by_document.setdefault(path, set()).add(fact["page_no"])
        references = []
        for path, pages in pages_by_document.items():
            runs: list[list[int]] = []
            for page in sorted(pages):
                if runs and page == runs[-1][-1] + 1:
                    runs[-1].append(page)
                else:
                    runs.append([page])
            page_list = ", ".join(
                str(run[0]) if len(run) == 1 else f"{run[0]}–{run[-1]}" for run in runs
            )
            references.append(
                index.token_for(path) + " (" + lang["page"].format(page=page_list) + ")"
            )
        return " ".join(references)

    def description(ids: list[str], *, limit: int = 190) -> str:
        parts = []
        excerpts: dict[str, list[str]] = {}
        for value in ids:
            fact = by_fact[value]
            firms = excerpts.setdefault(fact["excerpt"], [])
            firm = safe(by_quote[fact["quote_id"]]["name"])
            if firm not in firms:
                firms.append(firm)
        for excerpt, firms in excerpts.items():
            if len(excerpt) > limit:
                excerpt = excerpt[:limit].rsplit(" ", 1)[0] + "…"
            parts.append(
                lang["source_detail"].format(
                    firm=" / ".join(firms), excerpt=safe(excerpt)
                )
            )
        return "; ".join(parts) + " " + cites(ids)

    def matrix_cell(value: MatrixCell, column_index: int) -> str:
        column = matrix.columns[column_index]
        notes = []
        if len(value.counted_ids) > 1:
            notes.append(matrix_lang["combined"].format(count=len(value.counted_ids)))
        notes.extend(
            matrix_lang["bundled_in"].format(item=safe(name))
            for name in value.bundled_rows
        )
        counted = [by_fact[fact_id] for fact_id in value.counted_ids]
        for fact_id in value.fact_ids:
            fact = by_fact[fact_id]
            same_price = any(
                fact["kind"] in {"component", "subtotal", "allowance"}
                and (
                    fact["label"].casefold(),
                    fact["amount_cents"],
                    fact["currency"],
                    fact["tax_basis"],
                )
                == (
                    other["label"].casefold(),
                    other["amount_cents"],
                    other["currency"],
                    other["tax_basis"],
                )
                for other in counted
            )
            if same_price and not column.mixed_bases:
                if fact["kind"] == "allowance":
                    notes.append(lang["statuses"]["allowance"])
                continue
            if fact.get("amount_printed"):
                if fact["amount_cents"] is None:
                    notes.append(
                        lang["unresolved"].format(printed=safe(fact["amount_printed"]))
                    )
                else:
                    notes.append(
                        matrix_lang["reference_price"].format(
                            item=safe(fact["label"]),
                            amount=money(fact["amount_cents"], fact["currency"]),
                            basis=lang["tax"][fact["tax_basis"]],
                            status=lang["statuses"].get(
                                fact["kind"], lang["not_stated"]
                            ),
                        )
                    )
            else:
                notes.append(lang["statuses"].get(fact["kind"], lang["not_stated"]))
        if column.mixed_bases and value.fact_ids:
            notes.append(matrix_lang["mixed_bases"])
        if not value.fact_ids:
            notes.append(lang["not_stated"])
        references = matrix_cites(value.fact_ids)
        if references:
            notes.append(references)
        amount = (
            f"**{money(value.amount_cents, column.currency)}**"
            if value.amount_cents is not None
            else ""
        )
        return " · ".join(filter(None, [amount, "; ".join(dict.fromkeys(notes))]))

    preferred = by_quote.get(selection.preferred_quote_id or "", {}).get("name", "")
    lines = [
        f"# {lang['title'].format(package=safe(package))}",
        "",
        lang["reviewed"].format(
            date=review_date, files=len(documents), firms=len(quotes)
        ),
        "",
        f"## {lang['recommendation']}",
        "",
        lang["conclusions"][selection.conclusion].format(firm=safe(preferred))
        + " "
        + cites(selection.recommendation_fact_ids),
        "",
        f"## {lang['headlines']}",
        "",
        f"| {lang['headers']['firm']} | {lang['headers']['total']} | {lang['headers']['basis']} |",
        "| --- | --- | --- |",
    ]
    for quote in quotes:
        calc = calculations[quote["id"]]
        total = (
            money(calc["headline_cents"], calc["currency"])
            if calc["headline_cents"] is not None
            else lang["not_stated"]
        )
        basis = (
            lang["conflicting"]
            if calc["conflicting_totals"]
            else lang["tax"][calc["headline_basis"]]
        )
        lines.append(
            f"| {safe(quote['name'])} | {total} | {basis} {cites(calc['headline_fact_ids'])} |"
        )
    spread = headline_spread(calculations)
    if spread and spread[2]:
        lines += [
            "",
            lang["headline_meaning"].format(
                lowest=safe(by_quote[spread[0]]["name"]),
                highest=safe(by_quote[spread[1]]["name"]),
                spread=money(spread[2]),
            )
            + " "
            + cites(
                calculations[spread[0]]["headline_fact_ids"]
                + calculations[spread[1]]["headline_fact_ids"]
            ),
        ]
    lines += ["", f"## {lang['differences']}", ""]
    findings = selection.findings[:3] if profile == "consultant" else selection.findings
    for finding in findings:
        lines.append(
            f"- **{lang['issue_titles'][finding.issue]}:** {description(finding.fact_ids, limit=75 if profile == 'consultant' else 140)}"
        )

    checks_by_quote: dict[str, list[str]] = {quote["id"]: [] for quote in quotes}
    for quote in quotes:
        checks = checks_by_quote[quote["id"]]
        calc = calculations[quote["id"]]
        for value in calc["malformed_fact_ids"]:
            fact = by_fact[value]
            checks.append(
                lang["malformed"].format(
                    firm=safe(quote["name"]), printed=safe(fact["amount_printed"])
                )
                + " "
                + citation(fact)
            )
        if calc["expired_fact_ids"]:
            checks.append(
                lang["expired"].format(firm=safe(quote["name"]))
                + " "
                + cites(calc["expired_fact_ids"])
            )
        if calc["conflicting_totals"]:
            checks.append(
                safe(quote["name"])
                + ": "
                + lang["conflicting"]
                + " "
                + cites(calc["headline_fact_ids"])
            )
        if calc["residual_cents"] and calc["apparent_uplift_percent"]:
            checks.append(
                matrix_lang["residual_question"].format(
                    firm=safe(quote["name"]),
                    components=money(calc["component_sum_cents"], calc["currency"]),
                    total=money(
                        calc.get("reconciliation_total_cents", calc["headline_cents"]),
                        calc["currency"],
                    ),
                    residual=money(calc["residual_cents"], calc["currency"]),
                    percent=calc["apparent_uplift_percent"],
                )
                + " "
                + cites(calc["headline_fact_ids"])
            )
    for doc in documents:
        pages = sorted({item["page_no"] for item in doc.get("uncaptured", [])})
        if pages:
            cited_paths.add(doc["path"])
            checks_by_quote[doc["quote_id"]].append(
                lang["uncaptured"].format(
                    firm=safe(by_quote[doc["quote_id"]]["name"]),
                    page=", ".join(map(str, pages)),
                )
                + " "
                + index.token_for(doc["path"])
            )

    if profile == "head_contractor":
        lines += ["", "<!-- pagebreak -->"]
    lines += ["", f"## {lang['questions']}", ""]
    question_lines = []
    questions_by_quote: dict[str, list[str]] = {quote["id"]: [] for quote in quotes}
    for finding in findings:
        if profile == "consultant":
            own = [by_fact[value] for value in finding.fact_ids]
            items = ", ".join(dict.fromkeys(safe(fact["label"]) for fact in own))
            firms = " / ".join(
                dict.fromkeys(safe(by_quote[fact["quote_id"]]["name"]) for fact in own)
            )
            question_lines.append(
                lang["quote_question"].format(
                    firm=firms,
                    question=lang["question_templates"][finding.issue].format(
                        items=items
                    ),
                )
                + " "
                + cites(finding.fact_ids)
            )
            continue
        for quote in quotes:
            own = [
                by_fact[value]
                for value in finding.fact_ids
                if by_fact[value]["quote_id"] == quote["id"]
            ]
            if not own:
                continue
            if (
                finding.issue == "validity"
                and calculations[quote["id"]]["expired_fact_ids"]
            ):
                continue
            items = ", ".join(dict.fromkeys(safe(fact["label"]) for fact in own))
            issue = (
                "scope"
                if finding.issue == "conflict" and len(own) < 2
                else finding.issue
            )
            question = lang["question_templates"][issue].format(items=items)
            questions_by_quote[quote["id"]].append(
                lang["quote_question"].format(
                    firm=safe(quote["name"]), question=question
                )
                + " "
                + cites([fact["id"] for fact in own])
            )
    if profile == "consultant":
        checks = [item for values in checks_by_quote.values() for item in values]
        lines += [
            f"- {question}" for question in dict.fromkeys(checks + question_lines)
        ]
    else:
        for quote in quotes:
            priority = list(dict.fromkeys(checks_by_quote[quote["id"]]))
            additional = list(dict.fromkeys(questions_by_quote[quote["id"]]))
            used = {value for finding in findings for value in finding.fact_ids}
            for row in selection.matrix:
                if len(priority) + len(additional) >= 3:
                    break
                own = next(cell for cell in row.cells if cell.quote_id == quote["id"])
                if not own.fact_ids or used.intersection(own.fact_ids):
                    continue
                issue = (
                    "basis"
                    if any(
                        by_fact[value]["kind"] == "subtotal" for value in own.fact_ids
                    )
                    else "scope"
                )
                additional.append(
                    lang["quote_question"].format(
                        firm=safe(quote["name"]),
                        question=lang["question_templates"][issue].format(
                            items=safe(row.label)
                        ),
                    )
                    + " "
                    + cites(own.fact_ids)
                )
                used.update(own.fact_ids)
            questions = priority + additional[: max(0, 4 - len(priority))]
            if questions:
                lines += ["", f"### {safe(quote['name'])}", ""]
                prefix = safe(quote["name"]) + ": "
                texts = [question.removeprefix(prefix) for question in questions]
                lines += ["- " + text[0].upper() + text[1:] for text in texts]
    if profile != "consultant":
        lines += ["", "<!-- pagebreak -->"]
    title = lang["fees"] if profile == "consultant" else lang["matrix"]
    matrix_headers = [
        safe(quote["name"])
        + " ("
        + column.currency
        + ", "
        + (
            matrix_lang["mixed_header"]
            if column.mixed_bases
            else lang["tax"][column.tax_basis]
        )
        + ")"
        for quote, column in zip(quotes, matrix.columns, strict=True)
    ]
    lines += [
        "",
        f"## {title}",
        "",
        "| " + " | ".join([lang["headers"]["item"], *matrix_headers]) + " |",
        "| " + " | ".join("---" for _ in range(len(quotes) + 1)) + " |",
    ]
    for label, row in zip(matrix.labels, matrix.rows, strict=True):
        lines.append(
            "| "
            + " | ".join(
                [safe(label), *[matrix_cell(value, i) for i, value in enumerate(row)]]
            )
            + " |"
        )
    for key, attribute in [
        ("item_total", "item_total_cents"),
        ("quoted_total", "quoted_total_cents"),
        ("difference", "difference_cents"),
    ]:
        cells = []
        for quote, column in zip(quotes, matrix.columns, strict=True):
            amount = getattr(column, attribute)
            notes = []
            if key == "item_total" and column.partial_schedule:
                notes.append(matrix_lang["partial_schedule"])
            if key == "quoted_total":
                if column.converted_total:
                    notes.append(matrix_lang["converted_total"])
                notes.append(cites(calculations[quote["id"]]["headline_fact_ids"]))
            if key == "difference" and amount is not None:
                notes.append(
                    matrix_lang["matches"]
                    if amount == 0
                    else matrix_lang["unreconciled"]
                )
            cells.append(
                " · ".join(
                    filter(
                        None,
                        [
                            f"**{money(amount, column.currency)}**"
                            if amount is not None
                            else matrix_lang["not_checked"],
                            " ".join(notes),
                        ],
                    )
                )
            )
        lines.append("| **" + matrix_lang[key] + "** | " + " | ".join(cells) + " |")
    lines += ["", matrix_lang["explanation"], "", f"## {lang['citations']}", ""]
    for path, quote_id in index.documents:
        if path not in cited_paths:
            continue
        doc = next(doc for doc in documents if doc["path"] == path)
        lines.append(
            f"{index.token_for(path)} "
            + lang["source_key"].format(
                filename=safe(doc["filename"]), firm=safe(by_quote[quote_id]["name"])
            )
        )
    return "\n".join(lines).strip() + "\n"
