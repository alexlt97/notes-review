"""Vault source and destination path resolution."""

from datetime import date
from pathlib import Path


def personal_source_path(vault_path: Path, note_date: str) -> Path:
    return vault_path / "Personal" / f"{note_date}.md"


def personal_output_path(vault_path: Path, note_date: str) -> Path:
    return vault_path / "Refined_Personal" / f"{note_date}.md"


def work_source_path(vault_path: Path, week: int) -> Path:
    return vault_path / "Work" / f"Week {week}.md"


def work_output_path(vault_path: Path, week: int) -> Path:
    return vault_path / "Refined_Work" / f"Week {week}.md"


def resolve_work_year(year: int | None) -> int:
    return year if year is not None else date.today().isocalendar().year


def validate_iso_week(year: int, week: int) -> None:
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValueError(f"Week {week} is not valid for ISO week-year {year}.") from exc
