import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.agent.mutation_intent import classify_mutation_intent
from app.agent.turn_context import (
    _DOCUMENT_ACCESS_GUIDANCE,
    _ROLE_GUIDANCE,
    _WEB_RESEARCH_GUIDANCE,
)
from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread
from app.database.session import get_db
from app.main import fastapi_app as app
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
THREAD_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)

BODY = {
    "threadId": str(THREAD_ID),
    "messages": [
        {
            "role": "user",
            "parts": [{"type": "text", "text": "Compare the tender quotes"}],
        }
    ],
}

BODY_WITH_AGENT_MODEL = {
    **BODY,
    "agent_model": "openai:gpt-5.6-sol",
}

BODY_WITH_PI_RUNTIME = {
    **BODY,
    "agent_model": "openai:gpt-5.6-sol",
    "messages": [
        {
            "role": "user",
            "parts": [
                {"type": "text", "text": "what can you tell me about the project"}
            ],
        }
    ],
}


def test_terminal_event_persistence_is_ordered_and_sanitized() -> None:
    events = chat_api._sanitized_terminal_events(
        [
            {"kind": "tool", "tool": "write", "state": "done"},
            {
                "kind": "artefact",
                "title": "Project plan",
                "draftId": "draft-2",
                "version": 2,
                "token": "must-not-persist",
                "prompt": "must-not-persist",
            },
            {
                "kind": "resource",
                "projectId": "project-1",
                "resourceType": "artefact_revision",
                "resourceId": "draft-2",
                "revision": 2,
                "action": "published",
            },
        ]
    )

    assert [event["kind"] for event in events] == ["artefact", "resource"]
    assert events[0]["draftId"] == "draft-2"
    assert "token" not in events[0]
    assert "prompt" not in events[0]


def test_explicit_confirmation_selects_the_matching_pending_profile_proposal() -> None:
    proposal = SimpleNamespace(
        proposed_values={
            "site_address": "42 Hargrave Street, Paddington NSW 2021",
            "client": "David and Emma Walsh",
        }
    )
    snapshot = SimpleNamespace(open_profile_proposals=[proposal])
    intent = classify_mutation_intent(
        "Confirm and set that site address and client on the profile."
    )

    assert (
        chat_api._profile_proposal_to_accept(
            user_text="Confirm and set that site address and client on the profile.",
            mutation_intent=intent,
            snapshot=snapshot,
        )
        is proposal
    )


def test_confirmation_does_not_auto_accept_an_ambiguous_profile_proposal() -> None:
    snapshot = SimpleNamespace(
        open_profile_proposals=[
            SimpleNamespace(proposed_values={"site_address": "42 Hargrave Street"}),
            SimpleNamespace(proposed_values={"site_address": "40 Hargrave Street"}),
        ]
    )
    intent = classify_mutation_intent("Confirm that site address on the profile.")

    assert (
        chat_api._profile_proposal_to_accept(
            user_text="Confirm that site address on the profile.",
            mutation_intent=intent,
            snapshot=snapshot,
        )
        is None
    )


def _thread(
    *,
    owner_id: uuid.UUID = USER_ID,
    project_id: uuid.UUID | None = PROJECT_ID,
    title: str | None = "Test thread",
) -> ChatThread:
    return ChatThread(
        id=THREAD_ID,
        user_id=owner_id,
        project_id=project_id,
        title=title,
        created_at=NOW,
        updated_at=NOW,
    )


def _snapshot():
    return SimpleNamespace(
        schema_version=1,
        content_fingerprint="snapshot-fingerprint",
        profile=SimpleNamespace(profile_revision=1),
        decisions=SimpleNamespace(set_revision=1, items=[], open_count=0),
        evidence=SimpleNamespace(
            fingerprint="evidence-fingerprint",
            active_count=0,
            ingest_failure_count=0,
        ),
        confirmed_inputs={},
        open_profile_proposals=[],
        next_actions=[],
        latest_artefacts=[],
    )


class _SessionContext:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc_info):
        return None


class _SessionFactory:
    def __init__(self, session) -> None:
        self.session = session

    def __call__(self) -> _SessionContext:
        return _SessionContext(self.session)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield mock_session

    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(
        chat_api,
        "get_project_snapshot",
        AsyncMock(return_value=_snapshot()),
    )
    monkeypatch.setattr(
        chat_api,
        "generate_thread_title",
        AsyncMock(return_value="Tender Quote Comparison"),
    )
    monkeypatch.setattr(
        chat_api,
        "replace_thread_title_if_matches",
        AsyncMock(return_value=True),
    )
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_agent_stream_requires_auth(mock_session: AsyncMock) -> None:
    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        response = client.post("/chat/agent/stream", json=BODY)
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_agent_stream_forbidden_for_other_users_thread(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chat_api,
        "get_thread_by_id",
        AsyncMock(return_value=_thread(owner_id=OTHER_USER_ID)),
    )

    response = client.post("/chat/agent/stream", json=BODY)

    assert response.status_code == 403


def test_agent_stream_requires_active_entitlement(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        chat_api,
        "require_active_entitlement",
        AsyncMock(
            side_effect=HTTPException(
                status_code=402,
                detail="Subscription required",
            )
        ),
    )

    response = client.post("/chat/agent/stream", json=BODY)

    assert response.status_code == 402


def test_agent_stream_blocks_over_quota(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(chat_api, "list_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(
            return_value=SimpleNamespace(
                id=PROJECT_ID,
                title="Test project",
                archetype=None,
                user_role=None,
                state=None,
                phase="brief-planning",
                building_class=None,
                work_type=None,
                project_metadata=None,
            )
        ),
    )
    monkeypatch.setattr(
        chat_api,
        "reserve_agent_turn",
        AsyncMock(
            side_effect=HTTPException(
                status_code=402,
                detail="Monthly agent turn quota exceeded.",
            )
        ),
    )

    response = client.post("/chat/agent/stream", json=BODY)

    assert response.status_code == 402


def test_agent_stream_persists_user_then_successful_assistant_message(
    client: TestClient,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    assistant_session = AsyncMock()
    seen: dict[str, str] = {}

    async def fake_create_message(
        session, *, thread_id, role, content, message_data=None
    ):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_pi_turn(
        *,
        prompt,
        mcp_url,
        turn_token,
        cwd,
        provider=None,
        model=None,
    ):
        seen.update(
            {
                "prompt": prompt,
                "mcp_url": mcp_url,
                "turn_token": turn_token,
                "cwd": cwd,
                "provider": provider,
                "model": model,
            }
        )
        yield "Hello"
        yield " there"

    token_mint = Mock(return_value="turn-token")

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "reserve_agent_turn",
        AsyncMock(
            return_value=(
                SimpleNamespace(id=uuid.uuid4()),
                SimpleNamespace(used_turns=13, quota=100, percent=13, warning=False),
                True,
            )
        ),
    )
    monkeypatch.setattr(chat_api, "complete_agent_turn", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(
            return_value=SimpleNamespace(
                id=PROJECT_ID,
                title="Walsh Reno",
                archetype=None,
                user_role="architect-pm",
                state="NSW",
                phase="brief-planning",
                building_class="residential",
                work_type="refurb",
                project_metadata={
                    "taxonomy": {
                        "subclasses": ["house"],
                        "scale": {"gfa_sqm": 200},
                    }
                },
            )
        ),
    )
    monkeypatch.setattr(
        chat_api,
        "list_messages",
        AsyncMock(
            return_value=[
                SimpleNamespace(role="user", content="What quotes do we have?"),
                SimpleNamespace(
                    role="assistant", content="Three structural quotes are on file."
                ),
            ]
        ),
    )
    monkeypatch.setattr(chat_api, "update_thread", AsyncMock(return_value=thread))
    monkeypatch.setattr(
        chat_api,
        "create_message",
        AsyncMock(side_effect=fake_create_message),
    )
    monkeypatch.setattr(chat_api, "mint_turn_token", token_mint)
    monkeypatch.setattr(chat_api, "stream_pi_turn", fake_stream_pi_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(assistant_session),
    )

    with client.stream(
        "POST", "/chat/agent/stream", json=BODY_WITH_AGENT_MODEL
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"text-delta"' in body
    assert "Hello" in body
    assert '"type":"finish"' in body
    assert "[DONE]" in body
    expected_prompt = (
        _ROLE_GUIDANCE + "\n"
        "\n"
        "<project-context>\n"
        f"project_id: {PROJECT_ID}\n"
        "project_title: Walsh Reno\n"
        "classification_source: project_taxonomy\n"
        "building_class: residential\n"
        "work_type: refurb\n"
        "subclasses: House (Class 1a)\n"
        "scale: Site sqm=(not declared), GFA sqm=200, Storeys=(not declared), Bedrooms=(not declared), Garage spaces=(not declared)\n"
        "phase: brief-planning\n"
        "state: NSW\n"
        "site_address: (not declared)\n"
        "client: (not declared)\n"
            "</project-context>\n"
            "\n" + _DOCUMENT_ACCESS_GUIDANCE + "\n"
            "\n" + _WEB_RESEARCH_GUIDANCE + "\n"
            "\n"
        '<project-snapshot schema-version="1">\n'
        "content_fingerprint: snapshot-fingerprint\n"
        "profile_revision: 1\n"
        "decision_set_revision: 1\n"
        "open_decision_count: 0\n"
        "evidence_fingerprint: evidence-fingerprint\n"
        "active_evidence_count: 0\n"
        "ingest_failure_count: 0\n"
        "open_profile_proposals: 0\n"
        "workflow.approved_tender_cost_handoff=needs_input; required_fields=building_class,subclasses,work_type,state; reasons=Cost Plan requires confirmed project context.\n"
        "workflow.consultant_procurement=needs_input; required_fields=building_class,work_type; reasons=Complete the required project profile fields.\n"
        "workflow.contractor_eoi=needs_input; required_fields=building_class,work_type,state; reasons=Complete the required project profile fields.\n"
        "workflow.create_cost_plan=needs_input; required_fields=building_class,subclasses,work_type,state; reasons=Cost Plan requires confirmed project context.\n"
        "workflow.create_pmp=needs_input; required_fields=building_class,work_type,state; reasons=Complete the required project profile fields.\n"
        "workflow.edit_cost_plan=needs_input; required_fields=building_class,subclasses,work_type,state; reasons=Cost Plan requires confirmed project context.\n"
        "workflow.refresh_cost_plan=needs_input; required_fields=building_class,subclasses,work_type,state; reasons=Cost Plan requires confirmed project context.\n"
        "workflow.tender_comparison=needs_input; required_fields=building_class,subclasses,work_type,state; reasons=Tender Comparison requires confirmed Class 1a project context.\n"
        "workflow.trade_procurement=needs_input; required_fields=building_class,work_type,state; reasons=Complete the required project profile fields.\n"
        "workflow.transmittal=supported; required_fields=(none); reasons=A transmittal can be drafted from the files selected in the current document register. It remains unissued until the recipient and issue details are confirmed.\n"
        "workflow.update_pmp=needs_input; required_fields=building_class,work_type,state; reasons=Complete the required project profile fields.\n"
        "site_address=(not declared)\n"
        "client=(not declared)\n"
        "</project-snapshot>\n"
        "\n"
        "<recent-conversation>\n"
        "user: What quotes do we have?\n"
        "assistant: Three structural quotes are on file.\n"
        "</recent-conversation>\n"
        "\n"
        "Compare the tender quotes"
    )
    assert seen == {
        "prompt": expected_prompt,
        "mcp_url": "http://testserver/mcp",
        "turn_token": "turn-token",
        "cwd": str(tmp_path / str(PROJECT_ID)),
        "provider": "openai",
        "model": "gpt-5.6-sol",
    }
    assert (tmp_path / str(PROJECT_ID) / "AGENTS.md").exists()
    token_mint.assert_called_once()
    assert token_mint.call_args.kwargs["user_id"] == USER_ID
    assert token_mint.call_args.kwargs["project_id"] == PROJECT_ID
    assert isinstance(token_mint.call_args.kwargs["turn_id"], uuid.UUID)
    assert mock_session.commit.await_count == 1
    assert assistant_session.commit.await_count == 1

    calls = chat_api.create_message.await_args_list
    assert calls[0].kwargs["role"] == "user"
    assert calls[0].kwargs["content"] == "Compare the tender quotes"
    assert calls[1].kwargs["role"] == "assistant"
    assert calls[1].kwargs["content"] == "Hello there"
    assert calls[1].kwargs["message_data"]["agent"]["runtime"] == "pi"
    assert calls[1].kwargs["message_data"]["agent"]["sourceTrace"] == {
        "context": {"used": True, "label": "Project context"},
        "documents": {"used": False, "tools": []},
        "knowledge": {"used": False, "tools": [], "references": []},
        "tools": [],
        "model": {"used": True, "label": "LLM reasoning"},
    }
    chat_api.generate_thread_title.assert_awaited_once_with(
        "Compare the tender quotes",
        "",
    )
    chat_api.replace_thread_title_if_matches.assert_awaited_once_with(
        assistant_session,
        THREAD_ID,
        expected_title="Compare the tender quotes",
        title="Tender Quote Comparison",
    )


def test_agent_source_trace_classifies_context_knowledge_documents_and_tools() -> None:
    trace = chat_api._agent_source_trace(
        [
            {
                "kind": "tool",
                "tool": "list_platform_knowledge",
                "state": "done",
                "message": "Listed platform knowledge",
            },
            {
                "kind": "tool",
                "tool": "search_platform_knowledge",
                "state": "done",
                "message": "Searched platform knowledge",
            },
            {
                "kind": "tool",
                "tool": "read_platform_knowledge",
                "state": "done",
                "message": "Read platform knowledge",
                "knowledge_path": "seed/nsw/residential-refurb.md",
                "section_ids": ["brief", "budget"],
            },
            {
                "kind": "tool",
                "tool": "find_document_text",
                "state": "done",
                "message": "Searched ingested document text",
            },
            {
                "kind": "tool",
                "tool": "get_document",
                "state": "error",
                "message": "Document read failed",
            },
        ]
    )

    assert trace == {
        "context": {"used": True, "label": "Project context"},
        "documents": {"used": True, "tools": ["find_document_text"]},
        "knowledge": {
            "used": True,
            "tools": [
                "list_platform_knowledge",
                "search_platform_knowledge",
                "read_platform_knowledge",
            ],
            "references": ["seed/nsw/residential-refurb.md"],
        },
        "tools": [
            {
                "name": "list_platform_knowledge",
                "message": "Listed platform knowledge",
            },
            {
                "name": "search_platform_knowledge",
                "message": "Searched platform knowledge",
            },
            {
                "name": "read_platform_knowledge",
                "message": "Read platform knowledge",
                "knowledgePath": "seed/nsw/residential-refurb.md",
                "sectionIds": ["brief", "budget"],
            },
            {
                "name": "find_document_text",
                "message": "Searched ingested document text",
            },
        ],
        "model": {"used": True, "label": "LLM reasoning"},
    }


def test_agent_source_trace_includes_consultant_procurement_sources() -> None:
    trace = chat_api._agent_source_trace(
        [
            {
                "kind": "tool",
                "tool": "draft_consultant_procurement_artifact",
                "state": "done",
                "message": "Created consultant procurement draft",
                "document_count": 1,
                "knowledge_count": 1,
                "forecast_used": True,
                "source_documents": [
                    {
                        "filename": "project-brief.pdf",
                        "relative_path": "04-projects/demo/00-brief/project-brief.pdf",
                    }
                ],
                "platform_knowledge": [
                    {
                        "path": "seed/consultant-procurement.md",
                        "title": "Consultant procurement guide",
                    }
                ],
            }
        ]
    )

    assert trace == {
        "context": {"used": True, "label": "Project context"},
        "documents": {
            "used": True,
            "tools": ["draft_consultant_procurement_artifact"],
            "references": ["04-projects/demo/00-brief/project-brief.pdf"],
        },
        "knowledge": {
            "used": True,
            "tools": ["draft_consultant_procurement_artifact"],
            "references": ["seed/consultant-procurement.md"],
        },
        "tools": [
            {
                "name": "draft_consultant_procurement_artifact",
                "message": "Created consultant procurement draft",
                "documentCount": 1,
                "knowledgeCount": 1,
                "forecastUsed": True,
            }
        ],
        "model": {"used": True, "label": "LLM reasoning"},
    }


def test_agent_source_trace_includes_read_web_source_provenance() -> None:
    source = {
        "url": "https://www.legislation.qld.gov.au/view/html/inforce/current/act-2016-025",
        "title": "Planning Act 2016",
        "publisher": "Queensland Government",
        "jurisdiction": "QLD",
        "authority_class": "official_legislation",
        "source_type": "web_legislation",
        "version_status": "current",
        "effective_date": "29 November 2024",
        "section": "section 8",
        "content_hash": "a" * 64,
        "retrieved_at": "2026-08-08T10:00:00+00:00",
    }

    trace = chat_api._agent_source_trace(
        [
            {
                "kind": "tool",
                "tool": "search_web",
                "state": "done",
                "message": "Searched official web sources",
            },
            {
                "kind": "tool",
                "tool": "read_web_source",
                "state": "done",
                "message": "Read official web source · Planning Act 2016",
                "web_source": source,
            },
        ]
    )

    assert trace["web"] == {
        "used": True,
        "tools": ["search_web", "read_web_source"],
        "sources": [source],
    }
    assert [tool["name"] for tool in trace["tools"]] == [
        "search_web",
        "read_web_source",
    ]


def test_agent_source_trace_marks_successful_web_search_as_used_without_source_read() -> None:
    trace = chat_api._agent_source_trace(
        [
            {
                "kind": "tool",
                "tool": "search_web",
                "state": "done",
                "message": "Searched official web sources",
            },
            {
                "kind": "tool",
                "tool": "read_web_source",
                "state": "error",
                "message": "Official web source read failed",
            },
        ]
    )

    assert trace["web"] == {
        "used": True,
        "tools": ["search_web"],
        "sources": [],
    }


def test_persist_agent_message_writes_web_citations(monkeypatch) -> None:
    turn_id = uuid.uuid4()
    message_id = uuid.uuid4()
    session = AsyncMock()
    create = AsyncMock(
        return_value=ChatMessage(
            id=message_id,
            thread_id=THREAD_ID,
            role="assistant",
            content="Planning response",
            message_data={},
            created_at=NOW,
        )
    )
    persist_web = AsyncMock()
    source = {
        "url": "https://www.legislation.qld.gov.au/current-act",
        "title": "Planning Act 2016",
        "authority_class": "official_legislation",
        "source_type": "web_legislation",
        "version_status": "current",
        "content_hash": "a" * 64,
        "retrieved_at": "2026-08-08T10:00:00+00:00",
    }
    monkeypatch.setattr(chat_api, "create_message", create)
    monkeypatch.setattr(chat_api, "persist_message_web_citations", persist_web)

    run_async(
        chat_api._persist_agent_assistant_message(
            session,
            thread_id=THREAD_ID,
            project_id=PROJECT_ID,
            turn_id=turn_id,
            content="Planning response",
            runtime="pi",
            source_trace={
                "web": {
                    "used": True,
                    "tools": ["read_web_source"],
                    "sources": [source],
                }
            },
        )
    )

    persist_web.assert_awaited_once_with(
        session,
        project_id=PROJECT_ID,
        turn_id=turn_id,
        message_id=message_id,
        sources=[source],
    )


def test_agent_stream_pi_receives_project_context(
    client: TestClient,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    assistant_session = AsyncMock()
    seen: dict[str, str] = {}

    async def fake_create_message(
        session, *, thread_id, role, content, message_data=None
    ):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_pi_turn(
        *, prompt, mcp_url, turn_token, cwd, provider=None, model=None
    ):
        seen.update(
            {
                "prompt": prompt,
                "mcp_url": mcp_url,
                "turn_token": turn_token,
                "cwd": cwd,
                "provider": provider,
                "model": model,
            }
        )
        yield "Walsh Reno is a residential refurbishment."

    token_mint = Mock(return_value="turn-token")

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "reserve_agent_turn",
        AsyncMock(
            return_value=(
                SimpleNamespace(id=uuid.uuid4()),
                SimpleNamespace(used_turns=13, quota=100, percent=13, warning=False),
                True,
            )
        ),
    )
    monkeypatch.setattr(chat_api, "complete_agent_turn", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(
            return_value=SimpleNamespace(
                id=PROJECT_ID,
                title="Walsh Reno",
                archetype=None,
                user_role="architect-pm",
                state="NSW",
                phase="brief-planning",
                building_class="residential",
                work_type="refurb",
                project_metadata={
                    "taxonomy": {
                        "subclasses": ["house"],
                        "scale": {"gfa_sqm": 200},
                    }
                },
            )
        ),
    )
    monkeypatch.setattr(chat_api, "list_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_api, "update_thread", AsyncMock(return_value=thread))
    monkeypatch.setattr(
        chat_api,
        "create_message",
        AsyncMock(side_effect=fake_create_message),
    )
    monkeypatch.setattr(chat_api, "mint_turn_token", token_mint)
    monkeypatch.setattr(chat_api, "stream_pi_turn", fake_stream_pi_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(assistant_session),
    )

    with client.stream(
        "POST", "/chat/agent/stream", json=BODY_WITH_PI_RUNTIME
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert seen["provider"] == "openai"
    assert seen["model"] == "gpt-5.6-sol"
    assert "Walsh Reno is a residential refurbishment." in body
    assert "<project-context>" in seen["prompt"]
    assert "project_title: Walsh Reno" in seen["prompt"]
    assert "classification_source: project_taxonomy" in seen["prompt"]
    assert "building_class: residential" in seen["prompt"]
    assert "work_type: refurb" in seen["prompt"]
    assert "subclasses: House (Class 1a)" in seen["prompt"]
    assert (
        "scale: Site sqm=(not declared), GFA sqm=200, Storeys=(not declared), "
        "Bedrooms=(not declared), Garage spaces=(not declared)"
    ) in seen["prompt"]
    assert "what can you tell me about the project" in seen["prompt"]
    assert seen["mcp_url"] == "http://testserver/mcp"
    assert seen["turn_token"] == "turn-token"
    assert seen["cwd"] == str(tmp_path / str(PROJECT_ID))

    calls = chat_api.create_message.await_args_list
    assert calls[1].kwargs["content"] == "Walsh Reno is a residential refurbishment."
    assert calls[1].kwargs["message_data"]["agent"]["runtime"] == "pi"
    assert (
        calls[1].kwargs["message_data"]["agent"]["sourceTrace"]["context"]["used"]
        is True
    )
    assert (
        calls[1].kwargs["message_data"]["agent"]["sourceTrace"]["model"]["used"] is True
    )


def test_agent_stream_uses_pi_for_profile_enrichment(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    assistant_session = AsyncMock()
    seen_runtimes: list[str] = []

    async def fake_create_message(
        session, *, thread_id, role, content, message_data=None
    ):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_pi_turn(
        *, prompt, mcp_url, turn_token, cwd, provider=None, model=None
    ):
        seen_runtimes.append("pi")
        assert "<profile-enrichment-request>" in prompt
        yield "Proposed evidence-backed profile updates."

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "reserve_agent_turn",
        AsyncMock(
            return_value=(
                SimpleNamespace(id=uuid.uuid4()),
                SimpleNamespace(used_turns=1, quota=100, percent=1, warning=False),
                True,
            )
        ),
    )
    monkeypatch.setattr(chat_api, "complete_agent_turn", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(
            return_value=SimpleNamespace(
                id=PROJECT_ID,
                title="Industrial",
                archetype=None,
                user_role="architect-pm",
                state="NSW",
                phase="brief-planning",
                building_class="industrial",
                work_type="extend",
                project_metadata={"taxonomy": {"subclasses": ["warehouse"]}},
            )
        ),
    )
    monkeypatch.setattr(chat_api, "list_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_api, "update_thread", AsyncMock(return_value=thread))
    monkeypatch.setattr(
        chat_api,
        "create_message",
        AsyncMock(side_effect=fake_create_message),
    )
    monkeypatch.setattr(chat_api, "mint_turn_token", Mock(return_value="turn-token"))
    monkeypatch.setattr(chat_api, "stream_pi_turn", fake_stream_pi_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(assistant_session),
    )

    body = {
        "threadId": str(THREAD_ID),
        "messages": [
            {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "update the project profile to reflect avaliable facts",
                    }
                ],
            }
        ],
    }

    with client.stream("POST", "/chat/agent/stream", json=body) as response:
        stream_body = "".join(response.iter_text())

    assert response.status_code == 200
    assert seen_runtimes == ["pi"]
    assert "Proposed evidence-backed profile updates." in stream_body
    assert (
        chat_api.create_message.await_args_list[1].kwargs["message_data"]["agent"][
            "runtime"
        ]
        == "pi"
    )


def test_agent_stream_uses_pi_for_rfp_request(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    assistant_session = AsyncMock()
    seen_runtimes: list[str] = []

    async def fake_create_message(
        session, *, thread_id, role, content, message_data=None
    ):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_pi_turn(
        *, prompt, mcp_url, turn_token, cwd, provider=None, model=None
    ):
        seen_runtimes.append("pi")
        yield "Queued the Structural Engineer RFP."

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "reserve_agent_turn",
        AsyncMock(
            return_value=(
                SimpleNamespace(id=uuid.uuid4()),
                SimpleNamespace(used_turns=1, quota=100, percent=1, warning=False),
                True,
            )
        ),
    )
    monkeypatch.setattr(chat_api, "complete_agent_turn", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(
            return_value=SimpleNamespace(
                id=PROJECT_ID,
                title="Industrial",
                archetype=None,
                user_role="architect-pm",
                state="NSW",
                phase="brief-planning",
                building_class="industrial",
                work_type="extend",
                project_metadata={"taxonomy": {"subclasses": ["warehouse"]}},
            )
        ),
    )
    monkeypatch.setattr(chat_api, "list_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_api, "update_thread", AsyncMock(return_value=thread))
    monkeypatch.setattr(
        chat_api,
        "create_message",
        AsyncMock(side_effect=fake_create_message),
    )
    monkeypatch.setattr(chat_api, "mint_turn_token", Mock(return_value="turn-token"))
    monkeypatch.setattr(chat_api, "stream_pi_turn", fake_stream_pi_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(assistant_session),
    )

    body = {
        "threadId": str(THREAD_ID),
        "messages": [
            {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "create rfp for structural engineer",
                    }
                ],
            }
        ],
    }

    with client.stream("POST", "/chat/agent/stream", json=body) as response:
        stream_body = "".join(response.iter_text())

    assert response.status_code == 200
    assert seen_runtimes == ["pi"]
    assert "Queued the Structural Engineer RFP." in stream_body
    assert (
        chat_api.create_message.await_args_list[1].kwargs["message_data"]["agent"][
            "runtime"
        ]
        == "pi"
    )


def test_agent_stream_routes_fast_semantic_to_configured_model(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    seen: dict[str, object] = {}
    reserve = AsyncMock(
        return_value=(
            SimpleNamespace(id=uuid.uuid4()),
            SimpleNamespace(used_turns=1, quota=100, percent=1, warning=False),
            True,
        )
    )

    async def fake_stream_pi_turn(
        *, prompt, mcp_url, turn_token, cwd, provider=None, model=None
    ):
        seen["provider"] = provider
        seen["model"] = model
        yield "ok"

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(chat_api, "reserve_agent_turn", reserve)
    monkeypatch.setattr(chat_api, "complete_agent_turn", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(
            return_value=SimpleNamespace(
                id=PROJECT_ID,
                title="Walsh Reno",
                archetype=None,
                user_role="architect-pm",
                state="NSW",
                phase="brief-planning",
                building_class="residential",
                work_type="refurb",
                project_metadata={},
            )
        ),
    )
    monkeypatch.setattr(chat_api, "list_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(chat_api, "update_thread", AsyncMock(return_value=thread))
    monkeypatch.setattr(
        chat_api,
        "create_message",
        AsyncMock(
            return_value=ChatMessage(
                id=uuid.uuid4(),
                thread_id=THREAD_ID,
                role="assistant",
                content="ok",
                message_data={},
                created_at=NOW,
            )
        ),
    )
    monkeypatch.setattr(chat_api, "mint_turn_token", Mock(return_value="turn-token"))
    monkeypatch.setattr(chat_api, "stream_pi_turn", fake_stream_pi_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(AsyncMock()),
    )

    body = {
        "threadId": str(THREAD_ID),
        "messages": [
            {
                "role": "user",
                "parts": [{"type": "text", "text": "Add a suitable kitchen mixer"}],
            }
        ],
    }
    with client.stream("POST", "/chat/agent/stream", json=body) as response:
        "".join(response.iter_text())

    assert response.status_code == 200
    assert seen["provider"] == "openai"
    assert seen["model"] == "gpt-5.6-luna"
    assert reserve.await_args.kwargs["model"] == "gpt-5.6-luna"
    assert reserve.await_args.kwargs["input_context"]["task_route"]["task_class"] == (
        "FAST_SEMANTIC"
    )
    assert reserve.await_args.kwargs["input_context"]["task_route"]["path"] == (
        "fast_semantic"
    )


def test_agent_cancel_requires_thread_owner_and_cancels(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancel = AsyncMock(return_value=True)

    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(chat_api.agent_turn_registry, "cancel", cancel)

    response = client.post(f"/chat/agent/{THREAD_ID}/cancel")

    assert response.status_code == 200
    assert response.json() == {"cancelled": True}
    cancel.assert_awaited_once_with(str(THREAD_ID))
