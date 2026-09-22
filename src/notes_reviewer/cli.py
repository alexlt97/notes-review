"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from .config import ConfigurationError, load_config
from .ollama_client import OllamaError
from .parser import resolve_personal_date
from .paths import resolve_work_year, validate_iso_week
from .reviewer import ReviewError, atomic_write, review_personal, review_work


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notes-review", description="Refine Obsidian notes with local Ollama.")
    parser.add_argument("--config", help="Path to config.toml (also settable with NOTES_REVIEWER_CONFIG).")
    commands = parser.add_subparsers(dest="kind", required=True)

    personal = commands.add_parser("personal", help="Review a personal daily note.")
    personal.add_argument("date", help="'today' or a YYYY-MM-DD date.")
    personal.add_argument("--model", help="Override the configured Ollama model.")
    personal.add_argument("--dry-run", action="store_true", help="Print the result without writing a file.")

    work = commands.add_parser("work", help="Review a weekly work note.")
    work.add_argument("week", type=int, help="ISO week number (1–53).")
    work.add_argument("--year", type=int, help="ISO week-year; defaults to the current ISO week-year.")
    work.add_argument("--model", help="Override the configured Ollama model.")
    work.add_argument("--dry-run", action="store_true", help="Print the result without writing a file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.kind == "personal":
            note_date = resolve_personal_date(args.date)
            result = review_personal(config, note_date, args.model)
        else:
            if not 1 <= args.week <= 53:
                raise ValueError("Week must be between 1 and 53.")
            year = resolve_work_year(args.year)
            validate_iso_week(year, args.week)
            result = review_work(config, args.week, year, args.model)

        if args.dry_run:
            sys.stdout.write(result.content)
        else:
            atomic_write(result.destination, result.content)
            print(f"Wrote {result.destination}")
        return 0
    except (ConfigurationError, ReviewError, OllamaError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not write refined note: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
