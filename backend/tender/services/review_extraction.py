"""Read all pages, checkpoint validated windows and recover incomplete extraction."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.storage.project_files import download_project_file
from tender.llm.review_client import ReviewClient, reader_signature
from tender.models import TenderComparison, TenderDocument, TenderJob, TenderPage
from tender.review_schemas import ReviewExtraction
from tender.services import extract_cache, jobs, telemetry
from tender.services.review_facts import missing_amounts, validate_extraction
from tender.services.review_dates import normalize_source_dates


async def extract_review_window(
    pages: list[TenderPage],
    *,
    client: ReviewClient,
    context: dict[str, Any],
    image_loader=None,
) -> tuple[ReviewExtraction, list[dict[str, Any]]]:
    image_loader = image_loader or load_page_image
    source = {page.page_no: page.text_content for page in pages}
    payload = {
        "context": context,
        "expected_page_numbers": list(source),
        "pages": [{"page_no": number, "text": text} for number, text in source.items()],
    }
    images = {
        page.page_no: await image_loader(page.image_path)
        for page in pages
        if len(page.text_content.strip()) < 40
    }
    last_error = None
    for attempt in range(2):
        try:
            result = await client.request(
                stage="extract", payload=payload, schema=ReviewExtraction, images=images
            )
            # Ground model-supplied dates before checking calendar validity.
            normalize_source_dates(
                result, source, context.get("opening_page_context", "")
            )
            validate_extraction(result, source, set(images))
            missing = missing_amounts(result, source)
            if not missing or attempt:
                return result, missing
            payload["uncaptured_figures"] = missing
        except ValueError as exc:
            last_error = exc
            if attempt:
                raise
            payload["validation_error"] = str(exc)
        # A labelled image retry also catches malformed figures and layout errors.
        images = {page.page_no: await image_loader(page.image_path) for page in pages}
    raise ValueError("Could not validate the submission pages") from last_error


async def load_page_image(storage_key: str) -> bytes:
    # The key comes from an authorised TenderPage, never directly from the client.
    return await asyncio.to_thread(download_project_file, storage_key=storage_key)


async def read_review_document(
    session: AsyncSession, job: TenderJob, *, client: ReviewClient | None = None
) -> None:
    document = await session.get(TenderDocument, uuid.UUID(job.payload["document_id"]))
    comparison = await session.get(TenderComparison, job.comparison_id)
    if document is None or comparison is None:
        raise ValueError("Submission document not found")
    result = await session.execute(
        select(TenderPage)
        .where(TenderPage.document_id == document.id)
        .order_by(TenderPage.page_no)
    )
    pages = list(result.scalars())
    if not document.page_count or [page.page_no for page in pages] != list(
        range(1, document.page_count + 1)
    ):
        raise ValueError(
            "Some original PDF pages are missing; retry document ingestion"
        )
    client = client or ReviewClient()
    signature = reader_signature(ReviewExtraction)
    # Windows are independent, small queue units in the document checkpoint. No
    # retry restarts successfully validated pages or loses non-price attachments.
    data = dict(document.review_data or {})
    if data.get("extractor_version") != signature:
        data = {
            "read_version": data.get("read_version"),
            "extractor_version": signature,
            "windows": {},
        }
    windows = dict(data.get("windows", {}))
    context = {
        "package": comparison.context.get("package_name"),
        "filename": document.original_filename,
        "opening_page_context": pages[0].text_content[:6000],
    }
    for start in range(0, len(pages), 3):
        page_window = pages[start : start + 3]
        key = str(start)
        if key in windows:
            continue
        cache_key = hashlib.sha256(
            f"{document.content_hash}:{start}".encode()
        ).hexdigest()
        cached = await extract_cache.get_cached_extract(
            session,
            project_id=comparison.project_id,
            content_hash=cache_key,
            extractor_version=signature,
        )
        if cached:
            window = cached.payload
            usage = telemetry.current_stage_usage()
            if usage:
                usage.cache_hits += 1
        else:
            # End the read transaction before waiting on the provider.
            await session.commit()
            extracted, missing = await extract_review_window(
                page_window, client=client, context=context
            )
            window = {**extracted.model_dump(mode="json"), "uncaptured": missing}
            await jobs.assert_lease(session, job)
            await extract_cache.put_cached_extract(
                session,
                project_id=comparison.project_id,
                content_hash=cache_key,
                extractor_version=signature,
                model=settings.tender_model_extract,
                payload=window,
            )
        normalized = ReviewExtraction.model_validate(window)
        normalize_source_dates(
            normalized,
            {page.page_no: page.text_content for page in page_window},
            context["opening_page_context"],
        )
        window = {
            **window,
            **normalized.model_dump(mode="json"),
            "uncaptured": missing_amounts(
                normalized, {page.page_no: page.text_content for page in page_window}
            ),
        }
        await jobs.assert_lease(session, job)
        windows[key] = window
        document.review_data = {**data, "windows": windows}
        await session.commit()
    await jobs.assert_lease(session, job)
    document.review_data = {
        **data,
        "windows": windows,
        "complete": True,
        "facts": [
            fact for key in sorted(windows, key=int) for fact in windows[key]["facts"]
        ],
        "uncaptured": [
            fact
            for key in sorted(windows, key=int)
            for fact in windows[key].get("uncaptured", [])
        ],
    }
    await session.commit()
