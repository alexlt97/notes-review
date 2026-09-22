"""End-to-end note reading, generation, and safe output writing."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from importlib.resources import files

from .config import Config, require_vault_path
from .models import ModelResult
from .ollama_client import OllamaClient
from .parser import parse_personal_note, parse_work_note
from .paths import personal_output_path, personal_source_path, work_output_path, work_source_path
from .renderer import render_personal, render_work


class ReviewError(Exception):
    """Expected user-facing review error."""


@dataclass(frozen=True)
class ReviewResult:
    content: str
    destination: Path


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReviewError(f"Source note not found: {path}") from exc
    except (OSError, UnicodeError) as exc:
        raise ReviewError(f"Could not read source note: {path}") from exc


def _prompt(name: str) -> str:
    return files("notes_reviewer.prompts").joinpath(name).read_text(encoding="utf-8")


def _model_result(client: OllamaClient, *, model: str, template: str, source: str) -> ModelResult:
    return client.refine(
        model=model,
        system_prompt=_prompt("shared.md"),
        user_prompt=template.format(source=source),
    )


def review_personal(config: Config, note_date: str, model_override: str | None = None) -> ReviewResult:
    vault_path = require_vault_path(config)
    source_path = personal_source_path(vault_path, note_date)
    source = parse_personal_note(_read_source(source_path))
    model = model_override or config.default_model
    client = OllamaClient(config.ollama_url)
    result = _model_result(client, model=model, template=_prompt("personal_review.md"), source=source)
    content = render_personal(result, note_date=note_date, model=model)
    return ReviewResult(content=content, destination=personal_output_path(vault_path, note_date))


def review_work(config: Config, week: int, year: int, model_override: str | None = None) -> ReviewResult:
    vault_path = require_vault_path(config)
    source_path = work_source_path(vault_path, week)
    source = _read_source(source_path)
    days = parse_work_note(source)
    if not days:
        raise ReviewError(f"No work-day sections found in Week {week}.md.")

    model = model_override or config.default_model
    client = OllamaClient(config.ollama_url)
    refined_days: dict[str, ModelResult] = {}
    template = _prompt("work_review.md")
    for day, day_source in days.items():
        refined_days[day] = _model_result(client, model=model, template=template, source=day_source)

    content = render_work(refined_days, week=week, year=year, model=model)
    return ReviewResult(content=content, destination=work_output_path(vault_path, week))


def atomic_write(path: Path, content: str) -> None:
    """Replace an output file only after its complete content is on disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
