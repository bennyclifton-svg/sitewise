from app.projects.identity_confidence import score_identity_from_text


def test_strong_address_auto_applies() -> None:
    decisions = score_identity_from_text(
        "Project brief — proposed new dwelling at "
        "14 Wattle Grove, Lindfield NSW 2070"
    )
    address = next(item for item in decisions if item.field == "site_address")
    assert address.value == "14 Wattle Grove, Lindfield NSW 2070"
    assert address.confidence >= 0.85
    assert address.action == "auto_apply"


def test_ambiguous_client_for_phrase_proposes_only() -> None:
    text = (
        "Project: Walsh House, 42 Hargrave Street Paddington NSW 2021\n"
        "Client: Atelier North for David & Emma Walsh\n"
    )
    decisions = score_identity_from_text(text)
    client = next(item for item in decisions if item.field == "client")
    assert client.value == "Atelier North for David & Emma Walsh"
    assert client.action == "propose"
    assert client.confidence < 0.85


def test_clear_to_owners_auto_applies_client() -> None:
    text = (
        "**To:** David & Emma Walsh\n"
        "14 Wattle Grove\n"
        "Lindfield NSW 2070\n"
    )
    decisions = score_identity_from_text(text)
    client = next(item for item in decisions if item.field == "client")
    assert client.value == "David & Emma Walsh"
    assert client.action == "auto_apply"


def test_empty_text_skips() -> None:
    decisions = score_identity_from_text("   ")
    assert all(item.action == "skip" for item in decisions)
