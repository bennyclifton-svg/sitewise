import uuid
import time
from collections.abc import Awaitable, Callable

import structlog
from pydantic_ai.usage import UsageLimits
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.agent import (
    agent,
    format_turn_instructions,
    platform_qa_agent,
    repair_missing_platform_citations,
)
from app.assistant.run_agent import run_agent_with_retry
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.chat.intent import (
    is_corpus_catalog_question,
    is_drawing_register_question,
    is_pure_catalog_question,
    platform_inventory_scope,
)
from app.grounding.validator import GroundingValidator
from app.retrieval.catalog import (
    build_catalog_answer,
    catalog_to_passages,
    list_corpus_projects,
)
from app.retrieval.inventory import (
    build_platform_knowledge_inventory_answer,
    build_seed_inventory_answer,
    list_platform_documents,
    list_seed_documents,
    platform_rows_to_passages,
)
from app.retrieval.register import (
    build_drawing_register_answer,
    drawing_rows_to_passages,
    list_drawings,
)
from app.retrieval.router import should_use_whole_document_path
from app.retrieval.whole_document import load_platform_whole_documents
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.assistant.chat_models import resolve_chat_model
from app.config import settings

logger = structlog.get_logger(__name__)

StatusCallback = Callable[[str], Awaitable[None]]

_WHOLE_DOCUMENT_AGENT_LIMITS = UsageLimits(request_limit=5)


async def _notify(on_status: StatusCallback | None, message: str) -> None:
    if on_status is not None:
        await on_status(message)


async def run_chat_turn(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    user_text: str,
    filters: RetrievalFilters | None = None,
    on_status: StatusCallback | None = None,
    chat_model: str | None = None,
) -> GroundedAnswer:
    resolved_model = resolve_chat_model(chat_model)
    logger.info(
        "chat_turn_start",
        user_id=str(user_id),
        thread_id=str(thread_id),
        query=user_text,
    )
    total_start = time.perf_counter()
    retriever = DocumentRetriever(session)
    validator = GroundingValidator()

    inventory_scope = platform_inventory_scope(user_text)
    if inventory_scope == "seed":
        await _notify(on_status, "Loading seed file list")
        inventory_start = time.perf_counter()
        seed_rows = await list_seed_documents(session)
        validator.register(platform_rows_to_passages(seed_rows))
        answer = build_seed_inventory_answer(seed_rows)
        logger.info(
            "chat_turn_fast_path",
            path="seed_inventory",
            document_count=len(seed_rows),
            elapsed_ms=int((time.perf_counter() - inventory_start) * 1000),
            total_elapsed_ms=int((time.perf_counter() - total_start) * 1000),
        )
        return validator.validate(answer)

    if inventory_scope == "all":
        await _notify(on_status, "Loading platform knowledge")
        inventory_start = time.perf_counter()
        platform_rows = await list_platform_documents(session)
        validator.register(platform_rows_to_passages(platform_rows))
        answer = build_platform_knowledge_inventory_answer(platform_rows)
        logger.info(
            "chat_turn_fast_path",
            path="platform_inventory",
            document_count=len(platform_rows),
            elapsed_ms=int((time.perf_counter() - inventory_start) * 1000),
            total_elapsed_ms=int((time.perf_counter() - total_start) * 1000),
        )
        return validator.validate(answer)

    if is_drawing_register_question(user_text):
        await _notify(on_status, "Loading drawing register")
        register_start = time.perf_counter()
        drawing_rows = await list_drawings(session, filters=filters)
        validator.register(drawing_rows_to_passages(drawing_rows))
        answer = build_drawing_register_answer(drawing_rows)
        logger.info(
            "chat_turn_fast_path",
            path="drawing_register",
            document_count=len(drawing_rows),
            elapsed_ms=int((time.perf_counter() - register_start) * 1000),
            total_elapsed_ms=int((time.perf_counter() - total_start) * 1000),
        )
        return validator.validate(answer)

    catalog: list = []
    catalog_passages = []
    catalog_question = is_corpus_catalog_question(user_text)
    if catalog_question:
        catalog_start = time.perf_counter()
        catalog = await list_corpus_projects(session)
        catalog_passages = catalog_to_passages(catalog)
        validator.register(catalog_passages)
        logger.info(
            "chat_turn_catalog_loaded",
            project_count=len(catalog),
            elapsed_ms=int((time.perf_counter() - catalog_start) * 1000),
        )

    async def load_catalog() -> list:
        catalog_start = time.perf_counter()
        loaded = await list_corpus_projects(session)
        logger.info(
            "chat_turn_catalog_loaded",
            project_count=len(loaded),
            elapsed_ms=int((time.perf_counter() - catalog_start) * 1000),
            lazy=True,
        )
        return loaded

    if is_pure_catalog_question(user_text):
        await _notify(on_status, "Loading project list")
        logger.info("chat_turn_fast_path", path="catalog")
        return validator.validate(build_catalog_answer(catalog))

    if should_use_whole_document_path(user_text, filters):
        await _notify(on_status, "Loading SiteWise knowledge")
        initial_passages = await load_platform_whole_documents(session, user_text)
        validator.register(initial_passages)
        logger.info(
            "chat_turn_retrieval_complete",
            path="whole_document",
            initial_passage_count=len(initial_passages),
            registered_passage_count=len(validator.passages),
        )
        deps = DocumentAgentDeps(
            user_id=user_id,
            thread_id=thread_id,
            retriever=retriever,
            validator=validator,
            project_catalog=catalog,
            catalog_loader=load_catalog,
            initial_passages=initial_passages,
            filters=filters,
            tool_retrieval_enabled=False,
        )
        await _notify(on_status, "Drafting answer")
        agent_start = time.perf_counter()
        result = await run_agent_with_retry(
            platform_qa_agent,
            user_text,
            deps=deps,
            instructions=format_turn_instructions(None, initial_passages, tools_disabled=True),
            usage_limits=_WHOLE_DOCUMENT_AGENT_LIMITS,
            model=resolved_model,
        )
        logger.info(
            "chat_turn_agent_complete",
            path="whole_document",
            citation_count=len(result.output.citations),
            evidence_sufficient=result.output.evidence_sufficient,
            elapsed_ms=int((time.perf_counter() - agent_start) * 1000),
            tool_calls=deps.tool_call_summary(),
        )
        validation_start = time.perf_counter()
        validated = validator.validate(
            repair_missing_platform_citations(result.output, initial_passages)
        )
        logger.info(
            "chat_turn_validated",
            path="whole_document",
            cited_passage_count=len(validated.cited_passages),
            elapsed_ms=int((time.perf_counter() - validation_start) * 1000),
            total_elapsed_ms=int((time.perf_counter() - total_start) * 1000),
        )
        return validated

    if catalog_question:
        initial_passages = catalog_passages
    else:
        await _notify(on_status, "Searching project evidence")
        retrieval_start = time.perf_counter()
        initial_passages = await retriever.retrieve(
            user_text,
            filters=filters,
            limit=settings.assistant_context_passage_limit,
            include_neighbours=False,
        )
        validator.register(initial_passages)
        logger.info(
            "chat_turn_initial_retrieval_complete",
            elapsed_ms=int((time.perf_counter() - retrieval_start) * 1000),
        )

    logger.info(
        "chat_turn_retrieval_complete",
        initial_passage_count=len(initial_passages),
        registered_passage_count=len(validator.passages),
    )

    deps = DocumentAgentDeps(
        user_id=user_id,
        thread_id=thread_id,
        retriever=retriever,
        validator=validator,
        project_catalog=catalog,
        catalog_loader=load_catalog,
        initial_passages=initial_passages,
        filters=filters,
    )

    await _notify(on_status, "Drafting answer")
    agent_start = time.perf_counter()
    result = await run_agent_with_retry(
        agent,
        user_text,
        deps=deps,
        instructions=format_turn_instructions(
            catalog if catalog_question else None, initial_passages
        ),
        model=resolved_model,
    )
    logger.info(
        "chat_turn_agent_complete",
        citation_count=len(result.output.citations),
        evidence_sufficient=result.output.evidence_sufficient,
        elapsed_ms=int((time.perf_counter() - agent_start) * 1000),
        tool_calls=deps.tool_call_summary(),
    )
    validation_start = time.perf_counter()
    validated = validator.validate(result.output)
    logger.info(
        "chat_turn_validated",
        cited_passage_count=len(validated.cited_passages),
        elapsed_ms=int((time.perf_counter() - validation_start) * 1000),
        total_elapsed_ms=int((time.perf_counter() - total_start) * 1000),
    )
    return validated
