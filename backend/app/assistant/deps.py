import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.grounding.validator import GroundingValidator
from app.retrieval.catalog import CorpusProjectSummary
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters, SourcePassage


@dataclass
class DocumentAgentDeps:
    user_id: uuid.UUID
    thread_id: uuid.UUID
    retriever: DocumentRetriever
    validator: GroundingValidator
    project_catalog: list[CorpusProjectSummary] = field(default_factory=list)
    catalog_loader: Callable[[], Awaitable[list[CorpusProjectSummary]]] | None = None
    initial_passages: list[SourcePassage] = field(default_factory=list)
    filters: RetrievalFilters | None = None
    tool_retrieval_enabled: bool = True
    tool_call_counts: dict[str, int] = field(default_factory=dict)
    tool_call_total_ms: dict[str, int] = field(default_factory=dict)

    def record_tool_call(self, name: str, elapsed_ms: int) -> None:
        self.tool_call_counts[name] = self.tool_call_counts.get(name, 0) + 1
        self.tool_call_total_ms[name] = (
            self.tool_call_total_ms.get(name, 0) + elapsed_ms
        )

    def tool_call_summary(self) -> dict[str, dict[str, int]]:
        return {
            name: {
                "count": count,
                "total_ms": self.tool_call_total_ms.get(name, 0),
            }
            for name, count in self.tool_call_counts.items()
        }
