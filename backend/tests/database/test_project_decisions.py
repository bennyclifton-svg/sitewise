from app.sitewise.pmp_decisions import extract_decisions

SAMPLE = """\
```pmp-decision
{
  "id": "procurement-route",
  "section": "Procurement",
  "label": "Procurement route",
  "options": [{"value": "traditional", "label": "Traditional"}],
  "selected": "design_construct",
  "source": "agent"
}
```
"""


def test_sync_decisions_respects_locked_mapping() -> None:
    locked = {"procurement-route": "traditional"}
    from app.sitewise.pmp_decisions import restamp_decisions

    restamped = restamp_decisions(SAMPLE, locked)
    decision = extract_decisions(restamped)[0]
    assert decision.selected == "traditional"
    assert decision.source == "user"
