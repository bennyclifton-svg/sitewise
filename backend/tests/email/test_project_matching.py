"""X1 Stage 17: Python owns email-to-project match; user outranks machine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.database.project import Project
from app.email.models import ProjectEmail, ProjectEmailAttachment, ProjectEmailInterpretation
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
EMAIL_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SENT_AT = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


def _email(**overrides) -> ProjectEmail:
    fields = {
        "id": EMAIL_ID,
        "provider": "fake",
        "provider_message_id": "msg-1",
        "provider_thread_id": None,
        "internet_message_id": "<msg-1@example.com>",
        "from_address": "unknown@example.net",
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


def _candidate(project_id: uuid.UUID, **overrides):
    from app.email.project_matching import ProjectMatchCandidate

    fields = {
        "project_id": project_id,
        "slug": "kavanagh-residence",
        "title": "Kavanagh Residence",
        "code": "KAV-001",
        "site_address": "14 Wattle Grove, Lindfield NSW 2070",
        "client_name": "Kavanagh",
        "email_domains": (),
        "stored_addresses": (),
        "alias_hit": False,
    }
    fields.update(overrides)
    return ProjectMatchCandidate(**fields)


def test_user_override_outranks_thread_and_subject() -> None:
    from app.email.project_matching import ProjectMatch, match_project

    email = _email(subject="KAV-001 fee proposal")
    result = match_project(
        email=email,
        candidates=[_candidate(PROJECT_A), _candidate(PROJECT_B, slug="other", title="Other", code="OTH-1")],
        prior_thread_project_id=PROJECT_A,
        user_override=ProjectMatch(project_id=PROJECT_B, confidence=1.0, basis="user"),
    )
    assert result.project_id == PROJECT_B
    assert result.basis == "user"
    assert result.confidence == 1.0


def test_thread_association_wins_over_subject() -> None:
    from app.email.project_matching import match_project

    email = _email(subject="KAV-001 fee proposal", provider_thread_id="thread-b")
    result = match_project(
        email=email,
        candidates=[_candidate(PROJECT_A), _candidate(PROJECT_B, slug="other", title="Other", code="OTH-1")],
        prior_thread_project_id=PROJECT_B,
        user_override=None,
    )
    assert result.project_id == PROJECT_B
    assert result.basis == "thread"
    assert result.confidence >= 0.65


def test_unknown_sender_is_default_with_null_project() -> None:
    from app.email.project_matching import match_project

    email = _email(from_address="stranger@unknown.example", subject="Lunch tomorrow?")
    result = match_project(
        email=email,
        candidates=[_candidate(PROJECT_A)],
        prior_thread_project_id=None,
        user_override=None,
    )
    assert result.project_id is None
    assert result.basis == "default"
    assert result.confidence < 0.65


def test_low_confidence_subject_match_is_below_review_threshold() -> None:
    from app.email.project_matching import match_project
    from ingest.router import REVIEW_CONFIDENCE_MIN

    email = _email(subject="Re: Grove")
    result = match_project(
        email=email,
        candidates=[_candidate(PROJECT_A)],
        prior_thread_project_id=None,
        user_override=None,
    )
    assert result.project_id == PROJECT_A
    assert result.basis == "subject"
    assert result.confidence < REVIEW_CONFIDENCE_MIN
    assert REVIEW_CONFIDENCE_MIN == 0.65


def _project(project_id: uuid.UUID) -> Project:
    return Project(
        id=project_id,
        owner_user_id=USER_ID,
        slug="kavanagh-residence",
        title="Kavanagh Residence",
        workspace_path="04-projects/kavanagh-residence",
        phase="procurement",
        status="active",
        project_metadata={"taxonomy": {"site_address": "14 Wattle Grove, Lindfield NSW 2070"}},
        created_at=SENT_AT,
        updated_at=SENT_AT,
    )


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


class _LinkSession:
    def __init__(
        self,
        *,
        email: ProjectEmail,
        interpretation: ProjectEmailInterpretation | None = None,
        project: Project | None = None,
        attachments: list[ProjectEmailAttachment] | None = None,
    ) -> None:
        self.email = email
        self.interpretation = interpretation
        self.project = project
        self.attachments = attachments or []
        self.added: list[object] = []

    async def get(self, model, ident):
        if model is ProjectEmail and ident == self.email.id:
            return self.email
        if model is ProjectEmailInterpretation and ident == self.email.id:
            return self.interpretation
        if model is Project and self.project is not None and ident == self.project.id:
            return self.project
        return None

    def add(self, obj) -> None:
        self.added.append(obj)
        if isinstance(obj, ProjectEmailInterpretation):
            self.interpretation = obj

    async def execute(self, statement):
        from sqlalchemy.sql import Select

        if isinstance(statement, Select):
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: list(self.attachments)),
                scalar_one_or_none=lambda: None,
            )
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class _ImportMatchSession:
    def __init__(self) -> None:
        self.emails: dict[tuple[str, str], dict] = {}
        self.emails_by_id: dict[uuid.UUID, ProjectEmail] = {}
        self.interpretations: dict[uuid.UUID, ProjectEmailInterpretation] = {}
        self.attachments: list[dict] = []

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
                    provider_thread_id=params.get("provider_thread_id"),
                    internet_message_id=params.get("internet_message_id"),
                    from_address=params["from_address"],
                    to_addresses=params.get("to_addresses") or [],
                    cc_addresses=params.get("cc_addresses") or [],
                    subject=params["subject"],
                    sent_at=params.get("sent_at"),
                    body_text=params.get("body_text") or "",
                    headers=params.get("headers") or {},
                    content_hash=params["content_hash"],
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
                    match_reviewed_by_user_id=params.get("match_reviewed_by_user_id"),
                )
                self.interpretations[email_id] = interp
                return SimpleNamespace(scalar_one_or_none=lambda: email_id)
            if table == "project_email_attachments":
                self.attachments.append(params)
                return SimpleNamespace(scalar_one_or_none=lambda: params.get("id"))
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
        return SimpleNamespace(scalar_one_or_none=lambda: None, scalars=lambda: SimpleNamespace(all=lambda: []))


class _ThreadLookupSession(_LinkSession):
    def __init__(
        self,
        *,
        original: ProjectEmail,
        reply: ProjectEmail,
        original_project_id: uuid.UUID,
    ) -> None:
        super().__init__(
            email=reply,
            interpretation=_interpretation(email_id=reply.id),
        )
        self.original = original
        self.original_project_id = original_project_id

    async def execute(self, statement):
        from sqlalchemy.sql import Select

        if isinstance(statement, Select):
            compiled = str(statement.compile())
            if "provider_thread_id" in compiled:
                return SimpleNamespace(
                    scalar_one_or_none=lambda: self.original_project_id,
                    scalars=lambda: SimpleNamespace(all=lambda: []),
                )
        return await super().execute(statement)



def test_reimport_does_not_reset_a_user_link() -> None:
    from app.email.providers.fake import FakeProvider
    from app.email.schemas import RawProviderMessage
    from app.email.service import import_provider_messages, link_email_to_project

    provider = FakeProvider()
    provider.add_message(
        RawProviderMessage(
            provider="fake",
            provider_message_id="msg-user-link",
            from_address="qs@consultant.com",
            to_addresses=["pm@owner.com"],
            subject="Fee proposal",
            sent_at=SENT_AT,
            body_text="Please find attached.",
        )
    )
    session = _ImportMatchSession()
    run_async(import_provider_messages(session, provider=provider, actor_id=None))
    email_id = next(iter(session.emails_by_id))
    assert session.interpretations[email_id].match_basis == "default"
    assert session.interpretations[email_id].project_id is None

    run_async(
        link_email_to_project(
            session,
            email_id=email_id,
            project_id=PROJECT_A,
            actor_id=USER_ID,
            reason="this is Kavanagh",
        )
    )
    assert session.interpretations[email_id].match_basis == "user"
    assert session.interpretations[email_id].project_id == PROJECT_A
    raw_subject = session.emails_by_id[email_id].subject

    run_async(import_provider_messages(session, provider=provider, actor_id=None))
    assert session.interpretations[email_id].match_basis == "user"
    assert session.interpretations[email_id].project_id == PROJECT_A
    assert session.interpretations[email_id].match_reviewed_by_user_id == USER_ID
    assert session.emails_by_id[email_id].subject == raw_subject


def test_rematch_refuses_to_downgrade_a_user_basis() -> None:
    from app.email.service import rematch_email

    email = _email(subject="KAV-001 fee proposal")
    session = _LinkSession(
        email=email,
        interpretation=_interpretation(
            project_id=PROJECT_B,
            match_basis="user",
            match_confidence=Decimal("1.000"),
            match_reviewed_by_user_id=USER_ID,
        ),
    )
    result = run_async(
        rematch_email(
            session,
            email_id=email.id,
            candidates=[_candidate(PROJECT_A)],
            prior_thread_project_id=PROJECT_A,
        )
    )
    assert result.match_basis == "user"
    assert result.project_id == PROJECT_B
    assert result.match_reviewed_by_user_id == USER_ID


def test_link_email_does_not_rewrite_raw_subject() -> None:
    from app.email.service import link_email_to_project

    email = _email(subject="Original subject must survive")
    session = _LinkSession(email=email, interpretation=_interpretation())
    run_async(
        link_email_to_project(
            session,
            email_id=email.id,
            project_id=PROJECT_A,
            actor_id=USER_ID,
            reason=None,
        )
    )
    assert email.subject == "Original subject must survive"
    assert email.body_text == ""
    assert session.interpretation is not None
    assert session.interpretation.match_basis == "user"
    assert session.interpretation.match_confidence == Decimal("1.0")
    assert session.interpretation.project_id == PROJECT_A


def test_link_on_another_project_returns_404() -> None:
    from app.auth.dependencies import CurrentUser, get_current_user
    from app.database.session import get_db
    from app.main import fastapi_app as app

    email = _email()
    interpretation = _interpretation(
        project_id=PROJECT_A,
        match_basis="user",
        match_confidence=Decimal("1.000"),
        match_reviewed_by_user_id=USER_ID,
    )
    session = _LinkSession(
        email=email,
        interpretation=interpretation,
        project=_project(PROJECT_B),
    )

    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with (
        patch(
            "app.api.project_emails.get_project",
            new=AsyncMock(return_value=_project(PROJECT_B)),
        ),
        patch("app.api.project_emails.require_active_entitlement", new=AsyncMock()),
        TestClient(app) as client,
    ):
        response = client.post(
            f"/projects/{PROJECT_B}/emails/{EMAIL_ID}/link",
            json={"reason": "wrong project"},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.status_code != 403


def test_low_confidence_match_does_not_auto_ingest_attachments() -> None:
    from app.email.service import rematch_email

    email = _email(subject="Re: Grove")
    attachment = ProjectEmailAttachment(
        id=uuid.uuid4(),
        email_id=email.id,
        provider_attachment_id="att-1",
        filename="invoice.pdf",
        content_type="application_pdf",
        size_bytes=12,
    )
    session = _LinkSession(
        email=email,
        interpretation=_interpretation(),
        project=_project(PROJECT_A),
        attachments=[attachment],
    )
    ingest = AsyncMock()
    with patch("app.email.service.ingest_email_attachment", new=ingest):
        result = run_async(
            rematch_email(
                session,
                email_id=email.id,
                candidates=[_candidate(PROJECT_A)],
                prior_thread_project_id=None,
                actor_id=USER_ID,
            )
        )
    assert result.match_basis == "subject"
    assert result.match_confidence is not None
    assert result.match_confidence < Decimal("0.65")
    ingest.assert_not_called()


def test_reply_in_matched_thread_inherits_project() -> None:
    from app.email.project_matching import thread_key
    from app.email.service import lookup_prior_thread_project_id, rematch_email

    original = _email(
        id=uuid.uuid4(),
        provider_message_id="msg-orig",
        provider_thread_id="thread-17",
        internet_message_id="<orig@example.com>",
        subject="KAV-001 fee proposal",
    )
    reply = _email(
        id=uuid.uuid4(),
        provider_message_id="msg-reply",
        provider_thread_id="thread-17",
        internet_message_id="<reply@example.com>",
        from_address="stranger@unknown.example",
        subject="Re: that",
    )
    assert thread_key(original) == thread_key(reply)

    session = _ThreadLookupSession(
        original=original,
        reply=reply,
        original_project_id=PROJECT_A,
    )
    prior = run_async(lookup_prior_thread_project_id(session, reply))
    assert prior == PROJECT_A
    result = run_async(
        rematch_email(
            session,
            email_id=reply.id,
            candidates=[_candidate(PROJECT_A)],
            prior_thread_project_id=prior,
        )
    )
    assert result.project_id == PROJECT_A
    assert result.match_basis == "thread"
    assert result.match_reviewed_by_user_id is None


