"""Tests with a fake client, so no API key is needed.

Run with:  python -m unittest test_reviewer.py
"""

import tempfile
import unittest
from pathlib import Path

from reviewer import ReviewError, read_code_file, review_code, validate_report

GOOD_REPORT = """## EXPLANATION
The code sums the prices in a shopping cart.

## BUG_REPORT
- [CRITICAL] calculate_total: the loop goes one index too far and raises IndexError.

## REFACTORED_CODE
```python
def calculate_total(items):
    return sum(i["price"] * i["qty"] for i in items)
```"""

BAD_REPORT = "Sure! Here is your review: the code looks fine."


class FakeModels:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def generate_content(self, model, contents, config):
        self.prompts.append(contents)
        return type("R", (), {"text": self.answers.pop(0)})()


class FakeClient:
    def __init__(self, *answers):
        self.models = FakeModels(*answers)


class TestReadFile(unittest.TestCase):
    def test_reads_code_and_detects_language(self):
        code, lang, name = read_code_file("examples/buggy_cart.py")
        self.assertEqual((lang, name), ("python", "buggy_cart.py"))
        self.assertIn("    for i in range", code)  # indentation preserved

    def test_errors(self):
        with tempfile.TemporaryDirectory() as d:
            empty = Path(d) / "empty.py"
            empty.write_text("   ")
            for path in ["missing.py", str(empty), "notes.txt", d + "/folder.py"]:
                if path.endswith("folder.py"):
                    Path(path).mkdir()
                with self.assertRaises(ReviewError):
                    read_code_file(path)

    def test_non_utf8_file_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "old.py"
            f.write_bytes("name = 'caf\xe9'\n".encode("latin-1"))
            code, _, _ = read_code_file(f)
            self.assertIn("café", code)


class TestValidation(unittest.TestCase):
    def test_good_report_passes(self):
        self.assertEqual(validate_report(GOOD_REPORT), (True, ""))

    def test_missing_section_fails(self):
        ok, reason = validate_report(GOOD_REPORT.replace("## BUG_REPORT", "## BUGS"))
        self.assertFalse(ok)
        self.assertIn("BUG_REPORT", reason)

    def test_two_code_blocks_fail(self):
        ok, _ = validate_report(GOOD_REPORT + "\n```python\nprint(1)\n```")
        self.assertFalse(ok)

    def test_chatty_answer_fails(self):
        self.assertFalse(validate_report(BAD_REPORT)[0])


class TestReview(unittest.TestCase):
    def test_returns_valid_report(self):
        client = FakeClient(GOOD_REPORT)
        self.assertEqual(review_code(client, "x = 1", "python", "a.py"), GOOD_REPORT)
        self.assertIn("```python\nx = 1\n```", client.models.prompts[0])

    def test_retries_once_when_format_is_wrong(self):
        client = FakeClient(BAD_REPORT, GOOD_REPORT)
        review_code(client, "x = 1", "python", "a.py")
        self.assertIn("previous answer was rejected", client.models.prompts[1])

    def test_gives_up_after_two_bad_answers(self):
        with self.assertRaises(ReviewError):
            review_code(FakeClient(BAD_REPORT, BAD_REPORT), "x = 1", "python", "a.py")


if __name__ == "__main__":
    unittest.main()
