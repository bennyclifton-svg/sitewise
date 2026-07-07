import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.agent.turn_context import _ROLE_GUIDANCE
from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread
from app.database.session import get_db
from app.main import fastapi_app as app

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
    "agent_model": "openai-codex:gpt-5.5",
}

BODY_WITH_PI_RUNTIME = {
    **BODY,
    "agent_runtime": "pi",
    "messages": [
        {
            "role": "user",
            "parts": [
                {"type": "text", "text": "what can you tell me about the project"}
            ],
        }
    ],
}


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
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(return_value=SimpleNamespace(id=PROJECT_ID)),
    )
    monkeypatch.setattr(
        chat_api,
        "require_turn_within_quota",
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

    async def fake_create_message(session, *, thread_id, role, content, message_data=None):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_hermes_turn(
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
    monkeypatch.setattr(settings, "hermes_model_options", "openai-codex:gpt-5.5")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_turn_within_quota",
        AsyncMock(
            return_value=SimpleNamespace(
                used_turns=12,
                quota=100,
                percent=12,
                warning=False,
            )
        ),
    )
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
    monkeypatch.setattr(chat_api, "stream_hermes_turn", fake_stream_hermes_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(assistant_session),
    )

    with client.stream("POST", "/chat/agent/stream", json=BODY_WITH_AGENT_MODEL) as response:
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
        "scale: GFA sqm=200\n"
        "phase: brief-planning\n"
        "user_role: architect-pm\n"
        "state: NSW\n"
        "</project-context>\n"
        "\n"
        "<document-access>\n"
        "For questions about uploaded source documents, use project document tools before OCR:\n"
        "find_document_text is the first choice for simple keyword or phrase lookups.\n"
        "search_documents finds semantic matches, and get_document reads longer ingested text.\n"
        "For generated Clerk artefacts such as cost plans, PMP drafts, and Excel workbooks,\n"
        "use list_project_files to find the stored file. Read generated markdown drafts with\n"
        "read_workspace_file, and read generated .xlsx workbooks with read_project_workbook.\n"
        "For missing consultant-fee estimates, call forecast_consultant_fees before\n"
        "answering. Only call apply_consultant_fee_forecast when the user asks to apply,\n"
        "write, update, or save the forecast into the cost plan.\n"
        "For consultant procurement drafting requests, call\n"
        "draft_consultant_procurement_artifact. This includes phrases like \"draft a\n"
        "request for fee proposal\", \"draft consultant procurement\", \"prepare an RFP for\n"
        "the structural engineer\", \"get me a fee proposal request for the hydraulic\n"
        "consultant\", and \"prepare scope for BASIX assessor\". Do not answer these as\n"
        "free text only; create the artefact and then tell the user it was created.\n"
        "Generated artefacts are not independent project evidence unless they point to an\n"
        "ingested source_document_id.\n"
        "Do not inspect repository files, run shell commands, or query the database directly\n"
        "to answer questions about uploaded source documents.\n"
        "Only use OCR or document-conversion skills when these tools report text is unavailable,\n"
        "or when the ingested text is clearly garbled or insufficient for the user's question.\n"
        "</document-access>\n"
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
        "provider": "openai-codex",
        "model": "gpt-5.5",
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
    assert calls[1].kwargs["message_data"]["agent"]["runtime"] == "hermes"
    assert calls[1].kwargs["message_data"]["agent"]["sourceTrace"] == {
        "context": {"used": True, "label": "Project context"},
        "documents": {"used": False, "tools": []},
        "knowledge": {"used": False, "tools": [], "references": []},
        "tools": [],
        "model": {"used": True, "label": "LLM reasoning"},
    }


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


def test_agent_stream_pi_runtime_receives_project_context(
    client: TestClient,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    assistant_session = AsyncMock()
    seen: dict[str, str] = {}

    async def fake_create_message(session, *, thread_id, role, content, message_data=None):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_pi_turn(*, prompt, mcp_url, turn_token, cwd):
        seen.update(
            {
                "prompt": prompt,
                "mcp_url": mcp_url,
                "turn_token": turn_token,
                "cwd": cwd,
            }
        )
        yield "Walsh Reno is a residential refurbishment."

    token_mint = Mock(return_value="turn-token")

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(settings, "pi_runtime_enabled", True)
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_turn_within_quota",
        AsyncMock(
            return_value=SimpleNamespace(
                used_turns=12,
                quota=100,
                percent=12,
                warning=False,
            )
        ),
    )
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

    with client.stream("POST", "/chat/agent/stream", json=BODY_WITH_PI_RUNTIME) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "Walsh Reno is a residential refurbishment." in body
    assert "<project-context>" in seen["prompt"]
    assert "project_title: Walsh Reno" in seen["prompt"]
    assert "classification_source: project_taxonomy" in seen["prompt"]
    assert "building_class: residential" in seen["prompt"]
    assert "work_type: refurb" in seen["prompt"]
    assert "subclasses: House (Class 1a)" in seen["prompt"]
    assert "scale: GFA sqm=200" in seen["prompt"]
    assert "what can you tell me about the project" in seen["prompt"]
    assert seen["mcp_url"] == "http://testserver/mcp"
    assert seen["turn_token"] == "turn-token"
    assert seen["cwd"] == str(tmp_path / str(PROJECT_ID))

    calls = chat_api.create_message.await_args_list
    assert calls[1].kwargs["content"] == "Walsh Reno is a residential refurbishment."
    assert calls[1].kwargs["message_data"]["agent"]["runtime"] == "pi"
    assert calls[1].kwargs["message_data"]["agent"]["sourceTrace"]["context"]["used"] is True
    assert calls[1].kwargs["message_data"]["agent"]["sourceTrace"]["model"]["used"] is True


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
