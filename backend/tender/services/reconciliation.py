"""Deterministic quote ledger reconciliation. Invariant I2's core.

Pure module: no settings imports, no I/O. Callers pass ``tol_ratio`` from
``settings.tender_reconciliation_tolerance``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

GST_RATE = 0.10
COUNTABLE_ROLES = frozenset({"contract_component", "pc_allowance", "ps_allowance"})

_SUMMARY_HEADING_RE = re.compile(r"summary|quoted categories", re.IGNORECASE)
_SECTION_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)")
_LABEL_NOISE_RE = re.compile(r"[^a-z0-9]+")

GstTreatment = Literal["inclusive", "exclusive", "inc", "ex", "unknown"]
StatedBasis = Literal["inc", "ex", "unknown"]
ReconcileStatus = Literal["reconciled", "residual", "not_stated", "non_comparable"]


@dataclass
class FigureNode:
    figure_key: str
    parent_figure_key: str | None
    role: str
    gst_basis: str
    is_rollup: bool
    duplicate_of_figure_key: str | None
    amount_cents: int | None
    printed_text: str
    description_raw: str
    page_no: int
    section_path: list[str] = field(default_factory=list)
    counted_in_total: bool = False
    amount_ex_gst_cents: int | None = None
    children: list[FigureNode] = field(default_factory=list)
    parent: FigureNode | None = field(default=None, repr=False)


@dataclass
class LedgerResult:
    figures: list[FigureNode]
    residual_cents: int
    status: ReconcileStatus
    counted_total_cents: int
    computed_ex_gst_cents: int | None
    checks: list[dict]
    gst_line_cents: int | None
    stated_basis: StatedBasis


def _as_nodes(figures: list) -> list[FigureNode]:
    nodes: list[FigureNode] = []
    for fig in figures:
        if isinstance(fig, FigureNode):
            nodes.append(fig)
            continue
        nodes.append(
            FigureNode(
                figure_key=fig.figure_key,
                parent_figure_key=fig.parent_figure_key,
                role=fig.role,
                gst_basis=fig.gst_basis,
                is_rollup=bool(fig.is_rollup),
                duplicate_of_figure_key=fig.duplicate_of_figure_key,
                amount_cents=fig.amount_cents,
                printed_text=fig.printed_text,
                description_raw=fig.description_raw,
                page_no=fig.page_no,
                section_path=list(getattr(fig, "section_path", None) or []),
            )
        )
    return nodes


def map_gst_treatment(gst_treatment: str | None) -> StatedBasis:
    if gst_treatment in ("inclusive", "inc"):
        return "inc"
    if gst_treatment in ("exclusive", "ex"):
        return "ex"
    return "unknown"


def build_tree(figures: list) -> list[FigureNode]:
    """Link ``parent_figure_key`` → parent; return roots (no resolvable parent)."""
    nodes = _as_nodes(figures)
    by_key = {n.figure_key: n for n in nodes}
    for node in nodes:
        node.children = []
        node.parent = None
    roots: list[FigureNode] = []
    for node in nodes:
        parent_key = node.parent_figure_key
        parent = by_key.get(parent_key) if parent_key else None
        if parent is None:
            roots.append(node)
            continue
        node.parent = parent
        parent.children.append(node)
    return roots


def _normalised_label(text: str) -> str:
    return _LABEL_NOISE_RE.sub(" ", (text or "").lower()).strip()


def _leading_section_number(text: str) -> str | None:
    match = _SECTION_NUM_RE.match((text or "").strip())
    return match.group(1) if match else None


def _labels_match(a: FigureNode, b: FigureNode) -> bool:
    sec_a = _leading_section_number(a.description_raw)
    sec_b = _leading_section_number(b.description_raw)
    if sec_a and sec_b and sec_a == sec_b:
        return True
    label_a = _normalised_label(a.description_raw)
    label_b = _normalised_label(b.description_raw)
    if not label_a or not label_b:
        return False
    return SequenceMatcher(None, label_a, label_b).ratio() >= 0.85


def _is_under_summary_section(node: FigureNode) -> bool:
    current: FigureNode | None = node
    while current is not None:
        if _SUMMARY_HEADING_RE.search(current.description_raw or ""):
            return True
        for heading in current.section_path:
            if _SUMMARY_HEADING_RE.search(heading or ""):
                return True
        current = current.parent
    return False


def mark_duplicates(figures: list[FigureNode]) -> None:
    """Mark summary-side reprints as duplicates of body figures."""
    candidates = [
        n for n in figures if n.amount_cents is not None and n.duplicate_of_figure_key is None
    ]
    for i, left in enumerate(candidates):
        for right in candidates[i + 1 :]:
            if left.amount_cents != right.amount_cents:
                continue
            if not _labels_match(left, right):
                continue
            left_summary = _is_under_summary_section(left)
            right_summary = _is_under_summary_section(right)
            if left_summary == right_summary:
                continue
            summary, body = (left, right) if left_summary else (right, left)
            summary.duplicate_of_figure_key = body.figure_key


def to_ex_gst(cents: int | None, basis: str) -> int | None:
    if cents is None:
        return None
    if basis == "inc":
        return round(cents / (1 + GST_RATE))
    if basis == "ex":
        return cents
    return None


def rollup_checks(tree: list[FigureNode], tol: float) -> list[dict]:
    """Per-rollup identity check: printed vs sum of direct children."""
    del tol  # tolerance reserved for callers; checks always emit deltas
    checks: list[dict] = []

    def walk(node: FigureNode) -> None:
        if node.is_rollup and node.children:
            child_sum = sum(c.amount_cents or 0 for c in node.children)
            printed = node.amount_cents or 0
            checks.append(
                {
                    "figure_key": node.figure_key,
                    "printed_cents": printed,
                    "child_sum_cents": child_sum,
                    "delta_cents": printed - child_sum,
                }
            )
        for child in node.children:
            walk(child)

    for root in tree:
        walk(root)
    return checks


def _all_nodes(roots: list[FigureNode]) -> list[FigureNode]:
    out: list[FigureNode] = []

    def walk(node: FigureNode) -> None:
        out.append(node)
        for child in node.children:
            walk(child)

    for root in roots:
        walk(root)
    return out


def _is_countable(node: FigureNode) -> bool:
    return (
        node.duplicate_of_figure_key is None
        and node.role in COUNTABLE_ROLES
        and node.amount_cents is not None
    )


def _frontier_f0(roots: list[FigureNode]) -> list[FigureNode]:
    return list(roots)


def _frontier_f1(roots: list[FigureNode]) -> list[FigureNode]:
    out: list[FigureNode] = []
    for node in roots:
        if node.is_rollup and node.children:
            out.extend(node.children)
        else:
            out.append(node)
    return out


def _frontier_f2(roots: list[FigureNode]) -> list[FigureNode]:
    leaves: list[FigureNode] = []

    def walk(node: FigureNode) -> None:
        if not node.children:
            leaves.append(node)
            return
        for child in node.children:
            walk(child)

    for root in roots:
        walk(root)
    return leaves


def _abs_tol(stated_total_cents: int, tol_ratio: float) -> int:
    return int(round(abs(stated_total_cents) * tol_ratio))


def _frontier_comparable(
    frontier: list[FigureNode],
    stated_basis: StatedBasis,
    stated_total_cents: int,
    gst_line_cents: int | None,
) -> tuple[int, int]:
    """Return (comparable_total_in_stated_basis, residual = comparable - stated)."""
    countable = [n for n in frontier if _is_countable(n)]
    s_inc = sum(n.amount_cents or 0 for n in countable if n.gst_basis == "inc")
    s_ex = sum(n.amount_cents or 0 for n in countable if n.gst_basis == "ex")

    residuals: list[int] = []
    if stated_basis == "inc":
        residuals.append(s_inc + round(s_ex * (1 + GST_RATE)) - stated_total_cents)
        if gst_line_cents is not None:
            residuals.append(s_inc + s_ex + gst_line_cents - stated_total_cents)
    elif stated_basis == "ex":
        residuals.append(s_ex + round(s_inc / (1 + GST_RATE)) - stated_total_cents)
    else:
        # Unknown stated basis: prefer native sum of countable amounts.
        residuals.append(s_inc + s_ex - stated_total_cents)

    best = min(residuals, key=abs)
    return stated_total_cents + best, best


def select_counting_frontier(
    tree: list[FigureNode],
    stated_total_cents: int,
    stated_basis: StatedBasis,
    gst_line_cents: int | None,
    tol_ratio: float,
) -> tuple[list[FigureNode], int]:
    """Pick deepest reconciling frontier; else smallest |residual|."""
    candidates = (
        _frontier_f0(tree),
        _frontier_f1(tree),
        _frontier_f2(tree),
    )
    tol = _abs_tol(stated_total_cents, tol_ratio)

    scored: list[tuple[int, list[FigureNode], int]] = []
    for depth, frontier in enumerate(candidates):
        _comparable, residual = _frontier_comparable(
            frontier, stated_basis, stated_total_cents, gst_line_cents
        )
        scored.append((depth, frontier, residual))

    reconciling = [s for s in scored if abs(s[2]) <= tol]
    if reconciling:
        depth, frontier, residual = max(reconciling, key=lambda s: s[0])
        return [n for n in frontier if _is_countable(n)], residual

    _depth, frontier, residual = min(scored, key=lambda s: abs(s[2]))
    return [n for n in frontier if _is_countable(n)], residual


def reconcile_quote(
    figures: list,
    stated_total_cents: int | None,
    gst_treatment: str | None,
    tol_ratio: float,
    gst_line_cents: int | None = None,
) -> LedgerResult:
    roots = build_tree(figures)
    all_figures = _all_nodes(roots)
    mark_duplicates(all_figures)

    stated_basis = map_gst_treatment(gst_treatment)
    checks = rollup_checks(roots, tol_ratio)

    for node in all_figures:
        node.amount_ex_gst_cents = to_ex_gst(node.amount_cents, node.gst_basis)
        node.counted_in_total = False

    if stated_total_cents is None:
        return LedgerResult(
            figures=all_figures,
            residual_cents=0,
            status="not_stated",
            counted_total_cents=0,
            computed_ex_gst_cents=None,
            checks=checks,
            gst_line_cents=gst_line_cents,
            stated_basis=stated_basis,
        )

    if stated_basis == "unknown":
        return LedgerResult(
            figures=all_figures,
            residual_cents=0,
            status="non_comparable",
            counted_total_cents=0,
            computed_ex_gst_cents=None,
            checks=checks,
            gst_line_cents=gst_line_cents,
            stated_basis=stated_basis,
        )

    frontier, residual = select_counting_frontier(
        roots,
        stated_total_cents,
        stated_basis,
        gst_line_cents,
        tol_ratio,
    )
    counted_keys = {n.figure_key for n in frontier}
    for node in all_figures:
        node.counted_in_total = node.figure_key in counted_keys

    counted_total_cents = sum(n.amount_cents or 0 for n in frontier)
    ex_values = [n.amount_ex_gst_cents for n in frontier]
    computed_ex_gst_cents: int | None
    if frontier and any(v is None for v in ex_values):
        computed_ex_gst_cents = None
    else:
        computed_ex_gst_cents = sum(v or 0 for v in ex_values)

    tol = _abs_tol(stated_total_cents, tol_ratio)
    status: ReconcileStatus = "reconciled" if abs(residual) <= tol else "residual"

    return LedgerResult(
        figures=all_figures,
        residual_cents=residual,
        status=status,
        counted_total_cents=counted_total_cents,
        computed_ex_gst_cents=computed_ex_gst_cents,
        checks=checks,
        gst_line_cents=gst_line_cents,
        stated_basis=stated_basis,
    )
