from __future__ import annotations

from app.sitewise.cost_plan_lines import cost_plan_lines
from tests.sitewise.factories import commercial_fitout_project, fitout_evidence_pack


def test_fitout_keeps_every_unpriced_row() -> None:
    line_set = cost_plan_lines(commercial_fitout_project(), fitout_evidence_pack())

    codes = [line.cost_code for line in line_set.lines]
    assert codes == [str(n) for n in range(1, 30)]
    assert sum(1 for line in line_set.lines if line.budget is None) >= 25


def test_basis_key_dedupes_status_basis_pairs_in_first_appearance_order() -> None:
    line_set = cost_plan_lines(commercial_fitout_project(), fitout_evidence_pack())

    assert line_set.basis_key[0].number == 1
    assert line_set.basis_key[0].status == "Approved"
    assert line_set.basis_key[0].basis == "Engagement letter"

    pairs = [(entry.status, entry.basis) for entry in line_set.basis_key]
    assert len(pairs) == len(set(pairs))

    by_number = {entry.number: entry for entry in line_set.basis_key}
    for line in line_set.lines:
        entry = by_number[line.basis_key]
        assert (entry.status, entry.basis) == (line.status, line.basis)
