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

    def test_detects_iso_date(self):
        # A renamed date-of-birth column arrives as YYYY-MM-DD. The timeline
        # axis emits only MM/DD, so this rule costs the real page nothing.
        findings = piiscan.scan("<text>2014-05-06</text>")
        self.assertIn("iso-date", [kind for kind, _ in findings])

    def test_timeline_axis_labels_are_not_flagged(self):
        # What the renderer actually puts on the axis.
        self.assertEqual(piiscan.scan('<text class="axis">08/14</text>'), [])

    def test_detects_phone_number(self):
        for number in ["504-555-0143", "504.555.0143", "504 555 0143", "5045550143"]:
            findings = piiscan.scan("<p>call %s</p>" % number)
            self.assertIn("phone", [kind for kind, _ in findings], number)

    def test_counts_and_totals_are_not_flagged_as_phone_numbers(self):
        self.assertEqual(piiscan.scan("<p>23 registered, 37 total, 9 in 6th</p>"), [])

    def test_exception_message_reports_kinds_and_counts_only(self):
        html = "<p>a@example.com b@example.com 03/18/2015</p>"
        with self.assertRaises(piiscan.PIIFound) as caught:
            piiscan.assert_clean(html)
        message = str(caught.exception)
        self.assertIn("2 email", message)
        self.assertIn("1 date", message)
        # The PII itself must never ride along in the message.
        self.assertNotIn("example.com", message)
        self.assertNotIn("03/18/2015", message)

    def test_assert_clean_raises_on_poisoned_fixture(self):
        with open(os.path.join(FIXTURES, "poisoned.html")) as fh:
            html = fh.read()
        with self.assertRaises(piiscan.PIIFound):
            piiscan.assert_clean(html)

    def test_assert_clean_passes_on_clean_html(self):
        piiscan.assert_clean("<p>37 registered</p>")


if __name__ == "__main__":
    unittest.main()
