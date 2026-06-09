import uuid
from unittest.mock import MagicMock

from app.assistant.deps import DocumentAgentDeps


def test_document_agent_deps_summarizes_tool_calls() -> None:
    deps = DocumentAgentDeps(
        user_id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        retriever=MagicMock(),
        validator=MagicMock(),
    )

    deps.record_tool_call("search_documents", 1200)
    deps.record_tool_call("search_documents", 800)
    deps.record_tool_call("read_chunk", 40)

    assert deps.tool_call_summary() == {
        "search_documents": {"count": 2, "total_ms": 2000},
        "read_chunk": {"count": 1, "total_ms": 40},
    }
