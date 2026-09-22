import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from notes_reviewer.config import Config
from notes_reviewer.ollama_client import OllamaUnavailable
from notes_reviewer.reviewer import review_work


class ReviewSafetyTests(unittest.TestCase):
    def test_failed_generation_leaves_existing_refined_note_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            source = vault / "Work" / "Week 38.md"
            destination = vault / "Refined_Work" / "Week 38.md"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_text("## M\nTested camera calibration.\n", encoding="utf-8")
            destination.write_text("previous refined content\n", encoding="utf-8")
            original_source = source.read_text(encoding="utf-8")

            with patch("notes_reviewer.reviewer.OllamaClient") as client_type:
                client_type.return_value.refine.side_effect = OllamaUnavailable("offline")
                with self.assertRaises(OllamaUnavailable):
                    review_work(Config(vault_path=vault), 38, 2026)

            self.assertEqual(source.read_text(encoding="utf-8"), original_source)
            self.assertEqual(destination.read_text(encoding="utf-8"), "previous refined content\n")


if __name__ == "__main__":
    unittest.main()
