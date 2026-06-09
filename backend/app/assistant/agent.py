import json
import time
import uuid
from functools import lru_cache
from pathlib import Path

import structlog
from pydantic_ai import Agent, RunContext

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.retrieval.catalog import (
    CorpusProjectSummary,
    format_catalog_for_prompt,
    catalog_to_passages,
)
from app.config import settings
from app.retrieval.schemas import RetrievalFilters, SourcePassage

_PASSAGE_JSON = {"separators": (",", ":"), "ensure_ascii": True}

_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"
logger = structlog.get_logger(__name__)


def load_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def format_passages_for_prompt(passages: list[SourcePassage]) -> str:
    if not passages:
        return "No initial passages were retrieved for this query."

    limit = settings.assistant_context_passage_limit
    content_chars = settings.assistant_passage_content_chars
    blocks: list[str] = []
    for passage in passages[:limit]:
        if (passage.chunk_metadata or {}).get("whole_document"):
            passage_chars = settings.whole_document_content_chars
        else:
            passage_chars = content_chars
        blocks.append(
            json.dumps(
        {
            "chunk_id": str(passage.chunk_id),
            "document_id": str(passage.document_id),
            "filename": passage.filename,
            "project": passage.project,
            "source_type": passage.source_type,
            "knowledge_scope": (passage.document_metadata or {}).get("knowledge_scope"),
            "page_or_section": passage.page_or_section,
            "relative_path": passage.relative_path,
            "content": passage.content[:passage_chars],
        },
                **_PASSAGE_JSON,
            )
        )
    omitted = len(passages) - limit
    suffix = ""
    if omitted > 0:
        suffix = f"\n({omitted} more passages omitted.)"
    return "Initial retrieved passages:\n\n" + "\n".join(blocks) + suffix


_WHOLE_DOCUMENT_TURN_ADDENDUM = """
This turn has no tools. Answer only from the initial retrieved passages above.
Include at least one Citation for every factual claim, using chunk_id values exactly as given.
Set evidence_sufficient to false if those passages do not clearly answer the question.
"""


def format_turn_instructions(
    catalog: list[CorpusProjectSummary] | None,
    passages: list[SourcePassage],
    *,
    tools_disabled: bool = False,
) -> str:
    blocks: list[str] = []
    if catalog is not None:
        blocks.append(format_catalog_for_prompt(catalog))
    blocks.append(format_passages_for_prompt(passages))
    if tools_disabled:
        blocks.append(_WHOLE_DOCUMENT_TURN_ADDENDUM.strip())
    return "\n\n".join(blocks)


def _serialize_passages(passages: list[SourcePassage]) -> str:
    payload = [
        {
            "chunk_id": str(p.chunk_id),
            "document_id": str(p.document_id),
            "filename": p.filename,
            "project": p.project,
            "source_type": p.source_type,
            "knowledge_scope": (p.document_metadata or {}).get("knowledge_scope"),
            "page_or_section": p.page_or_section,
            "excerpt": p.content[:300],
        }
        for p in passages
    ]
    return json.dumps(payload, **_PASSAGE_JSON)


@lru_cache
def get_document_agent() -> Agent[DocumentAgentDeps, GroundedAnswer]:
    return Agent(
        f"openai-chat:{settings.openai_chat_model}",
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=load_instructions(),
        defer_model_check=True,
    )


agent = get_document_agent()


@lru_cache
def get_platform_qa_agent() -> Agent[DocumentAgentDeps, GroundedAnswer]:
    """Single-pass LLM for seed/doctrine turns — no retrieval tools."""
    return Agent(
        f"openai-chat:{settings.openai_chat_model}",
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=load_instructions(),
        defer_model_check=True,
    )


platform_qa_agent = get_platform_qa_agent()


def _primary_whole_document_passage(passages: list[SourcePassage]) -> SourcePassage:
    doctrine = [p for p in passages if p.source_type == "doctrine"]
    if doctrine:
        return doctrine[0]
    return max(passages, key=lambda p: p.score or 0.0)


def repair_missing_platform_citations(
    answer: GroundedAnswer,
    passages: list[SourcePassage],
) -> GroundedAnswer:
    if answer.citations or not answer.evidence_sufficient or not passages:
        return answer
    passage = _primary_whole_document_passage(passages)
    return answer.model_copy(
        update={
            "citations": [
                Citation(
                    chunk_id=passage.chunk_id,
                    document_id=passage.document_id,
                    excerpt=passage.content[:300].strip(),
                    filename=passage.filename,
                    project=passage.project,
                    phase=passage.phase,
                    source_type=passage.source_type,
                    label=EvidenceLabel.FACT,
                )
            ]
        }
    )


_TOOL_RETRIEVAL_DISABLED = (
    "Additional tool retrieval is disabled for this turn. "
    "Answer from the initial retrieved passages already provided in the turn context."
)


@agent.tool
async def list_corpus_projects(ctx: RunContext[DocumentAgentDeps]) -> str:
    """Return the authoritative list of indexed corpus projects with sample chunk_ids for citation."""
    if not ctx.deps.tool_retrieval_enabled:
        return _TOOL_RETRIEVAL_DISABLED
    tool_start = time.perf_counter()
    project_count = 0
    try:
        if not ctx.deps.project_catalog and ctx.deps.catalog_loader is not None:
            ctx.deps.project_catalog = await ctx.deps.catalog_loader()
        project_count = len(ctx.deps.project_catalog)
        if not ctx.deps.project_catalog:
            return "No projects are indexed in the corpus yet."
        ctx.deps.validator.register(catalog_to_passages(ctx.deps.project_catalog))
        return format_catalog_for_prompt(ctx.deps.project_catalog)
    finally:
        elapsed_ms = int((time.perf_counter() - tool_start) * 1000)
        ctx.deps.record_tool_call("list_corpus_projects", elapsed_ms)
        logger.info(
            "assistant_tool_call_complete",
            tool="list_corpus_projects",
            user_id=str(ctx.deps.user_id),
            thread_id=str(ctx.deps.thread_id),
            elapsed_ms=elapsed_ms,
            project_count=project_count,
        )


@agent.tool
async def search_documents(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    project: str | None = None,
    source_type: str | None = None,
    procurement_stage: str | None = None,
    tenderer_id: str | None = None,
) -> str:
    """Hybrid search over the Clerk corpus. Returns chunk summaries with chunk_id values for citation."""
    if not ctx.deps.tool_retrieval_enabled:
        return _TOOL_RETRIEVAL_DISABLED
    tool_start = time.perf_counter()
    result_count = 0
    filters = RetrievalFilters(
        project=project or (ctx.deps.filters.project if ctx.deps.filters else None),
        active_project=ctx.deps.filters.active_project if ctx.deps.filters else None,
        include_platform_knowledge=(
            ctx.deps.filters.include_platform_knowledge if ctx.deps.filters else False
        ),
        cross_project=ctx.deps.filters.cross_project if ctx.deps.filters else False,
        source_type=source_type
        or (ctx.deps.filters.source_type if ctx.deps.filters else None),
        procurement_stage=procurement_stage
        or (ctx.deps.filters.procurement_stage if ctx.deps.filters else None),
        tenderer_id=tenderer_id
        or (ctx.deps.filters.tenderer_id if ctx.deps.filters else None),
        phase=ctx.deps.filters.phase if ctx.deps.filters else None,
        document_class=ctx.deps.filters.document_class if ctx.deps.filters else None,
    )
    try:
        passages = await ctx.deps.retriever.retrieve(
            query,
            filters=filters,
            limit=settings.assistant_context_passage_limit,
            include_neighbours=False,
        )
        result_count = len(passages)
        ctx.deps.validator.register(passages)
        if not passages:
            return "No matching passages found for that query and filter set."
        return _serialize_passages(passages[: settings.assistant_context_passage_limit])
    finally:
        elapsed_ms = int((time.perf_counter() - tool_start) * 1000)
        ctx.deps.record_tool_call("search_documents", elapsed_ms)
        logger.info(
            "assistant_tool_call_complete",
            tool="search_documents",
            user_id=str(ctx.deps.user_id),
            thread_id=str(ctx.deps.thread_id),
            elapsed_ms=elapsed_ms,
            result_count=result_count,
            query_length=len(query.strip()),
            filters=filters.model_dump(exclude_none=True),
        )


@agent.tool
async def read_chunk(ctx: RunContext[DocumentAgentDeps], chunk_id: str) -> str:
    """Load a single chunk by chunk_id, including neighbouring chunks for context."""
    if not ctx.deps.tool_retrieval_enabled:
        return _TOOL_RETRIEVAL_DISABLED
    tool_start = time.perf_counter()
    found = False
    try:
        try:
            parsed_id = uuid.UUID(chunk_id)
        except ValueError:
            return f"Invalid chunk_id: {chunk_id}"

        passage = await ctx.deps.retriever.read_chunk(parsed_id)
        if passage is None:
            return f"Chunk not found: {chunk_id}"

        found = True
        ctx.deps.validator.register([passage])
        content = passage.content[:2500]
        truncated = len(passage.content) > 2500
        return json.dumps(
            {
                "chunk_id": str(passage.chunk_id),
                "document_id": str(passage.document_id),
                "filename": passage.filename,
                "project": passage.project,
                "source_type": passage.source_type,
                "page_or_section": passage.page_or_section,
                "content": content,
                "content_truncated": truncated,
                "neighbours": [
                    {
                        "chunk_id": str(n.chunk_id),
                        "chunk_index": n.chunk_index,
                        "page_or_section": n.page_or_section,
                        "content": n.content[:500],
                    }
                    for n in passage.neighbours
                ],
            },
            **_PASSAGE_JSON,
        )
    finally:
        elapsed_ms = int((time.perf_counter() - tool_start) * 1000)
        ctx.deps.record_tool_call("read_chunk", elapsed_ms)
        logger.info(
            "assistant_tool_call_complete",
            tool="read_chunk",
            user_id=str(ctx.deps.user_id),
            thread_id=str(ctx.deps.thread_id),
            elapsed_ms=elapsed_ms,
            found=found,
        )


@agent.tool
async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps], chunk_id: str
) -> str:
    """Return neighbouring chunks around a given chunk_id for grounding context."""
    if not ctx.deps.tool_retrieval_enabled:
        return _TOOL_RETRIEVAL_DISABLED
    tool_start = time.perf_counter()
    neighbour_count = 0
    found = False
    try:
        try:
            parsed_id = uuid.UUID(chunk_id)
        except ValueError:
            return f"Invalid chunk_id: {chunk_id}"

        passage = await ctx.deps.retriever.read_chunk(parsed_id)
        if passage is None:
            return f"Chunk not found: {chunk_id}"

        found = True
        ctx.deps.validator.register([passage])
        neighbour_count = len(passage.neighbours)
        if not passage.neighbours:
            return "No neighbouring chunks found."
        return json.dumps(
            [
                {
                    "chunk_id": str(n.chunk_id),
                    "chunk_index": n.chunk_index,
                    "page_or_section": n.page_or_section,
                    "content": n.content,
                }
                for n in passage.neighbours
            ],
            indent=2,
        )
    finally:
        elapsed_ms = int((time.perf_counter() - tool_start) * 1000)
        ctx.deps.record_tool_call("read_surrounding_chunks", elapsed_ms)
        logger.info(
            "assistant_tool_call_complete",
            tool="read_surrounding_chunks",
            user_id=str(ctx.deps.user_id),
            thread_id=str(ctx.deps.thread_id),
            elapsed_ms=elapsed_ms,
            found=found,
            neighbour_count=neighbour_count,
        )
