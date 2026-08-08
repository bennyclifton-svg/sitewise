"""Temporary diagnosis helper for Kavanagh PMP citation failures."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from sqlalchemy import text

from app.database.session import get_session_factory
from app.sitewise.pmp_claim_support import citation_claim_support_violations

PROJECT_ID = "7876bd93-87ce-4e95-89b2-67724fee458d"
CREATE_PMP_EVIDENCE_DOC_CHARS = 8_000
OUT = Path("_tmp_kavanagh_pmp")


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    async with get_session_factory()() as session:
        project = (
            await session.execute(
                text(
                    """
                    SELECT id, title, slug, archetype, building_class, work_type,
                           project_metadata
                    FROM projects
                    WHERE id = :pid
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().one()
        print("project:", {k: project[k] for k in project if k != "project_metadata"})

        docs = (
            await session.execute(
                text(
                    """
                    SELECT id, filename, relative_path,
                           coalesce(normalized_content, '') AS content
                    FROM source_documents
                    WHERE project_id = :pid
                    ORDER BY filename
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("docs:", len(docs))
        for doc in docs:
            content = doc["content"]
            print(
                {
                    "filename": doc["filename"],
                    "relative_path": doc["relative_path"],
                    "content_len": len(content),
                }
            )
            safe = re.sub(r"[^a-zA-Z0-9]+", "_", doc["filename"] or "doc")[:50]
            (OUT / f"full_{safe}.txt").write_text(content, encoding="utf-8")
            (OUT / f"trunc8k_{safe}.txt").write_text(
                content[:CREATE_PMP_EVIDENCE_DOC_CHARS], encoding="utf-8"
            )

        needles = [
            "1,234,000",
            "1234000",
            "1 234 000",
            "$1,234",
            "30,000",
            "22,000",
            "rock",
            "pool",
            "Ironbark",
            "lump",
            "fixed",
            "provisional",
            "Stage 1",
            "schematic",
            "working regime",
            "QUA-KAV",
            "Quoin",
            "GST",
        ]
        for needle in needles:
            hits = []
            for doc in docs:
                content = doc["content"]
                idx = content.casefold().find(needle.casefold())
                if idx < 0:
                    continue
                hits.append(
                    {
                        "filename": doc["filename"],
                        "pos": idx,
                        "in_first_8k": idx < CREATE_PMP_EVIDENCE_DOC_CHARS,
                        "snippet": content[max(0, idx - 40) : idx + 90].replace("\n", " "),
                    }
                )
            print(f"needle {needle!r}: {hits}")

        runs = (
            await session.execute(
                text(
                    """
                    SELECT id, workflow_type, state,
                           left(coalesce(error_message, ''), 2000) AS err,
                           progress, result, created_at
                    FROM workflow_runs
                    WHERE project_id = :pid
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("workflow_runs:", len(runs))
        for run in runs:
            print(
                {
                    "id": run["id"],
                    "workflow_type": run["workflow_type"],
                    "state": run["state"],
                    "created_at": run["created_at"],
                    "err": run["err"],
                }
            )
            progress = run["progress"] or {}
            if isinstance(progress, dict):
                (OUT / f"run_{run['id']}_progress.json").write_text(
                    json.dumps(progress, default=str, indent=2)[:200000],
                    encoding="utf-8",
                )
                result = run["result"]
                if result is not None:
                    (OUT / f"run_{run['id']}_result.json").write_text(
                        json.dumps(result, default=str, indent=2)[:200000],
                        encoding="utf-8",
                    )

        msgs = (
            await session.execute(
                text(
                    """
                    SELECT m.id, m.role, m.content, m.message_data, m.created_at
                    FROM chat_messages m
                    JOIN chat_threads t ON t.id = m.thread_id
                    WHERE t.project_id = :pid
                    ORDER BY m.created_at DESC
                    LIMIT 20
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("messages:", len(msgs))
        for msg in msgs:
            content = msg["content"] or ""
            print(
                {
                    "created_at": msg["created_at"],
                    "role": msg["role"],
                    "content": content[:1000],
                }
            )
            data = msg["message_data"]
            if isinstance(data, dict):
                (OUT / f"msg_{msg['id']}_data.json").write_text(
                    json.dumps(data, default=str, indent=2)[:200000],
                    encoding="utf-8",
                )
                if "citation support" in content.casefold():
                    (OUT / f"msg_{msg['id']}_content.txt").write_text(
                        content, encoding="utf-8"
                    )

        # Reconstruct validation inputs from truncated docs (Create PMP behaviour).
        labels = [doc["filename"] or doc["relative_path"] for doc in docs]
        texts = [doc["content"][:CREATE_PMP_EVIDENCE_DOC_CHARS] for doc in docs]

        # Search activity events for failed markdown previews.
        events = (
            await session.execute(
                text(
                    """
                    SELECT id, event_type, payload, created_at
                    FROM activity_events
                    WHERE project_id = :pid
                    ORDER BY created_at DESC
                    LIMIT 30
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("activity_events:", len(events))
        for event in events:
            payload = event["payload"] or {}
            print(
                {
                    "created_at": event["created_at"],
                    "event_type": event["event_type"],
                    "payload_keys": sorted(payload.keys())
                    if isinstance(payload, dict)
                    else type(payload).__name__,
                }
            )
            if isinstance(payload, dict):
                blob = json.dumps(payload, default=str)
                if "citation support" in blob.casefold() or "Cited claim" in blob:
                    (OUT / f"event_{event['id']}.json").write_text(
                        json.dumps(payload, default=str, indent=2)[:300000],
                        encoding="utf-8",
                    )

        # Try to find any persisted draft markdown for this project.
        drafts = (
            await session.execute(
                text(
                    """
                    SELECT id, title, artifact_type, version, status,
                           left(coalesce(content_md, content, ''), 200) AS head,
                           length(coalesce(content_md, content, '')) AS content_len,
                           created_at
                    FROM draft_artifacts
                    WHERE project_id = :pid
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("draft_artifacts query skipped if columns wrong; trying flexible path")
        print("drafts_raw_attempt_len", len(drafts) if drafts is not None else None)

        # Build synthetic claims from the user error and see overlap against each source.
        claims = [
            "Working regime: Stage 1 concept/schematic design to DA submission; Stage 2 design development; Stage 3 construction documentation and delivery. This is a PMP baseline Assumption",
            "The current builder proposal is a fixed contract sum of $1,234,000 ex GST and includes separate provisional allowances of $30,000 ex GST for rock removal and $22,000 ex GST for pool",
            "User provided: traditional lump-sum procurement. Ironbark’s proposal is a fixed-price tender based on Quoin tender set QUA-KAV-T01–T18, revision C, dated 2 March 2026",
        ]
        from app.sitewise.pmp_claim_support import _meaningful_tokens

        for claim in claims:
            claim_tokens = set(_meaningful_tokens(claim))
            print("CLAIM:", claim[:120])
            print(" claim_tokens_sample:", sorted(claim_tokens)[:40])
            for label, text_value in zip(labels, texts, strict=True):
                source_tokens = set(_meaningful_tokens(text_value))
                overlap = claim_tokens & source_tokens
                concrete = any(t.isdigit() or t in {"one","two","three"} for t in claim_tokens)
                print(
                    {
                        "label": label,
                        "overlap_count": len(overlap),
                        "minimum": 2 if concrete else 3,
                        "overlap_sample": sorted(overlap)[:30],
                    }
                )


if __name__ == "__main__":
    asyncio.run(main())
