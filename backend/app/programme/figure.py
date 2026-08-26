from __future__ import annotations

from datetime import date, timedelta
from xml.sax.saxutils import escape as xml_escape

from app.programme.schemas import ProgrammeActivityInput, ProgrammeState

FIGURE_WIDTH = 720
HEADER_HEIGHT = 40
ROW_HEIGHT = 28
NAME_WIDTH = 160
PAD = 8
VOID = "#14120f"
BEAM = "#d8c3a5"
EDGE = "#3a342c"
STAGE = "#e8e8e4"
ACTIVITY = "#7fb0e4"
MILESTONE = "#e8d7b8"
TODAY = "#c45c26"


def render_programme_svg(state: ProgrammeState) -> str:
    rows = _visible_activities(state)
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
        f'<defs><marker id="dependency-arrow" viewBox="0 0 6 6" refX="5" '
        f'refY="3" markerWidth="5" markerHeight="5" orient="auto">'
        f'<path d="M 0 0 L 6 3 L 0 6 Z" fill="{BEAM}"/></marker></defs>'
    ]
    geometry: dict[str, tuple[float, float, float]] = {}
    for index, item in enumerate(rows):
        start_x = chart_left + ((item.start_date - span_start).days / span_days) * chart_width
        finish = item.finish_date or item.start_date
        finish_x = chart_left + ((finish - span_start).days / span_days) * chart_width
        geometry[item.activity_key] = (
            start_x,
            finish_x,
            HEADER_HEIGHT + index * ROW_HEIGHT + ROW_HEIGHT / 2,
        )
    for dependency in state.dependencies:
        source = geometry.get(dependency.source_activity_key)
        target = geometry.get(dependency.target_activity_key)
        if source is None or target is None:
            continue
        x1 = source[0] if dependency.source_endpoint == "start" else source[1]
        x2 = target[0] if dependency.target_endpoint == "start" else target[1]
        source_stub = x1 + (-8 if dependency.source_endpoint == "start" else 8)
        target_stub = x2 + (-8 if dependency.target_endpoint == "start" else 8)
        if dependency.source_endpoint == dependency.target_endpoint == "start":
            trunk = min(source_stub, target_stub) - 8
        elif dependency.source_endpoint == dependency.target_endpoint == "finish":
            trunk = max(source_stub, target_stub) + 8
        elif dependency.source_endpoint == "finish":
            trunk = (
                (source_stub + target_stub) / 2
                if source_stub <= target_stub
                else max(source_stub, target_stub) + 8
            )
        else:
            trunk = min(source_stub, target_stub) - 8
        parts.append(
            f'<path d="M {x1:.1f} {source[2]:.1f} H {source_stub:.1f} '
            f'H {trunk:.1f} V {target[2]:.1f} H {target_stub:.1f} H {x2:.1f}" '
            f'stroke="{BEAM}" stroke-opacity="0.58" stroke-width="1.2" '
            f'fill="none" marker-end="url(#dependency-arrow)"/>'
        )
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
        elif item.kind == "stage":
            parts.append(
                f'<path d="M {x:.1f} {y + 3} H {x + width:.1f} '
                f'M {x:.1f} {y + 3} V {y + 11} '
                f'M {x + width:.1f} {y + 3} V {y + 11}" '
                f'stroke="{STAGE}" stroke-width="3" fill="none"/>'
            )
        else:
            parts.append(
                f'<rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="12" '
                f'rx="1" fill="{ACTIVITY}"/>'
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


def render_programme_markdown(state: ProgrammeState) -> str:
    """Render a durable programme snapshot for issue-document Markdown."""
    rows = _visible_activities(state)
    by_key = {item.activity_key: item for item in rows}
    dependencies_by_target: dict[str, list[str]] = {}
    for dependency in state.dependencies:
        source = by_key.get(dependency.source_activity_key)
        if source is None or dependency.target_activity_key not in by_key:
            continue
        relationship = (
            f"{dependency.source_endpoint[0].upper()}"
            f"{dependency.target_endpoint[0].upper()}"
        )
        lag = f" +{dependency.lag_days}d" if dependency.lag_days else ""
        dependencies_by_target.setdefault(dependency.target_activity_key, []).append(
            f"{source.name} ({relationship}{lag})"
        )
    lines = [
        f"**Current Programme v{state.version} — static snapshot**",
        "",
        "| Stage / activity | Start | Finish | Duration | Dependency |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for item in rows:
        label = _programme_row_label(item.name, kind=item.kind)
        finish = item.finish_date or item.start_date
        duration = "Milestone" if item.kind == "milestone" else _days(item.duration_days)
        dependency = ", ".join(dependencies_by_target.get(item.activity_key, [])) or "—"
        lines.append(
            "| "
            f"{label} | {_display_date(item.start_date)} | {_display_date(finish)} | "
            f"{duration} | {dependency} |"
        )
    if not rows:
        lines.append("| — | — | — | — | No programme activities recorded |")
    return "\n".join(lines)


def _visible_activities(state: ProgrammeState) -> list[ProgrammeActivityInput]:
    collapsed = set(state.collapsed_stage_keys)
    return [
        item
        for item in state.activities
        if item.kind == "stage"
        or not item.parent_key
        or item.parent_key not in collapsed
    ]


def _programme_row_label(name: str, *, kind: str) -> str:
    escaped = name.replace("|", "\\|")
    if kind == "stage":
        return f"**{escaped}**"
    if kind == "milestone":
        return f"↳ ◆ {escaped}"
    return f"↳ {escaped}"


def _display_date(value: date) -> str:
    return f"{value.day} {value.strftime('%b %Y')}"


def _days(value: int) -> str:
    return f"{value} day" if value == 1 else f"{value} days"
