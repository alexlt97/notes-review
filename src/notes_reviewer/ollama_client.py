"""Minimal Ollama chat API client using Python's standard library."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

from .models import ModelResult


class OllamaError(Exception):
    """Raised when Ollama cannot produce a usable response."""


class OllamaUnavailable(OllamaError):
    pass


class ModelUnavailable(OllamaError):
    pass


class InvalidModelResponse(OllamaError):
    pass


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "markdown": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["markdown", "tags"],
    "additionalProperties": False,
}


def _clean_tags(raw_tags: list[str]) -> tuple[str, ...]:
    tags: list[str] = []
    for raw_tag in raw_tags:
        tag = raw_tag.strip().lower().lstrip("#")
        tag = "-".join(part for part in tag.replace("_", "-").split() if part)
        tag = "".join(char for char in tag if char.isascii() and (char.isalnum() or char == "-"))
        tag = "-".join(part for part in tag.split("-") if part)
        if tag and tag not in tags:
            tags.append(tag[:48].strip("-"))
        if len(tags) == 6:
            break
    return tuple(tag for tag in tags if tag)


def _validate_result(content: str) -> ModelResult:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise InvalidModelResponse("The model returned an invalid response. No file was modified.") from exc

    if not isinstance(payload, dict) or set(payload) != {"markdown", "tags"}:
        raise InvalidModelResponse("The model returned an invalid response. No file was modified.")
    markdown = payload["markdown"]
    raw_tags = payload["tags"]
    if not isinstance(markdown, str) or not isinstance(raw_tags, list):
        raise InvalidModelResponse("The model returned an invalid response. No file was modified.")
    if any(not isinstance(tag, str) for tag in raw_tags):
        raise InvalidModelResponse("The model returned an invalid response. No file was modified.")

    markdown = markdown.strip()
    if (
        not markdown
        or "\x00" in markdown
        or (markdown.startswith("```") and markdown.endswith("```"))
        or markdown.splitlines()[:1] == ["---"]
    ):
        raise InvalidModelResponse("The model returned an invalid response. No file was modified.")
    return ModelResult(markdown=markdown, tags=_clean_tags(raw_tags))


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def refine(self, *, model: str, system_prompt: str, user_prompt: str) -> ModelResult:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": _RESPONSE_SCHEMA,
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }
        try:
            response_body = self._post(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            lowered = detail.lower()
            if "think" in body and "think" in lowered and any(
                marker in lowered for marker in ("unknown", "unmarshal", "invalid", "unsupported")
            ):
                compatible_body = dict(body)
                compatible_body.pop("think", None)
                try:
                    response_body = self._post(compatible_body)
                except urllib.error.HTTPError as retry_exc:
                    raise self._http_error(model, retry_exc) from retry_exc
                except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as retry_exc:
                    raise OllamaUnavailable(
                        f"Ollama is not reachable at {self.base_url}."
                    ) from retry_exc
            else:
                raise self._http_error(model, exc, detail) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            raise OllamaUnavailable(f"Ollama is not reachable at {self.base_url}.") from exc
        except UnicodeDecodeError as exc:
            raise InvalidModelResponse("The model returned an invalid response. No file was modified.") from exc

        try:
            response = json.loads(response_body)
            content = response["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content is not a string")
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise InvalidModelResponse("The model returned an invalid response. No file was modified.") from exc
        return _validate_result(content)

    def _post(self, body: dict[str, object]) -> str:
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    @staticmethod
    def _http_error(model: str, exc: urllib.error.HTTPError, detail: str | None = None) -> OllamaError:
        if detail is None:
            detail = exc.read().decode("utf-8", errors="replace")
        detail = detail.lower()
        if "model" in detail and ("not found" in detail or "does not exist" in detail):
            return ModelUnavailable(f"Model {model} is not available.")
        return OllamaError(f"Ollama request failed (HTTP {exc.code}). Check the local Ollama service and model.")
