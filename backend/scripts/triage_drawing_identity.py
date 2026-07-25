"""Report the identity Clerk would register for a folder of drawings.

Run this over a batch before or after uploading to see which sheets parse
cleanly and which need work, without waiting on ingest.

    python scripts/triage_drawing_identity.py "D:/drawings/petersham"
    python scripts/triage_drawing_identity.py "D:/drawings" --only-suspect
    python scripts/triage_drawing_identity.py "D:/drawings" --csv out.csv

Columns: the parsed fields, the confidence, and which source supplied them —
``title-block`` means the geometry reader carried it, ``filename`` means the
sheet itself gave nothing. A blank title or revision on a drawing is the signal
worth chasing; dump that sheet to a fixture and add a case:

    python scripts/dump_title_block_fixture.py SHEET.pdf \
        tests/fixtures/title_blocks/<name>.json
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ingest.document_metadata import parse_document_metadata
from ingest.title_block import pdf_title_block_preview


@dataclass(frozen=True, slots=True)
class Row:
    file_name: str
    document_number: str
    title: str
    revision: str
    confidence: str
    source: str

    @property
    def is_suspect(self) -> bool:
        if not self.title or not self.document_number:
            return True
        if self.confidence == "low" or self.confidence == "error":
            return True
        # "Current" is the placeholder the parser uses when no revision was found.
        if not self.revision or self.revision == "Current":
            return True
        # A title that only restates the filename means nothing was read off the
        # sheet — the row looks populated but carries no new information.
        return _same_words(self.title, Path(self.file_name).stem)


def _same_words(left: str, right: str) -> bool:
    return _word_key(left) == _word_key(right)


def _word_key(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def triage(path: Path) -> Row:
    try:
        preview = pdf_title_block_preview(path.read_bytes())
    except Exception as exc:  # a corrupt sheet should not stop the batch
        return Row(path.name, "", f"<unreadable: {exc}>", "", "error", "none")

    parsed = parse_document_metadata(
        file_name=path.name,
        filed_path=f"04-projects/triage/03-design/{path.name}",
        source_path=f"04-projects/triage/_inbox/{path.name}",
        preview_snippet=preview,
    )
    return Row(
        file_name=path.name,
        document_number=parsed.document_number,
        title=parsed.title,
        revision=parsed.revision,
        confidence=parsed.confidence,
        source="title-block" if preview else "filename",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder of PDFs, searched recursively")
    parser.add_argument("--only-suspect", action="store_true", help="hide sheets that parsed cleanly")
    parser.add_argument("--csv", type=Path, help="also write every row to this CSV")
    args = parser.parse_args(argv[1:])

    if not args.folder.is_dir():
        print(f"not a folder: {args.folder}")
        return 2

    pdfs = sorted(args.folder.rglob("*.pdf")) + sorted(args.folder.rglob("*.PDF"))
    pdfs = sorted(set(pdfs))
    if not pdfs:
        print(f"no PDFs under {args.folder}")
        return 1

    rows = [triage(pdf) for pdf in pdfs]
    shown = [row for row in rows if row.is_suspect] if args.only_suspect else rows

    width = min(max((len(row.file_name) for row in shown), default=10), 52)
    print(f"{'FILE':<{width}}  {'NUMBER':<14} {'REV':<6} {'CONF':<7} {'SOURCE':<12} TITLE")
    for row in shown:
        flag = "!" if row.is_suspect else " "
        print(
            f"{row.file_name[:width]:<{width}}{flag} {row.document_number[:14]:<14}"
            f" {row.revision[:6]:<6} {row.confidence:<7} {row.source:<12} {row.title}"
        )

    suspect = sum(1 for row in rows if row.is_suspect)
    from_sheet = sum(1 for row in rows if row.source == "title-block")
    print(
        f"\n{len(rows)} sheets | {from_sheet} read from the title block"
        f" | {suspect} need review"
    )

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["file_name", "document_number", "title", "revision", "confidence", "source"])
            for row in rows:
                writer.writerow(
                    [row.file_name, row.document_number, row.title, row.revision, row.confidence, row.source]
                )
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
