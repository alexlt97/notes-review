"""Shared data types used by the reviewer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelResult:
    markdown: str
    tags: tuple[str, ...]
