import unittest

from notes_reviewer.parser import parse_work_note


class WorkParserTests(unittest.TestCase):
    def test_parses_only_work_day_headings_in_weekday_order(self):
        source = """# Week 38

Ignored intro text.

## M:
Did A.

## T:
Did B.

## Notes
This remains part of Tuesday until the next work-day heading.

### W
Not a work-day heading.

## X:
Planned C.

## W:

## F:
Did D.
"""
        self.assertEqual(
            parse_work_note(source),
            {
                "M": "Did A.",
                "T": "Did B.\n\n## Notes\nThis remains part of Tuesday until the next work-day heading.\n\n### W\nNot a work-day heading.",
                "X": "Planned C.",
                "F": "Did D.",
            },
        )

    def test_ignores_empty_days_and_unrelated_headings_before_first_day(self):
        self.assertEqual(parse_work_note("## Notes\nIgnored\n\n## M\n \n## W\nWorked."), {"W": "Worked."})


if __name__ == "__main__":
    unittest.main()
