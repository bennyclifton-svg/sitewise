"""Check the compact report against the shared export's A4 content area."""

from __future__ import annotations

import re
from io import BytesIO

import fitz

from app.sitewise.artifact_exports import _document_html, _markdown_html


def validate_review_layout(markdown: str, profile: str) -> None:
    maximum = {"consultant": 1, "trade": 2, "head_contractor": 3}[profile]
    html = _document_html(
        _markdown_html(markdown),
        project_title="",
        artifact_title="",
        version=1,
        compact=True,
    )
    # Story uses an explicit content rectangle instead of CSS page-margin boxes.
    html = re.sub(r"^@page.*$", "", html, flags=re.MULTILINE)
    story = fitz.Story(html=html)
    paper = fitz.paper_rect("a4")
    page = paper + (45.36, 45.36, -45.36, -51.03)
    writer = fitz.DocumentWriter(BytesIO())
    try:
        for _ in range(maximum):
            device = writer.begin_page(paper)
            more, _ = story.place(page)
            story.draw(device)
            writer.end_page()
            if not more:
                return
    finally:
        writer.close()
    raise ValueError(
        f"The {profile} report exceeds its {maximum}-page limit; use fewer matrix groups and shorter source selections"
    )
