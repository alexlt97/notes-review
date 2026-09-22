"""Small parsers for Obsidian note formats."""

from __future__ import annotations

import re


WORK_DAYS = ("M", "T", "W", "X", "F")
_DAY_HEADING = re.compile(r"^##[ \t]+([MTWXF]):?(?:[ \t]+#+)?[ \t]*$")


def parse_work_note(markdown: str) -> dict[str, str]:
    """Return non-empty M/T/W/X/F sections in weekday order."""
    sections: dict[str, list[str]] = {}
    active_day: str | None = None

    for line in markdown.splitlines():
        match = _DAY_HEADING.fullmatch(line)
        if match:
            active_day = match.group(1)
            sections.setdefault(active_day, [])
        elif active_day is not None:
            sections[active_day].append(line)

    return {
        day: "\n".join(sections[day]).strip()
        for day in WORK_DAYS
        if day in sections and "\n".join(sections[day]).strip()
    }


def parse_personal_note(markdown: str) -> str:
    """Treat the complete daily note as the raw text to refine."""
    return markdown


def resolve_personal_date(value: str) -> str:
    """Resolve `today` or validate an ISO daily-note date."""
    from datetime import date

    if value.lower() == "today":
        return date.today().isoformat()
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Date must be 'today' or a valid YYYY-MM-DD date.") from exc
    if parsed.isoformat() != value:
        raise ValueError("Date must be 'today' or a valid YYYY-MM-DD date.")
    return parsed.isoformat()
