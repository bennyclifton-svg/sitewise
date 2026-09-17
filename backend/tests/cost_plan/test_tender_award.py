from types import SimpleNamespace
from decimal import Decimal

import pytest

from app.cost_plan.tender_award import AwardedTenderLine, awarded_tender_operations


def line(amount="10.00", key="roof"):
    return AwardedTenderLine(item_key=key, description="Roof work", amount_ex_gst=amount,
                             source_location="page 1, roofing")


def operations(lines, total="20.00"):
    state = SimpleNamespace(items=[SimpleNamespace(item_key="roof", source_refs=[], paid=Decimal("0"))])
    return awarded_tender_operations(state, lines=lines, contract_total_ex_gst=total,
                                     contractor="Kaposi", source={"document_id": "doc"})


def test_groups_lines_and_sets_contract_without_overwriting_budget_or_paid():
    second = line().model_copy(update={"source_location": "page 2, roofing"})
    result = operations([line(), second])
    assert len(result) == 1
    assert Decimal(result[0].values["committed"]) == Decimal("20")
    assert Decimal(result[0].values["forecast"]) == Decimal("20")
    assert "budget" not in result[0].values
    assert "paid" not in result[0].values
    assert len(result[0].values["source_refs"][0]["lines"]) == 2


def test_rejects_unreconciled_total_before_producing_operations():
    with pytest.raises(ValueError, match="Resolve missing items, margin or GST"):
        operations([line()])


def test_rejects_unknown_row():
    with pytest.raises(ValueError, match="Unknown Cost Plan item"):
        operations([line("20.00", "missing")])


def test_rejects_double_counted_source_line():
    with pytest.raises(ValueError, match="mapped more than once"):
        operations([line(), line()])


@pytest.mark.parametrize("total", ["invalid", "NaN", "Infinity", "-1", "1e999", "20.001"])
def test_rejects_invalid_contract_total(total):
    with pytest.raises(ValueError, match="Contract total"):
        operations([line()], total)


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1", "0.001", 1.5])
def test_rejects_invalid_money(amount):
    with pytest.raises(ValueError):
        line(amount)
