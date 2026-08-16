from __future__ import annotations

from datetime import date, timedelta
from xml.sax.saxutils import escape as xml_escape

from app.programme.schemas import ProgrammeState

FIGURE_WIDTH = 720
HEADER_HEIGHT = 40
ROW_HEIGHT = 28
NAME_WIDTH = 160
PAD = 8
VOID = "#14120f"
BEAM = "#d8c3a5"
EDGE = "#3a342c"
STAGE = "#8f7b5f"
ACTIVITY = "#c4a574"
MILESTONE = "#e8d7b8"
TODAY = "#c45c26"


def render_programme_svg(state: ProgrammeState) -> str:
    rows = list(state.activities)
    height = HEADER_HEIGHT + ROW_HEIGHT * max(len(rows), 1)
    starts = [item.start_date for item in rows] or [date.today()]
    finishes = [item.finish_date or item.start_date for item in rows] or [date.today()]
    span_start = min(starts)
    span_end = max(finishes)
    if span_end <= span_start:
        span_end = span_start + timedelta(days=1)
    span_days = (span_end - span_start).days
    chart_left = NAME_WIDTH
    chart_width = FIGURE_WIDTH - NAME_WIDTH - PAD
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{FIGURE_WIDTH}" '
        f'height="{height}" viewBox="0 0 {FIGURE_WIDTH} {height}" '
        f'role="img" aria-label="Project programme">'
        f'<rect width="100%" height="100%" fill="{VOID}"/>'
        f'<text x="{PAD}" y="24" fill="{BEAM}" font-size="12" '
        f'font-family="ui-sans-serif, system-ui">Programme</text>'
    ]
    for index, item in enumerate(rows):
        top = HEADER_HEIGHT + index * ROW_HEIGHT
        indent = 0 if item.kind == "stage" else 12
        parts.append(
            f'<text x="{PAD + indent}" y="{top + 18}" fill="{BEAM}" font-size="11" '
            f'font-family="ui-sans-serif, system-ui">'
            f"{xml_escape(item.name)}</text>"
        )
        start = item.start_date
        finish = item.finish_date or item.start_date
        x = chart_left + ((start - span_start).days / span_days) * chart_width
        width = max(((finish - start).days / span_days) * chart_width, 4)
        y = top + 8
        if item.kind == "milestone":
            cx = x
            cy = top + ROW_HEIGHT / 2
            parts.append(
                f'<polygon points="{cx},{cy - 5} {cx + 5},{cy} {cx},{cy + 5} {cx - 5},{cy}" '
                f'fill="{MILESTONE}"/>'
            )
        else:
            fill = STAGE if item.kind == "stage" else ACTIVITY
            parts.append(
                f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="12" '
                f'rx="2" fill="{fill}"/>'
            )
    today = date.today()
    if span_start <= today <= span_end:
        tx = chart_left + ((today - span_start).days / span_days) * chart_width
        parts.append(
            f'<line x1="{tx:.1f}" y1="{HEADER_HEIGHT}" x2="{tx:.1f}" '
            f'y2="{height}" stroke="{TODAY}" stroke-width="1"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def figure_filename(state: ProgrammeState) -> str:
    return f"programme-v{state.version}-{state.view_scale}.svg"
