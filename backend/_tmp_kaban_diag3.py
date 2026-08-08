"""Extract failed Kavanagh draft markdown and simulate mobilisation doc selection."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from app.database.session import get_session_factory
from app.sitewise.pmp_claim_support import (
    _citation_source_map,
    citation_claim_support_violations,
)

PROJECT_ID = "7876bd93-87ce-4e95-89b2-67724fee458d"
CREATE_PMP_EVIDENCE_DOC_CHARS = 8_000
CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS = 8
MOBILISATION_EVIDENCE_PATH_MARKERS = (
    "engagement-letter",
    "engagement_letter",
    "fee-proposal",
    "fee_proposal",
    "00-brief",
    "owner-brief",
    "project-brief",
)
OUT = Path("_tmp_kavanagh_pmp")


def walk_find_markdown(obj, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.extend(walk_find_markdown(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for index, value in enumerate(obj[:80]):
            found.extend(walk_find_markdown(value, f"{path}[{index}]"))
    elif isinstance(obj, str) and (
        "Citation key" in obj or "Working regime" in obj or "1,234,000" in obj
    ):
        found.append((path, obj))
    return found


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    async with get_session_factory()() as session:
        docs = (
            await session.execute(
                text(
                    """
                    SELECT filename, relative_path,
                           left(coalesce(normalized_content, ''), :n) AS content
                    FROM source_documents
                    WHERE project_id = :pid
                    ORDER BY filename
                    """
                ),
                {"pid": PROJECT_ID, "n": CREATE_PMP_EVIDENCE_DOC_CHARS},
            )
        ).mappings().all()

        marker_paths = []
        for doc in docs:
            path_lower = (doc["relative_path"] or "").lower()
            if any(marker in path_lower for marker in MOBILISATION_EVIDENCE_PATH_MARKERS):
                marker_paths.append(doc["relative_path"])
        print("marker_paths:", marker_paths)

        # Approximate mobilisation set: marker docs first, then others, capped at 8.
        # Real code merges semantic hits + markers. Without semantic scores, show markers-only
        # and first-8-by-filename for comparison.
        by_path = {doc["relative_path"]: doc for doc in docs}
        marker_docs = [by_path[p] for p in marker_paths if p in by_path][
            :CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS
        ]
        print("mobilisation_marker_only:")
        for doc in marker_docs:
            print(" -", doc["filename"], doc["relative_path"])

        # Important: Ironbark is under 06-programme and named building-proposal, NOT fee-proposal.
        ironbark = [
            d for d in docs if "ironbark" in (d["filename"] or "").lower()
        ]
        print("ironbark in corpus:", [d["filename"] for d in ironbark])
        print(
            "ironbark would be loaded via markers only?",
            any("ironbark" in (d["filename"] or "").lower() for d in marker_docs),
        )

        msgs = (
            await session.execute(
                text(
                    """
                    SELECT m.id, m.content, m.message_data, m.created_at
                    FROM chat_messages m
                    JOIN chat_threads t ON t.id = m.thread_id
                    WHERE t.project_id = :pid
                      AND m.content ILIKE '%citation support%'
                    ORDER BY m.created_at DESC
                    LIMIT 2
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()

        for msg in msgs:
            path = OUT / f"fullmsg_{msg['id']}.json"
            path.write_text(
                json.dumps(
                    {
                        "content": msg["content"],
                        "message_data": msg["message_data"],
                        "created_at": msg["created_at"],
                    },
                    default=str,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("wrote", path)
            for found_path, markdown in walk_find_markdown(msg["message_data"]):
                md_path = OUT / f"draft_from_msg_{msg['id']}.md"
                md_path.write_text(markdown, encoding="utf-8")
                print("FOUND markdown at", found_path, "len", len(markdown), "->", md_path)

        runs = (
            await session.execute(
                text(
                    """
                    SELECT id, state, error_message, progress, result, created_at
                    FROM workflow_runs
                    WHERE project_id = :pid
                      AND created_at > now() - interval '3 days'
                    ORDER BY created_at DESC
                    LIMIT 15
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("recent runs:", len(runs))
        for run in runs:
            err = run["error_message"] or ""
            print(run["created_at"], run["state"], err[:220])
            blob = json.dumps(
                {"progress": run["progress"], "result": run["result"]},
                default=str,
            )
            hits = walk_find_markdown(run["progress"]) + walk_find_markdown(run["result"])
            for found_path, markdown in hits:
                md_path = OUT / f"draft_from_run_{run['id']}.md"
                md_path.write_text(markdown, encoding="utf-8")
                print("FOUND run markdown at", found_path, "->", md_path)

                # Validate against marker-only corpus (likely Create PMP set if semantic missed Ironbark)
                labels = [d["filename"] for d in marker_docs]
                texts = [d["content"] for d in marker_docs]
                violations = citation_claim_support_violations(
                    markdown, source_texts=texts, source_labels=labels
                )
                print("marker-only violations:", len(violations))
                for item in violations:
                    print(" -", item)
                print("citation map:", list(_citation_source_map(markdown, texts, labels)))

                # Also against full corpus
                labels_all = [d["filename"] for d in docs]
                texts_all = [d["content"] for d in docs]
                violations_all = citation_claim_support_violations(
                    markdown, source_texts=texts_all, source_labels=labels_all
                )
                print("full-corpus violations:", len(violations_all))
                for item in violations_all:
                    print(" -", item)


if __name__ == "__main__":
    asyncio.run(main())
