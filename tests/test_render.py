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


class SlugTests(unittest.TestCase):
    def test_colliding_slugs_are_made_unique(self):
        tabs = [{"slug": "tryout"}, {"slug": "tryout"}, {"slug": "tryout"}]
        self.assertEqual(render.unique_slugs(tabs), ["tryout", "tryout-2", "tryout-3"])

    def test_empty_slug_falls_back_to_the_registration_id(self):
        self.assertEqual(render.unique_slugs([{"slug": "", "id": "1126331"}]),
                         ["1126331"])

    def test_no_slug_and_no_id_still_gets_an_id(self):
        self.assertEqual(render.unique_slugs([{}]), ["registration-1"])

    def test_two_registrations_never_share_a_panel_id(self):
        tabs = [dict(TABS[0], slug="same"), dict(TABS[1], slug="same")]
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        self.assertEqual(html.count('id="panel-same"'), 1)
        self.assertEqual(html.count('id="panel-same-2"'), 1)
        self.assertEqual(html.count('data-slug="same-2"'), 1)
        self.assertNotIn('id="panel-"', html)


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
        # The scoreboard reads as a figure plus a suffix, so a flat run shows
        # an em dash captioned "no change" rather than the words on their own.
        self.assertIn("no change", self.html)

    def test_shows_the_countdown(self):
        # Same shape: the digit is the value, "days out" is the suffix.
        self.assertIn(">9<", self.html)
        self.assertIn("days out", self.html)

    def test_first_run_reads_as_a_dash_with_a_caption(self):
        # A tab with no previous count has no delta to show; it must not
        # render "+0" or an empty cell.
        tabs = [dict(TABS[0], previous=None, delta=0)]
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        self.assertIn("first run", html)
        self.assertNotIn("+0", html)

    def test_renders_dimension_labels(self):
        self.assertIn("Advanced", self.html)
        self.assertIn("Intermediate", self.html)

    def test_charts_render_as_bar_rows(self):
        # Charts are plain HTML bars now; the signups-over-time SVG was cut.
        self.assertIn('class="bar-row"', self.html)
        self.assertNotIn("<svg", self.html)

    def test_no_signups_over_time_section(self):
        self.assertNotIn("Signups over time", self.html)

    def test_has_no_external_references(self):
        for forbidden in ["http://", "https://cdn", "<script src", "<link rel=\"stylesheet\""]:
            self.assertNotIn(forbidden, self.html)

    def test_escapes_html_in_labels(self):
        tabs = [dict(TABS[0], name="Tryout <script>alert(1)</script>")]
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_output_passes_the_pii_scan(self):
        piiscan.assert_clean(self.html)

    def test_panel_ids_match_the_tab_buttons(self):
        for slug in ["travel-tryout", "skills-course"]:
            self.assertIn('data-slug="%s"' % slug, self.html)
            self.assertIn('id="panel-%s"' % slug, self.html)

    def test_handles_no_active_registrations(self):
        html = render.render_dashboard([], "now", "2026-08-15")
        self.assertIn("No active registrations", html)


def _tab_with_crosstab(skipped):
    """A tab carrying one grade-by-question breakdown."""
    return {
        "slug": "camp",
        "name": "Camp",
        "event": {"label": "Aug 18–20", "start": "2026-08-18", "end": "2026-08-20"},
        "delta": 0,
        "previous": 5,
        "metrics": {
            "total": 6 + skipped,
            "grades": [("3rd Grade", 2), ("6th Grade", 4)],
            "dimensions": [{"question": "Sessions?",
                            "values": [("Advanced", 4), ("Intermediate", 2)]}],
            "crosstabs": [{
                "question": "Sessions?",
                "categories": ["Advanced", "Intermediate"],
                "rows": [
                    {"grade": "3rd Grade", "counts": {"Intermediate": 2}, "total": 2},
                    {"grade": "6th Grade", "counts": {"Advanced": 4}, "total": 4},
                ],
                "skipped": skipped,
            }],
            "timeline": [{"date": "2026-08-12", "new": 6, "cumulative": 6}],
        },
    }


class CrosstabRenderTests(unittest.TestCase):
    def test_renders_a_legend_with_each_category_total(self):
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertIn("swatch", html)
        self.assertIn("Advanced", html)
        self.assertIn("Intermediate", html)

    def test_each_answer_gets_its_own_chart_never_a_combined_bar(self):
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertEqual(html.count('<div class="split">'), 2)
        self.assertNotIn('class="stack"', html)
        self.assertNotIn('class="seg"', html)

    def test_every_grade_appears_in_every_chart_including_at_zero(self):
        # The two charts must read row for row, so a grade with nobody in one
        # answer still gets a labelled row showing 0.
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertEqual(html.count("3rd Grade"), 2)
        self.assertEqual(html.count("6th Grade"), 2)
        self.assertIn(">0<", html)

    def test_both_charts_share_one_scale(self):
        # 4 is the largest cell, so it is the only 100%-wide bar; the grade with
        # 2 must render at half that, not at full width on its own scale.
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertIn("width:100.0%", html)
        self.assertIn("width:50.0%", html)

    def test_grade_card_is_dropped_when_everyone_answered(self):
        # The breakdown's own right-hand column already carries grade totals.
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertNotIn("By grade</h3>", html)

    def test_grade_card_is_kept_when_some_people_skipped(self):
        # The breakdown then covers only part of the field, so the full grade
        # distribution still needs showing.
        html = render.render_dashboard([_tab_with_crosstab(9)], "now", "2026-08-15")
        self.assertIn("By grade</h3>", html)

    def test_the_flat_question_card_is_replaced_not_duplicated(self):
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertEqual(html.count("Sessions?"), 1)

    def test_crosstab_output_passes_the_pii_scan(self):
        html = render.render_dashboard([_tab_with_crosstab(3)], "now", "2026-08-15")
        piiscan.assert_clean(html)


if __name__ == "__main__":
    unittest.main()
