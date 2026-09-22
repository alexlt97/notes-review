import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from notes_reviewer.ollama_client import (
    InvalidModelResponse,
    ModelUnavailable,
    OllamaClient,
    _validate_result,
)


def http_error(message):
    return HTTPError(
        "http://127.0.0.1:11434/api/chat",
        404,
        "request failed",
        None,
        io.BytesIO(json.dumps({"error": message}).encode("utf-8")),
    )


class OllamaClientTests(unittest.TestCase):
    def test_model_not_found_is_reported_clearly(self):
        client = OllamaClient("http://127.0.0.1:11434")
        with patch.object(client, "_post", side_effect=http_error("model 'qwen3:14b' not found")):
            with self.assertRaisesRegex(ModelUnavailable, "Model qwen3:14b is not available"):
                client.refine(model="qwen3:14b", system_prompt="rules", user_prompt="note")

    def test_retries_without_think_for_older_ollama(self):
        client = OllamaClient("http://127.0.0.1:11434")
        response = json.dumps({
            "message": {
                "content": json.dumps({"markdown": "## Daily Summary\nDone.", "tags": ["notes"]})
            }
        })
        with patch.object(client, "_post", side_effect=[http_error("unknown field think"), response]) as post:
            result = client.refine(model="model", system_prompt="rules", user_prompt="note")
        self.assertEqual(result.markdown, "## Daily Summary\nDone.")
        self.assertIn("think", post.call_args_list[0].args[0])
        self.assertNotIn("think", post.call_args_list[1].args[0])

    def test_rejects_yaml_front_matter_from_model(self):
        with self.assertRaisesRegex(InvalidModelResponse, "invalid response"):
            _validate_result(json.dumps({"markdown": "---\r\ntype: personal", "tags": []}))


if __name__ == "__main__":
    unittest.main()
