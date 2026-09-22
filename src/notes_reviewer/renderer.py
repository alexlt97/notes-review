"""Rendering of YAML front matter and refined Markdown."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from collections.abc import Iterable

from .models import ModelResult

_SECTION_NAMES = (
    "Daily Summary",
    "Work Completed",
    "Technical Findings",
    "Decisions",
    "Problems / Blockers",
    "Next Steps",
)
_SECTION_HEADING = re.compile(
    r"^#{1,6}[ \t]+(" + "|".join(re.escape(name) for name in _SECTION_NAMES) + r")[ \t]*#*[ \t]*$"
)
_WORK_DAY_NUMBERS = {"M": 1, "T": 2, "W": 3, "X": 4, "F": 5}
_WORK_DAY_NAMES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "X": "Thursday",
    "F": "Friday",
}


def rank_work_tags(days: dict[str, ModelResult], limit: int = 6) -> tuple[str, ...]:
    """Return the most frequent work tags, preserving first appearance on ties."""
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    position = 0
    for result in days.values():
        for tag in result.tags:
            if tag not in counts:
                counts[tag] = 0
                first_seen[tag] = position
                position += 1
            counts[tag] += 1

    ranked = sorted(counts, key=lambda tag: (-counts[tag], first_seen[tag]))
    return tuple(ranked[:limit])


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _format_sections(markdown: str, heading_level: int) -> str:
    """Normalize known section levels and discard headings with no content."""
    lines: list[tuple[str, bool]] = []
    fence: str | None = None
    for line in markdown.strip().splitlines():
        stripped = line.lstrip()
        marker = stripped[:3] if stripped.startswith(("```", "~~~")) else None
        if fence is not None:
            lines.append((line, False))
            if marker == fence:
                fence = None
            continue
        if marker is not None:
            fence = marker
            lines.append((line, False))
            continue

        match = _SECTION_HEADING.fullmatch(line)
        if match:
            lines.append((f"{'#' * heading_level} {match.group(1)}", True))
        else:
            lines.append((line, False))

    output: list[str] = []
    current_header: str | None = None
    current_body: list[str] = []

    def flush_section() -> None:
        if current_header is not None and any(line.strip() for line in current_body):
            output.append(current_header)
            output.extend(current_body)

    for line, is_section in lines:
        if is_section:
            flush_section()
            current_header = line
            current_body = []
        elif current_header is None:
            output.append(line)
        else:
            current_body.append(line)
    flush_section()
    return "\n".join(output).strip()


def _front_matter(*, note_type: str, model: str, tags: Iterable[str], reviewed_at: datetime,
                  week: int | None = None, year: int | None = None,
                  note_date: str | None = None) -> str:
    lines = ["---", f"type: {note_type}"]
    if note_type == "work":
        assert week is not None and year is not None
        lines.extend((f"week: {week}", f"year: {year}"))
    else:
        assert note_date is not None
        lines.append(f"date: {note_date}")
    tag_list = list(tags)
    lines.extend((f"reviewed_at: {_yaml_string(reviewed_at.isoformat(timespec='seconds'))}",
                  f"model: {_yaml_string(model)}", "tags:" if tag_list else "tags: []"))
    for tag in tag_list:
        lines.append(f"  - {tag}")
    lines.append("---")
    return "\n".join(lines)


def render_personal(result: ModelResult, *, note_date: str, model: str,
                    reviewed_at: datetime | None = None) -> str:
    timestamp = reviewed_at or datetime.now().astimezone()
    markdown = _format_sections(result.markdown, heading_level=2)
    if not markdown:
        raise ValueError("The model returned an invalid response. No file was modified.")
    front_matter = _front_matter(
        note_type="personal", model=model, tags=result.tags, reviewed_at=timestamp,
        note_date=note_date,
    )
    return f"{front_matter}\n\n{markdown}\n"


def render_work(days: dict[str, ModelResult], *, week: int, year: int, model: str,
                reviewed_at: datetime | None = None) -> str:
    timestamp = reviewed_at or datetime.now().astimezone()
    tags = rank_work_tags(days)

    rendered_days = {
        day: _format_sections(result.markdown, heading_level=3)
        for day, result in days.items()
    }
    if not rendered_days or any(not markdown for markdown in rendered_days.values()):
        raise ValueError("The model returned an invalid response. No file was modified.")

    front_matter = _front_matter(
        note_type="work", model=model, tags=tags, reviewed_at=timestamp,
        week=week, year=year,
    )
    sections = [front_matter]
    for day, markdown in rendered_days.items():
        weekday_date = date.fromisocalendar(year, week, _WORK_DAY_NUMBERS[day])
        sections.append(
            f"## {_WORK_DAY_NAMES[day]}, {weekday_date.isoformat()}\n\n{markdown}"
        )
    return "\n\n".join(sections) + "\n"
