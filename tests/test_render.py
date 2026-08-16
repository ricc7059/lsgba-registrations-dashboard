import unittest

from scripts import piiscan, render

TABS = [
    {
        "slug": "travel-tryout",
        "name": "2026 LSGBA Travel Tryout Registration",
        "event": {"label": "Aug 24–27", "start": "2026-08-24", "end": "2026-08-27"},
        "delta": 4,
        "previous": 19,
        "metrics": {
            "total": 23,
            "grades": [("3rd Grade", 3), ("6th Grade", 9)],
            "dimensions": [{"question": "Interested in coaching?",
                            "values": [("No response", 20), ("Assistant Coach", 2)]}],
            "timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5},
                         {"date": "2026-08-14", "new": 18, "cumulative": 23}],
        },
    },
    {
        "slug": "skills-course",
        "name": "2026 LSGBA / NSA 3 Day Pre-Tryout Skills Course",
        "event": {"label": "Aug 18–20", "start": "2026-08-18", "end": "2026-08-20"},
        "delta": 0,
        "previous": 37,
        "metrics": {
            "total": 37,
            "grades": [("8th Grade", 4)],
            "dimensions": [{"question": "Sessions?",
                            "values": [("Advanced", 24), ("Intermediate", 13)]}],
            "timeline": [{"date": "2026-08-12", "new": 37, "cumulative": 37}],
        },
    },
]


class DaysUntilTests(unittest.TestCase):
    def test_counts_days_forward(self):
        self.assertEqual(render.days_until("2026-08-24", "2026-08-15"), 9)

    def test_zero_on_the_day(self):
        self.assertEqual(render.days_until("2026-08-15", "2026-08-15"), 0)

    def test_negative_once_past(self):
        self.assertEqual(render.days_until("2026-08-10", "2026-08-15"), -5)

    def test_none_when_no_date(self):
        self.assertIsNone(render.days_until(None, "2026-08-15"))


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.html = render.render_dashboard(TABS, "Aug 15, 2026 9:55 PM", "2026-08-15")

    def test_produces_a_full_document(self):
        self.assertTrue(self.html.lstrip().startswith("<!doctype html>"))
        self.assertIn("</html>", self.html)

    def test_has_one_tab_button_per_registration(self):
        self.assertEqual(self.html.count('class="tab-button'), 2)

    def test_has_one_panel_per_registration(self):
        self.assertEqual(self.html.count('class="tab-panel'), 2)

    def test_shows_each_total(self):
        self.assertIn(">23<", self.html)
        self.assertIn(">37<", self.html)

    def test_never_shows_a_combined_total(self):
        # 23 + 37 = 60 must not appear anywhere.
        self.assertNotIn(">60<", self.html)

    def test_shows_a_positive_delta_with_a_sign(self):
        self.assertIn("+4", self.html)

    def test_shows_no_change_when_delta_is_zero(self):
        self.assertIn("No change", self.html)

    def test_shows_the_countdown(self):
        self.assertIn("9 days", self.html)

    def test_renders_dimension_labels(self):
        self.assertIn("Advanced", self.html)
        self.assertIn("Intermediate", self.html)

    def test_draws_svg_charts(self):
        self.assertIn("<svg", self.html)

    def test_has_no_external_references(self):
        for forbidden in ["http://", "https://cdn", "<script src", "<link rel=\"stylesheet\""]:
            self.assertNotIn(forbidden, self.html)

    def test_escapes_html_in_labels(self):
        tabs = [dict(TABS[0], name="Tryout <script>alert(1)</script>")]
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_output_passes_the_pii_scan(self):
        piiscan.assert_clean(self.html)

    def test_handles_no_active_registrations(self):
        html = render.render_dashboard([], "now", "2026-08-15")
        self.assertIn("No active registrations", html)


if __name__ == "__main__":
    unittest.main()
