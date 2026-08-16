import os
import unittest

from scripts import piiscan

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class ScanTests(unittest.TestCase):
    def test_clean_html_produces_no_findings(self):
        html = "<html><body><p>23 registered, 6th grade leads with 9</p></body></html>"
        self.assertEqual(piiscan.scan(html), [])

    def test_detects_email_address(self):
        findings = piiscan.scan("<p>reach me at parent@example.com</p>")
        self.assertIn("email", [kind for kind, _ in findings])

    def test_detects_date_of_birth_pattern(self):
        findings = piiscan.scan("<p>born 03/18/2015</p>")
        self.assertIn("date", [kind for kind, _ in findings])

    def test_iso_dates_are_not_flagged(self):
        # The timeline axis uses ISO dates and must not trip the scan.
        self.assertEqual(piiscan.scan("<text>2026-08-14</text>"), [])

    def test_assert_clean_raises_on_poisoned_fixture(self):
        with open(os.path.join(FIXTURES, "poisoned.html")) as fh:
            html = fh.read()
        with self.assertRaises(piiscan.PIIFound):
            piiscan.assert_clean(html)

    def test_assert_clean_passes_on_clean_html(self):
        piiscan.assert_clean("<p>37 registered</p>")


if __name__ == "__main__":
    unittest.main()
