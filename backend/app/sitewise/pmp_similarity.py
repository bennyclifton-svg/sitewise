"""Identical-line similarity for PMP corpus gates.

Wave 2 measured 14.1 extend versus 43.1 new at 94.7% identical lines. The
Stage 1 acceptance gate is that any pair differing in class, work type, and
scale band must land below PAIRWISE_SIMILARITY_LIMIT.
"""

from __future__ import annotations

from collections import Counter
import re

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

PAIRWISE_SIMILARITY_LIMIT = 0.70


def pmp_content_lines(markdown: str) -> list[str]:
    """Non-empty lines after stripping clerk HTML comments."""
    stripped = _HTML_COMMENT_RE.sub("", markdown)
    return [line.strip() for line in stripped.splitlines() if line.strip()]


def identical_line_similarity(left: str, right: str) -> float:
    """Dice coefficient on stripped content lines.

    This is the Wave 2 identical-line metric: shared line occurrences over the
    combined line counts. Blank lines and ``<!-- clerk:block ... -->`` markers
    are ignored so comment ids do not inflate the diff.
    """
    left_lines = pmp_content_lines(left)
    right_lines = pmp_content_lines(right)
    if not left_lines and not right_lines:
        return 1.0
    if not left_lines or not right_lines:
        return 0.0
    shared = sum((Counter(left_lines) & Counter(right_lines)).values())
    return (2 * shared) / (len(left_lines) + len(right_lines))


def below_pairwise_similarity_gate(left: str, right: str) -> bool:
    return identical_line_similarity(left, right) < PAIRWISE_SIMILARITY_LIMIT
