"""Run the procurement review against local source files without touching project data.

uv run python -m tender.eval.procurement_review --manifest <json> --output <directory>
The manifest lists profile, package and submissions ({firm, files}). Validated windows
are cached under the output directory. This exercises the same reader and renderer as
the queued workflow, including image fallbacks and citation checks.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.config import settings
from tender.llm.review_client import VERSION, ReviewClient
from tender.review_schemas import ReviewSelection
from tender.services.pdf import extract_native_pages, render_page_png
from tender.services.report import load_report_language_yaml
from tender.services.review_extraction import extract_review_window
from tender.services.review_facts import (
    numbered_facts,
    reconcile_submission,
    validate_selection,
    remove_enclosed_prices,
    missing_amounts,
)
from tender.services.review_render import render_review
from tender.services.review_layout import validate_review_layout
from tender.services.review_dates import normalize_source_dates
from tender.review_schemas import ReviewExtraction


async def run(manifest: dict, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    client = ReviewClient()
    semaphore = asyncio.Semaphore(3)
    quotes = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, str(index))),
            "name": submission["firm"],
        }
        for index, submission in enumerate(manifest["submissions"])
    ]
    started = time.monotonic()

    async def document(path: str, quote: dict) -> dict:
        source_path = Path(path)
        content = source_path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        pages = extract_native_pages(content)
        facts, uncaptured = [], []

        async def image_loader(key: str) -> bytes:
            return await asyncio.to_thread(
                render_page_png, content, page_no=int(key), dpi=150
            )

        for start in range(0, len(pages), 3):
            cache_digest = hashlib.sha256(
                f"{digest}:{VERSION}:{settings.tender_model_extract}:{start}".encode()
            ).hexdigest()
            cache = output / f"window-{cache_digest}.json"
            if cache.exists():
                window = json.loads(cache.read_text(encoding="utf-8"))
            else:
                wrapped = [
                    SimpleNamespace(
                        page_no=page.page_no,
                        text_content=page.text,
                        image_path=str(page.page_no),
                    )
                    for page in pages[start : start + 3]
                ]
                async with semaphore:
                    extraction, missing = await extract_review_window(
                        wrapped,
                        client=client,
                        context={
                            "package": manifest["package"],
                            "filename": source_path.name,
                            "opening_page_context": pages[0].text[:6000],
                        },
                        image_loader=image_loader,
                    )
                window = {**extraction.model_dump(mode="json"), "uncaptured": missing}
                cache.write_text(
                    json.dumps(window, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            normalized = ReviewExtraction.model_validate(window)
            normalize_source_dates(
                normalized,
                {page.page_no: page.text for page in pages[start : start + 3]},
                pages[0].text,
            )
            facts.extend(normalized.model_dump(mode="json")["facts"])
            uncaptured.extend(
                missing_amounts(
                    normalized,
                    {page.page_no: page.text for page in pages[start : start + 3]},
                )
            )
            print(
                f"{source_path.name}: {min(start + 3, len(pages))}/{len(pages)} pages",
                flush=True,
            )
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, digest)),
            "quote_id": quote["id"],
            "filename": source_path.name,
            "path": path,
            "page_count": len(pages),
            "facts": facts,
            "uncaptured": uncaptured,
        }

    documents = await asyncio.gather(
        *(
            document(path, quote)
            for quote, submission in zip(quotes, manifest["submissions"], strict=True)
            for path in submission["files"]
        )
    )
    facts = numbered_facts(documents)
    review_date = date.fromisoformat(
        manifest.get("review_date", date.today().isoformat())
    )
    calculations = {
        quote["id"]: reconcile_submission(
            [fact for fact in facts if fact["quote_id"] == quote["id"]],
            review_date=review_date,
        )
        for quote in quotes
    }
    payload = {
        "profile": manifest["profile"],
        "package": manifest["package"],
        "review_date": review_date.isoformat(),
        "quotes": quotes,
        "facts": facts,
        "calculations": calculations,
    }
    for attempt in range(2):
        selection = await client.request(
            stage="select", payload=payload, schema=ReviewSelection
        )
        (output / f"selection-attempt-{attempt}.json").write_text(
            selection.model_dump_json(indent=2), encoding="utf-8"
        )
        remove_enclosed_prices(selection, facts)
        try:
            validate_selection(
                selection, facts, [quote["id"] for quote in quotes], manifest["profile"]
            )
            break
        except ValueError as exc:
            if attempt:
                raise
            payload["validation_error"] = str(exc)
    language = load_report_language_yaml(
        Path(__file__).parents[3] / "data/tender/report_language.yaml"
    )
    markdown = render_review(
        package=manifest["package"],
        profile=manifest["profile"],
        review_date=review_date.isoformat(),
        quotes=quotes,
        documents=documents,
        facts=facts,
        selection=selection,
        calculations=calculations,
        language=language,
    )
    validate_review_layout(markdown, manifest["profile"])
    (output / "review.md").write_text(markdown, encoding="utf-8")
    result = {
        "duration_seconds": round(time.monotonic() - started, 2),
        "quotes": quotes,
        "documents": documents,
        "calculations": calculations,
        "selection": selection.model_dump(mode="json"),
    }
    (output / "evaluation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    try:
        result = asyncio.run(run(manifest, args.output))
    except Exception as exc:
        print(f"Review evaluation failed: {type(exc).__name__}", flush=True)
        if isinstance(exc, ValueError):
            print(str(exc)[:1200], flush=True)
        raise SystemExit(1) from None
    print(
        json.dumps(
            {
                "duration_seconds": result["duration_seconds"],
                "headlines": [
                    value["headline_cents"] for value in result["calculations"].values()
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
