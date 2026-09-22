# Obsidian Notes Reviewer

A small local CLI that rewrites personal daily notes and weekly work notes with Ollama. It reads the source note, generates the complete result in memory, and atomically replaces only the matching file under `Refined_Personal` or `Refined_Work`.

## Setup

Use Python 3.11 or newer. Install Ollama and pull a model, for example:

```sh
ollama pull qwen3:14b
```

Set `vault_path` in `config.toml` to the Obsidian vault root containing the `Personal/` and `Work/` folders. From this directory, create and sync the project environment with uv:

```sh
uv sync
```

This installs the project into `.venv` and creates or updates `uv.lock`. Run project commands with `uv run`; no activation step is needed. The CLI looks for `config.toml` in the current directory, then `~/.config/notes-reviewer/config.toml`. You can select a file explicitly with the global `--config` option or set `NOTES_REVIEWER_CONFIG`.

## Use

```sh
uv run notes-review personal today
uv run notes-review personal 2026-09-20
uv run notes-review personal today --dry-run

uv run notes-review work 38
uv run notes-review work 38 --year 2026
```

The configured default is `qwen3:14b`. Use `--model` to select a different installed model, for example `--model ministral-3:14b`.

When using `--config`, place it before the command:

```sh
uv run notes-review --config /path/to/config.toml personal today
```

Personal source notes are read from `Personal/YYYY-MM-DD.md`; refined notes are written to `Refined_Personal/YYYY-MM-DD.md`. Work sources use `Work/Week N.md`, and results go to `Refined_Work/Week N.md`. Work-day headings include the original day marker, full weekday name, and exact ISO date, such as `## M — Monday, 2026-09-21`. The refined folders are created beside `Personal/` and `Work/` as needed. A work week without `--year` uses the current ISO week-year. Re-running a command replaces the refined note. The source is never written to.

Work-note tags favor concrete technologies, algorithms, libraries, frameworks, protocols, systems, and technical methods found in the source. Generic workflow and status labels are removed, and weekly tags are ranked by how often they occur during the week.

`--dry-run` prints the generated note and does not create or replace an output file. Ollama requests go to the configured local URL; the tool does not use a cloud API.

## Obsidian ribbon plugin

The `obsidian-plugin/` folder contains a small desktop-only Obsidian plugin that runs the CLI directly. It adds ribbon buttons and command palette actions for today's personal note, a selected personal date, and the current work week. The plugin uses `uv`; it does not depend on the Shell Commands or Commander community plugins.

To install it locally:

1. In your vault, create `.obsidian/plugins/notes-reviewer/`.
2. Copy `manifest.json` and `main.js` from this project's `obsidian-plugin/` folder into it.
3. In Obsidian, enable community plugins if needed, reload the app, then enable **Notes Reviewer** in **Settings → Community plugins**.
4. Open **Settings → Notes Reviewer**. Set **uv executable** to the full path to `uv` if needed, and **Project folder** to this project's full path (the folder containing `pyproject.toml` and `config.toml`).

The plugin invokes `uv run --project <project-folder> notes-review ...` with shell execution disabled. Reviews still use the CLI's existing config and output behavior. Use the calendar-search ribbon button or the **Review a personal note for a date** command to choose any `YYYY-MM-DD` date. The completion notice includes the CLI's output path. Running on mobile is not supported because the plugin launches a local process.

## Tests

Run the standard-library unit tests from this directory:

```sh
uv run python -m unittest discover -s tests
```
