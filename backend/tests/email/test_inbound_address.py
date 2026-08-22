"""The address shown to the user must be the one the resolver accepts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.config import settings
from app.email.alias_names import inbound_address_for_slug
from app.email.inbound import project_code_from_alias
from app.schemas.projects import ProjectSummary
from app.sitewise.gate import OverlayStatus


def _summary(slug: str) -> ProjectSummary:
    return ProjectSummary(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        slug=slug,
        title="Newtown Extension",
        workspace_path="projects/newtown-extension-2",
        phase="design",
        archetype=None,
        building_class=None,
        work_type=None,
        user_role=None,
        state=None,
        status="active",
        overlay_status=OverlayStatus(ready=True, missing=[], invalid=[]),
        updated_at=datetime.now(UTC),
    )


def test_address_uses_the_configured_inbound_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    assert inbound_address_for_slug("newtown-extension-2") == (
        "newtown-extension-2@sitewise.au"
    )


def test_address_follows_a_domain_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "email_inbound_domain", "in.sitewise.au")
    assert inbound_address_for_slug("kavanagh") == "kavanagh@in.sitewise.au"


def test_project_summary_exposes_the_inbound_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    payload = _summary("newtown-extension-2").model_dump()
    assert payload["inbound_address"] == "newtown-extension-2@sitewise.au"


def test_the_advertised_address_round_trips_through_the_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The UI must never advertise an address the resolver would 404."""
    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    for slug in ("newtown-extension-2", "kavanagh", "walsh-reno", "61-rail-station"):
        advertised = _summary(slug).model_dump()["inbound_address"]
        assert project_code_from_alias(advertised) == slug


def test_reserved_local_parts_are_not_advertised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A project slugged 'support' would collide with a human inbox."""
    monkeypatch.setattr(settings, "email_inbound_domain", "sitewise.au")
    assert _summary("support").model_dump()["inbound_address"] is None
    assert _summary("admin").model_dump()["inbound_address"] is None
