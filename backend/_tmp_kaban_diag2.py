"""Reproduce Kavanagh citation-support failures against real corpus."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from sqlalchemy import text

from app.database.session import get_session_factory
from app.sitewise.pmp_claim_support import (
    _citation_source_map,
    _meaningful_tokens,
    citation_claim_support_violations,
)

PROJECT_ID = "7876bd93-87ce-4e95-89b2-67724fee458d"
CREATE_PMP_EVIDENCE_DOC_CHARS = 8_000
OUT = Path("_tmp_kavanagh_pmp")


def analyze_claim(claim: str, labels: list[str], texts: list[str]) -> None:
    claim_tokens = _meaningful_tokens(claim)
    claim_set = set(claim_tokens)
    concrete = any(t.isdigit() or t in {"one", "two", "three"} for t in claim_tokens)
    print("\nCLAIM:", claim)
    print("concrete:", concrete, "min:", 2 if concrete else 3)
    print("claim_tokens:", claim_tokens)
    for label, text_value in zip(labels, texts, strict=True):
        source_tokens = set(_meaningful_tokens(text_value))
        overlap = sorted(claim_set & source_tokens)
        print(f"  vs {label}: overlap={len(overlap)} -> {overlap[:25]}")


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
        labels = [d["filename"] or d["relative_path"] for d in docs]
        texts = [d["content"] for d in docs]

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
                    LIMIT 5
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()
        print("citation support messages:", len(msgs))
        for msg in msgs:
            print("\n=== MESSAGE", msg["created_at"], msg["id"], "===")
            print(msg["content"])
            data = msg["message_data"] or {}
            if isinstance(data, dict):
                (OUT / f"citation_msg_{msg['id']}.json").write_text(
                    __import__("json").dumps(data, default=str, indent=2)[:400000],
                    encoding="utf-8",
                )
                # Hunt for markdown in nested structures.
                blob = __import__("json").dumps(data, default=str)
                if "## Citation key" in blob or "Citation key" in blob:
                    print("message_data contains Citation key")

        # Number tokenization probe
        samples = ["$1,234,000", "$1,234,000.00", "QUA-KAV-T01–T18", "QUA-KAV-T01 to T18"]
        for sample in samples:
            print(sample, "->", _meaningful_tokens(sample))

        claims = [
            "Working regime: Stage 1 concept/schematic design to DA submission; Stage 2 design development; Stage 3 construction documentation and delivery. This is a PMP baseline Assumption [1]",
            "The current builder proposal is a fixed contract sum of $1,234,000 ex GST and includes separate provisional allowances of $30,000 ex GST for rock removal and $22,000 ex GST for pool [2]",
            "**User provided:** traditional lump-sum procurement. Ironbark’s proposal is a fixed-price tender based on Quoin tender set QUA-KAV-T01–T18, revision C, dated 2 March 2026 [3]",
        ]
        for claim in claims:
            analyze_claim(claim, labels, texts)

        # Simulate likely citation keys and run the real validator.
        ironbark = "05-building-proposal-ironbark-main-works.md"
        quoin = "01-fee-proposal-quoin-architecture.md"
        scenarios = {
            "all_to_ironbark": f"""
## Programme and staging regime

Working regime: Stage 1 concept/schematic design to DA submission; Stage 2 design development; Stage 3 construction documentation and delivery. This is a PMP baseline **Assumption**. [1]

## Cost, programme and procurement posture

The current builder proposal is a fixed contract sum of $1,234,000 ex GST and includes separate provisional allowances of $30,000 ex GST for rock removal and $22,000 ex GST for pool. [1]

**User provided:** traditional lump-sum procurement. Ironbark’s proposal is a fixed-price tender based on Quoin tender set QUA-KAV-T01–T18, revision C, dated 2 March 2026. [1]

## Citation key

- [1] {ironbark} — current
""",
            "correct_mapping": f"""
## Programme and staging regime

Working regime: Stage 1 concept/schematic design to DA submission; Stage 2 design development; Stage 3 construction documentation and delivery. This is a PMP baseline **Assumption**. [1]

## Cost, programme and procurement posture

The current builder proposal is a fixed contract sum of $1,234,000 ex GST and includes separate provisional allowances of $30,000 ex GST for rock removal and $22,000 ex GST for pool. [2]

**User provided:** traditional lump-sum procurement. Ironbark’s proposal is a fixed-price tender based on Quoin tender set QUA-KAV-T01–T18, revision C, dated 2 March 2026. [2]

## Citation key

- [1] {quoin} — current
- [2] {ironbark} — current
""",
            "assumption_cited_quoin_money_wrong_doc": f"""
## Programme and staging regime

Working regime: Stage 1 concept/schematic design to DA submission; Stage 2 design development; Stage 3 construction documentation and delivery. This is a PMP baseline **Assumption**. [1]

## Cost, programme and procurement posture

The current builder proposal is a fixed contract sum of $1,234,000 ex GST and includes separate provisional allowances of $30,000 ex GST for rock removal and $22,000 ex GST for pool. [1]

**User provided:** traditional lump-sum procurement. Ironbark’s proposal is a fixed-price tender based on Quoin tender set QUA-KAV-T01–T18, revision C, dated 2 March 2026. [1]

## Citation key

- [1] {quoin} — current
""",
        }
        for name, markdown in scenarios.items():
            violations = citation_claim_support_violations(
                markdown, source_texts=texts, source_labels=labels
            )
            print(f"\nSCENARIO {name}: {len(violations)} violations")
            for v in violations:
                print(" -", v)
            key_map = _citation_source_map(markdown, texts, labels)
            print(" mapped refs:", {k: (labels[[t for t in texts].index(v.split('\n')[0])] if False else len(v)) for k, v in key_map.items()})
            for ref, source in key_map.items():
                matched = [lab for lab, txt in zip(labels, texts, strict=True) if txt in source or source in txt]
                # simpler: which labels contributed
                matched = []
                for lab, txt in zip(labels, texts, strict=True):
                    if txt and txt in source:
                        matched.append(lab)
                print(f"  [{ref}] -> {matched} ({len(source)} chars)")


if __name__ == "__main__":
    asyncio.run(main())
