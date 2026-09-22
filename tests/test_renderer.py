import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from notes_reviewer.models import ModelResult
from notes_reviewer.renderer import render_personal, render_work
from notes_reviewer.reviewer import atomic_write


class RendererTests(unittest.TestCase):
    def test_personal_front_matter_and_content(self):
        rendered = render_personal(
            ModelResult("### Daily Summary\nA concise summary.\n\n### Next Steps\n", ("robotics", "camera-system")),
            note_date="2026-09-20",
            model="qwen3:14b",
            reviewed_at=datetime(2026, 9, 21, 8, 30, tzinfo=timezone.utc),
        )
        self.assertTrue(rendered.startswith("---\ntype: personal\ndate: 2026-09-20\n"))
        self.assertIn('model: "qwen3:14b"', rendered)
        self.assertIn("  - camera-system", rendered)
        self.assertIn("## Daily Summary\nA concise summary.", rendered)
        self.assertNotIn("Next Steps", rendered)

    def test_work_omits_missing_days_and_combines_grounded_tags(self):
        rendered = render_work(
            {
                "M": ModelResult("### Work Completed\nTested the mount.", ("robotics",)),
                "X": ModelResult("### Next Steps\nTest the second axis.", ("camera", "robotics")),
            },
            week=38,
            year=2026,
            model="ministral-3:14b",
            reviewed_at=datetime(2026, 9, 21, 8, 30, tzinfo=timezone.utc),
        )
        self.assertIn("week: 38\nyear: 2026", rendered)
        self.assertIn("## M — Monday, 2026-09-14\n\n### Work Completed", rendered)
        self.assertIn("## X — Thursday, 2026-09-17\n\n### Next Steps", rendered)
        self.assertNotIn("## W\n", rendered)
        self.assertEqual(rendered.count("  - robotics"), 1)

    def test_work_renderer_normalizes_section_heading_level(self):
        rendered = render_work(
            {"M": ModelResult("## Technical Findings\nRenderer needs a test.\n\n```md\n## Next Steps\n```", ())},
            week=38,
            year=2026,
            model="ministral-3:14b",
        )
        self.assertIn("## M — Monday, 2026-09-14\n\n### Technical Findings", rendered)
        self.assertIn("```md\n## Next Steps\n```", rendered)
        self.assertIn("tags: []", rendered)

    def test_atomic_write_replaces_complete_output(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "Refined_Personal" / "2026-09-20.md"
            atomic_write(destination, "first version\n")
            atomic_write(destination, "second version\n")
            self.assertEqual(destination.read_text(encoding="utf-8"), "second version\n")
            self.assertEqual([path.name for path in destination.parent.iterdir()], [destination.name])


if __name__ == "__main__":
    unittest.main()
