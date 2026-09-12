from decimal import Decimal
from pathlib import Path

import pytest

from app.cost_plan.consultant_appointment import extract_fee_proposal
from app.database.source_document import SourceDocument


ROOT = Path(__file__).resolve().parents[3] / "docs/demo-corpus/seven-hills/02-consultant-procurement"


@pytest.mark.parametrize("folder,firm,discipline,amount", [
    ("architectural-services", "Axis Studio", "Architect", "286000"),
    ("town-planning", "Civic Pattern Planning", "Town Planner", "48000"),
    ("structural-engineering", "Northline Structures", "Structural", "132000"),
    ("building-services-engineering", "Flux Services", "Building Services", "158000"),
])
def test_appointment_uses_explicit_letter_fields_over_machine_metadata(folder, firm, discipline, amount):
    source = next((ROOT / folder / "appointment").glob("*.md"))
    document = SourceDocument(filename=source.name, relative_path=source.name,
        normalized_content=source.read_text(encoding="utf-8"),
        document_metadata={"discipline": "Electrical", "issuing_firm": "Wianamatta Developments Pty Ltd"})
    result = extract_fee_proposal(document)
    assert result.discipline == discipline
    assert result.firm == firm
    assert result.fee_ex_gst == Decimal(amount)
