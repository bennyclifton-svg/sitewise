"""X1 Stage 18: email verbs and action candidates do not mutate canonical rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.database.project import Project
from app.email.models import ProjectEmail, ProjectEmailInterpretation
from app.email.intelligence import ACTION_EXCERPT_MAX
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EMAIL_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SENT_AT = datetime(2026, 8, 19, 21, 0, tzinfo=UTC)


def _email(**overrides) -> ProjectEmail:
    fields = {
        "id": EMAIL_ID,
        "provider": "fake",
        "provider_message_id": "msg-1",
        "provider_thread_id": None,
        "internet_message_id": "<msg-1@example.com>",
        "from_address": "qs@consultant.com",
        "to_addresses": ["pm@owner.com"],
        "cc_addresses": [],
        "subject": "Hello",
        "sent_at": SENT_AT,
        "body_text": "",
        "headers": {},
        "content_hash": "a" * 64,
        "created_at": SENT_AT,
    }
    fields.update(overrides)
    return ProjectEmail(**fields)


def _interpretation(**overrides) -> ProjectEmailInterpretation:
    fields = {
        "email_id": EMAIL_ID,
        "project_id": None,
        "match_confidence": Decimal("0.000"),
        "match_basis": "default",
        "match_reviewed_by_user_id": None,
        "updated_at": SENT_AT,
    }
    fields.update(overrides)
    return ProjectEmailInterpretation(**fields)


def _project() -> Project:
    return Project(
        id=PROJECT_A,
        owner_user_id=USER_ID,
        slug="kavanagh-residence",
        title="Kavanagh Residence",
        workspace_path="04-projects/kavanagh-residence",
        phase="procurement",
        status="active",
        project_metadata={},
        created_at=SENT_AT,
        updated_at=SENT_AT,
    )


def _candidate():
    from app.email.project_matching import ProjectMatchCandidate

    return ProjectMatchCandidate(
        project_id=PROJECT_A,
        slug="kavanagh-residence",
        title="Kavanagh Residence",
        code="KAV-001",
        site_address="14 Wattle Grove, Lindfield NSW 2070",
        client_name="Kavanagh",
    )


class _LinkSession:
    def __init__(
        self,
        *,
        email: ProjectEmail,
        interpretation: ProjectEmailInterpretation | None = None,
        project: Project | None = None,
    ) -> None:
        self.email = email
        self.interpretation = interpretation
        self.project = project

    async def get(self, model, ident):
        if model is ProjectEmail and ident == self.email.id:
            return self.email
        if model is ProjectEmailInterpretation and ident == self.email.id:
            return self.interpretation
        if model is Project and self.project is not None and ident == self.project.id:
            return self.project
        return None

    def add(self, obj) -> None:
        if isinstance(obj, ProjectEmailInterpretation):
            self.interpretation = obj

    async def execute(self, statement):
        _ = statement
        return SimpleNamespace(
            scalar_one_or_none=lambda: None,
            scalars=lambda: SimpleNamespace(all=lambda: []),
        )


class _ImportSession:
    def __init__(self) -> None:
        self.emails: dict[tuple[str, str], dict] = {}
        self.emails_by_id: dict[uuid.UUID, ProjectEmail] = {}
        self.interpretations: dict[uuid.UUID, ProjectEmailInterpretation] = {}

    async def get(self, model, ident):
        if model is ProjectEmail:
            return self.emails_by_id.get(ident)
        if model is ProjectEmailInterpretation:
            return self.interpretations.get(ident)
        return None

    def add(self, obj) -> None:
        if isinstance(obj, ProjectEmailInterpretation):
            self.interpretations[obj.email_id] = obj

    async def execute(self, statement):
        from sqlalchemy.dialects.postgresql import Insert as PGInsert
        from sqlalchemy.sql import Select

        if isinstance(statement, PGInsert):
            params = dict(statement.compile().params)
            table = statement.table.name
            if table == "project_emails":
                key = (params["provider"], params["provider_message_id"])
                if key in self.emails:
                    return SimpleNamespace(scalar_one_or_none=lambda: None)
                self.emails[key] = params
                email = _email(
                    id=params["id"],
                    provider=params["provider"],
                    provider_message_id=params["provider_message_id"],
                    from_address=params["from_address"],
                    subject=params["subject"],
                    sent_at=params.get("sent_at"),
                    body_text=params.get("body_text") or "",
                    headers=params.get("headers") or {},
                    content_hash=params["content_hash"],
                    internet_message_id=params.get("internet_message_id"),
                )
                self.emails_by_id[params["id"]] = email
                return SimpleNamespace(scalar_one_or_none=lambda: params["id"])
            if table == "project_email_interpretations":
                email_id = params["email_id"]
                if email_id in self.interpretations:
                    return SimpleNamespace(scalar_one_or_none=lambda: None)
                interp = _interpretation(
                    email_id=email_id,
                    project_id=params.get("project_id"),
                    match_confidence=params.get("match_confidence"),
                    match_basis=params.get("match_basis"),
                    message_category=params.get("message_category"),
                    actions=params.get("actions") or [],
                )
                self.interpretations[email_id] = interp
                return SimpleNamespace(scalar_one_or_none=lambda: email_id)
        if isinstance(statement, Select):
            params = dict(statement.compile().params)
            provider = params.get("provider_1") or params.get("provider")
            message_id = params.get("provider_message_id_1") or params.get(
                "provider_message_id"
            )
            row = self.emails.get((provider, message_id))
            email_id = None if row is None else row["id"]
            return SimpleNamespace(
                scalar_one=lambda: email_id,
                scalar_one_or_none=lambda: email_id,
                scalars=lambda: SimpleNamespace(all=lambda: []),
            )
        return SimpleNamespace(scalar_one_or_none=lambda: None)


def test_import_emits_email_received_once() -> None:
    from app.email.providers.fake import FakeProvider
    from app.email.schemas import RawProviderMessage
    from app.email.service import import_provider_messages

    provider = FakeProvider()
    provider.add_message(
        RawProviderMessage(
            provider="fake",
            provider_message_id="msg-recv",
            from_address="qs@consultant.com",
            to_addresses=["pm@owner.com"],
            subject="KAV-001 fee proposal",
            sent_at=SENT_AT,
            body_text="Please find attached.",
        )
    )
    session = _ImportSession()
    verbs: list[str] = []

    async def _record(*_args, **kwargs):
        verbs.append(kwargs["verb"])
        return SimpleNamespace(id=uuid.uuid4())

    with (
        patch(
            "app.email.service.load_project_match_candidates",
            new=AsyncMock(return_value=[_candidate()]),
        ),
        patch("app.email.service.record_project_verb", new=_record),
    ):
        run_async(
            import_provider_messages(session, provider=provider, actor_id=USER_ID)
        )
        run_async(
            import_provider_messages(session, provider=provider, actor_id=USER_ID)
        )

    assert verbs.count("email.received") == 1


def test_link_emits_email_linked() -> None:
    from app.email.service import link_email_to_project

    email = _email(subject="Please advise on the ceiling void")
    session = _LinkSession(
        email=email,
        interpretation=_interpretation(),
        project=_project(),
    )
    verbs: list[dict] = []

    async def _record(*_args, **kwargs):
        verbs.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    with patch("app.email.service.record_project_verb", new=_record):
        run_async(
            link_email_to_project(
                session,
                email_id=email.id,
                project_id=PROJECT_A,
                actor_id=USER_ID,
                reason="Kavanagh",
            )
        )

    linked = [item for item in verbs if item["verb"] == "email.linked"]
    assert len(linked) == 1
    assert linked[0]["project_id"] == PROJECT_A
    assert str(email.id) in linked[0]["deduplication_key"]


def test_action_candidate_emits_email_action_detected() -> None:
    from app.email.service import link_email_to_project

    email = _email(
        subject="RFI-012 ceiling void",
        body_text="Please advise the required clearance at grid C/4.",
    )
    session = _LinkSession(
        email=email,
        interpretation=_interpretation(),
        project=_project(),
    )
    verbs: list[dict] = []

    async def _record(*_args, **kwargs):
        verbs.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    with patch("app.email.service.record_project_verb", new=_record):
        run_async(
            link_email_to_project(
                session,
                email_id=email.id,
                project_id=PROJECT_A,
                actor_id=USER_ID,
                reason=None,
            )
        )

    detected = [item for item in verbs if item["verb"] == "email.action_detected"]
    assert detected
    assert detected[0]["metadata"]["signal_type"] in {
        "reply_required",
        "decision_required",
        "commit_date",
        "cost_signal",
        "document_transmittal",
    }
    assert detected[0]["metadata"]["subject_key"] == str(email.id)
    assert "Please find attached." not in detected[0]["message"]
    assert len(detected[0]["message"]) < 200


def test_cost_signal_candidate_does_not_book_an_invoice() -> None:
    from app.email.intelligence import detect_action_candidates
    from app.email.service import link_email_to_project

    email = _email(
        subject="Variation Option B",
        body_text="Proceed with Option B, additional cost $7,800 as a variation.",
    )
    candidates = detect_action_candidates(email)
    assert any(item.type == "cost_signal" for item in candidates)
    session = _LinkSession(
        email=email,
        interpretation=_interpretation(),
        project=_project(),
    )
    book = AsyncMock()
    with (
        patch("app.email.service.record_project_verb", new=AsyncMock()),
        patch("app.cost_plan.invoice_service.book_invoice", new=book),
    ):
        run_async(
            link_email_to_project(
                session,
                email_id=email.id,
                project_id=PROJECT_A,
                actor_id=USER_ID,
                reason=None,
            )
        )
    book.assert_not_called()
    import app.email.intelligence as intel
    import app.email.service as service

    assert "book_invoice" not in Path_read(intel) + Path_read(service)


def test_commit_date_candidate_does_not_write_programme_rows() -> None:
    from app.email.intelligence import detect_action_candidates
    from app.email.service import link_email_to_project

    email = _email(
        subject="IFC issue",
        body_text="We will issue IFC drawings Friday.",
    )
    assert any(item.type == "commit_date" for item in detect_action_candidates(email))
    session = _LinkSession(
        email=email,
        interpretation=_interpretation(),
        project=_project(),
    )
    write_object = AsyncMock()
    update_decision = AsyncMock()
    with (
        patch("app.email.service.record_project_verb", new=AsyncMock()),
        patch(
            "app.projects.project_knowledge.write_shared_project_object",
            new=write_object,
        ),
        patch("app.projects.decisions.update_project_decision", new=update_decision),
    ):
        run_async(
            link_email_to_project(
                session,
                email_id=email.id,
                project_id=PROJECT_A,
                actor_id=USER_ID,
                reason=None,
            )
        )
    write_object.assert_not_called()
    update_decision.assert_not_called()


def test_action_excerpt_is_bounded() -> None:
    from app.email.intelligence import detect_action_candidates

    padding = "lorem ipsum dolor sit amet " * 40
    body = (
        padding
        + "Proceed with Option B, additional cost $7,800 as a variation. "
        + padding
    )
    email = _email(subject="Cost", body_text=body)
    candidates = detect_action_candidates(email)
    cost = next(item for item in candidates if item.type == "cost_signal")
    assert len(cost.excerpt) <= ACTION_EXCERPT_MAX
    assert "additional cost $7,800" in cost.excerpt
    assert cost.excerpt in body or cost.excerpt.rstrip("…") in body


def test_email_action_detected_is_not_a_pulse_attention_type() -> None:
    from app.projects.pulse import PULSE_SIGNAL_TYPES

    assert "email.action_detected" not in PULSE_SIGNAL_TYPES
    assert "action_detected" not in PULSE_SIGNAL_TYPES


def Path_read(module) -> str:
    from pathlib import Path

    return Path(module.__file__).read_text(encoding="utf-8")
