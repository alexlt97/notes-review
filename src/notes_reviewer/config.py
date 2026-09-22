"""Configuration loading for the notes-review CLI."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "qwen3:14b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    vault_path: Path | None
    default_model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL


def _config_path(explicit_path: str | None) -> Path | None:
    selected = explicit_path or os.environ.get("NOTES_REVIEWER_CONFIG")
    if selected:
        path = Path(selected).expanduser()
        if not path.is_file():
            raise ConfigurationError(f"Config file not found: {path}")
        return path

    local_path = Path.cwd() / "config.toml"
    if local_path.is_file():
        return local_path

    user_path = Path.home() / ".config" / "notes-reviewer" / "config.toml"
    if user_path.is_file():
        return user_path
    return None


def load_config(explicit_path: str | None = None) -> Config:
    """Load TOML configuration, falling back to the documented defaults."""
    path = _config_path(explicit_path)
    if path is None:
        return Config(vault_path=None)

    try:
        with path.open("rb") as config_file:
            values = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Could not read config file {path}: {exc}") from exc

    vault_value = values.get("vault_path", "")
    model_value = values.get("default_model", DEFAULT_MODEL)
    url_value = values.get("ollama_url", DEFAULT_OLLAMA_URL)
    if not isinstance(vault_value, str):
        raise ConfigurationError("vault_path in config.toml must be a string.")
    if not isinstance(model_value, str) or not model_value.strip():
        raise ConfigurationError("default_model in config.toml must be a non-empty string.")
    if not isinstance(url_value, str) or not url_value.strip():
        raise ConfigurationError("ollama_url in config.toml must be a non-empty string.")

    vault_path = Path(vault_value).expanduser() if vault_value.strip() else None
    return Config(
        vault_path=vault_path,
        default_model=model_value.strip(),
        ollama_url=url_value.rstrip("/"),
    )


def require_vault_path(config: Config) -> Path:
    if config.vault_path is None:
        raise ConfigurationError("Set vault_path in config.toml to the Obsidian vault root containing Personal/ and Work/.")
    return config.vault_path
