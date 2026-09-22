import unittest

from notes_reviewer.parser import parse_personal_note, resolve_personal_date
from notes_reviewer.paths import personal_output_path, personal_source_path
from pathlib import Path


class PersonalParserTests(unittest.TestCase):
    def test_personal_note_is_kept_as_a_complete_markdown_body(self):
        source = "---\ntags: [raw]\n---\n\n# Today\nKeep the full source.\n"
        self.assertEqual(parse_personal_note(source), source)

    def test_resolves_explicit_iso_date_and_paths(self):
        vault = Path("/vault")
        day = resolve_personal_date("2026-09-20")
        self.assertEqual(day, "2026-09-20")
        self.assertEqual(personal_source_path(vault, day), vault / "Personal/2026-09-20.md")
        self.assertEqual(personal_output_path(vault, day), vault / "Refined_Personal/2026-09-20.md")

    def test_rejects_invalid_date_format(self):
        with self.assertRaises(ValueError):
            resolve_personal_date("2026-9-20")


if __name__ == "__main__":
    unittest.main()
