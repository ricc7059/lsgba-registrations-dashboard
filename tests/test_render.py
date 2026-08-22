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

    def test_shows_the_countdown(self):
        # The digit is the value, "days out" is the suffix.
        self.assertIn(">9<", self.html)
        self.assertIn("days out", self.html)

    def test_countdown_carries_the_event_date_as_numbers_for_the_browser(self):
        # Baked-in at build time the countdown goes stale on every quiet day, so
        # the browser recomputes it. The date must NOT be an ISO string: the PII
        # scanner reads YYYY-MM-DD as a possible date of birth and would refuse
        # to publish the page.
        self.assertIn('data-cd-y="2026" data-cd-m="8" data-cd-d="24"', self.html)
        self.assertIn('data-cd-y="2026" data-cd-m="8" data-cd-d="18"', self.html)
        self.assertNotIn("2026-08-24", self.html)
        piiscan.assert_clean(self.html)

    def test_countdown_is_recomputed_on_load(self):
        self.assertIn("data-cd-y]", self.html)
        for wording in ["days out", "day out", "today", "finished"]:
            self.assertIn(wording, self.html)

    def test_a_registration_without_dates_carries_no_countdown_attributes(self):
        tabs = [dict(TABS[0], event=None)]
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        # The bare name still appears in the script's selector; what must be
        # absent is the attribute on the cell.
        self.assertNotIn('data-cd-y="', html)
        self.assertIn('<div class="board-cell"><span class="board-label">Countdown', html)
        self.assertIn("no date set", html)

    def test_scoreboard_is_three_cells_with_no_change_readout(self):
        self.assertEqual(self.html.count('class="board-cell"'), 6)  # 3 per panel
        for gone in ["Change", "since last run", "first run", "no change", "+4"]:
            self.assertNotIn(gone, self.html)

    def test_today_cell_sits_between_registered_and_countdown(self):
        registered = self.html.index("Registered")
        today_label = self.html.index("Today")
        countdown = self.html.index("Countdown")
        self.assertLess(registered, today_label)
        self.assertLess(today_label, countdown)

    def test_today_cell_reads_new_signups_for_todays_date(self):
        tab = dict(TABS[0])
        tab["metrics"] = dict(tab["metrics"], timeline=[
            {"date": "2026-08-14", "new": 18, "cumulative": 23},
            {"date": "2026-08-15", "new": 6, "cumulative": 29},
        ])
        html = render.render_dashboard([tab], "now", "2026-08-15")
        self.assertIn(
            '<span class="board-label">Today</span><span class="board-value">6</span>',
            html)

    def test_today_cell_is_zero_when_nobody_signed_up_today(self):
        # TABS' timelines end before 2026-08-15, the fixture's "today".
        self.assertIn(
            '<span class="board-label">Today</span><span class="board-value">0</span>',
            self.html)

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


class TabOrderTests(unittest.TestCase):
    def test_explicit_priority_wins_over_soonest_event(self):
        # Skills course starts sooner (Aug 18 vs Aug 24) but Travel Tryout is
        # pinned to priority 0, so it must render, and tab, first regardless.
        tabs = [dict(t, priority=1) for t in TABS]
        tabs[0]["priority"] = 0  # travel-tryout
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        travel = html.index("2026 LSGBA Travel Tryout Registration")
        skills = html.index("2026 LSGBA / NSA 3 Day Pre-Tryout Skills Course")
        self.assertLess(travel, skills)

    def test_missing_priority_falls_back_to_soonest_event(self):
        tabs = [dict(t) for t in TABS]  # no priority key on either tab
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        skills = html.index("2026 LSGBA / NSA 3 Day Pre-Tryout Skills Course")
        travel = html.index("2026 LSGBA Travel Tryout Registration")
        self.assertLess(skills, travel)


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

    def test_small_counts_render_as_numbers_not_bars(self):
        # Every grade at one volunteer makes every bar identical, so the chart
        # would say nothing the number does not. skipped=0 so the standalone
        # grade card is dropped and the breakdown is the only chart on the page.
        tab = _tab_with_crosstab(0)
        tab["metrics"]["crosstabs"][0]["rows"] = [
            {"grade": "3rd Grade", "counts": {"Advanced": 1}, "total": 1},
            {"grade": "6th Grade", "counts": {"Intermediate": 1}, "total": 1},
        ]
        html = render.render_dashboard([tab], "now", "2026-08-15")
        self.assertIn('class="figure-row"', html)
        self.assertNotIn('class="bar-track"', html)

    def test_big_counts_still_render_as_bars(self):
        html = render.render_dashboard([_tab_with_crosstab(0)], "now", "2026-08-15")
        self.assertIn('class="bar-track"', html)
        self.assertNotIn('class="figure-row"', html)

    def test_grade_card_is_a_vertical_chart_at_full_width(self):
        # Grades run along the x axis, and the card spans the grid so it lines
        # up with the breakdown beneath it.
        html = render.render_dashboard([_tab_with_crosstab(9)], "now", "2026-08-15")
        self.assertIn('class="vchart"', html)
        self.assertEqual(html.count('class="vcol"'), 2)
        self.assertIn('<section class="card wide"><h3>By grade</h3>', html)

    def test_axis_labels_drop_the_word_grade(self):
        html = render.render_dashboard([_tab_with_crosstab(9)], "now", "2026-08-15")
        self.assertIn('<span class="vlabel">3rd</span>', html)

    def test_crosstab_output_passes_the_pii_scan(self):
        html = render.render_dashboard([_tab_with_crosstab(3)], "now", "2026-08-15")
        piiscan.assert_clean(html)


def _comparison_tab():
    return {
        "slug": "season-comparison",
        "name": "Registration Comparison to Last Season",
        "kind": "comparison",
        "event": None,
        "priority": 0,
        "metrics": {"total": 66},
        "comparison": {
            "this_year_label": "2026-27",
            "this_year_open_label": "Aug 13",
            "this_year_days": [
                {"day": 0, "label": "Aug 13", "new": 5, "cumulative": 5},
                {"day": 1, "label": "Aug 14", "new": 61, "cumulative": 66},
            ],
            "this_year_today_day": 1,
            "this_year_total": 66,
            "last_year_label": "2025-26",
            "last_year_open_label": "Aug 11",
            "last_year_close_label": "Sep 10",
            "last_year_days": [
                {"day": 0, "label": "Aug 11", "new": 4, "cumulative": 4},
                {"day": 1, "label": "Aug 12", "new": 28, "cumulative": 32},
                {"day": 2, "label": "Aug 13", "new": 0, "cumulative": 32},
            ],
            "last_year_total": 116,
            "last_year_at_same_day": 32,
            "pace_delta": 34,
            "callout_day": 1,
            "callout_label": "Aug 24",
            "callout_count": 47,
            "callout_pct": 41,
            "callout_made_team": 41,
            "callout_made_team_pct": 87,
            "callout_made_team_by_grade": [("3rd", 10), ("4th", 6)],
            "callout_before_count": 69,
            "callout_before_pct": 59,
            "callout_before_made_team": 55,
            "callout_before_made_team_pct": 80,
            "callout_before_made_team_by_grade": [("2nd", 1), ("3rd", 10)],
            "domain_days": 2,
            "grades": ["3rd", "4th"],
            "this_year_grade_days": [
                {"day": 0, "label": "Aug 13",
                 "counts": {"3rd": 3, "4th": 2}, "total": 5},
                {"day": 1, "label": "Aug 14",
                 "counts": {"3rd": 40, "4th": 21}, "total": 61},
            ],
            "last_year_grade_days": [
                {"day": 0, "label": "Aug 11",
                 "counts": {"3rd": 1, "4th": 3}, "total": 4},
                {"day": 1, "label": "Aug 12",
                 "counts": {"3rd": 20, "4th": 8}, "total": 28},
                {"day": 2, "label": "Aug 13",
                 "counts": {"3rd": 0, "4th": 0}, "total": 0},
            ],
        },
    }


class ComparisonPanelTests(unittest.TestCase):
    def setUp(self):
        self.html = render.render_dashboard([_comparison_tab()], "now", "2026-08-14")

    def test_every_nonzero_bar_gets_a_count_label(self):
        # Fixture: last season days 0,1 are nonzero (day 2 is 0), this season
        # days 0,1 are both nonzero -- 4 labelled bars, not 5.
        self.assertEqual(self.html.count('class="cmp-bar-label'), 4)

    def test_a_zero_count_bar_gets_no_label(self):
        # last_year_days day 2 is 0 -- present as a bar, not as a "0" label.
        self.assertNotIn('cmp-bar-label-last" text-anchor="middle">0<', self.html)

    def test_renders_four_svg_charts(self):
        # Cumulative overlay, daily overlay, and one heatmap per season.
        self.assertEqual(self.html.count("<svg"), 4)

    def test_grade_breakdown_is_dropped_when_neither_season_has_grade_data(self):
        tab = _comparison_tab()
        tab["comparison"] = dict(tab["comparison"], grades=[],
                                 this_year_grade_days=[], last_year_grade_days=[])
        html = render.render_dashboard([tab], "now", "2026-08-14")
        self.assertEqual(html.count("<svg"), 2)
        self.assertNotIn("by grade", html)

    def test_renders_a_grade_row_for_each_grade_in_sorted_order(self):
        self.assertIn("3rd", self.html)
        self.assertIn("4th", self.html)
        third = self.html.index("3rd")
        fourth = self.html.index("4th")
        self.assertLess(third, fourth)

    def test_heatmap_intensity_scale_note_is_present(self):
        self.assertIn("Darker", self.html)
        self.assertIn("share the same", self.html)
        self.assertIn("scale", self.html)

    def test_every_chart_card_gets_its_own_legend(self):
        # Cumulative and daily-overlay charts each carry a legend; the
        # heatmap card uses its own per-panel labels instead.
        self.assertEqual(self.html.count('<div class="cmp-legend">'), 2)

    def test_renders_a_legend_for_both_seasons(self):
        self.assertIn("cmp-legend", self.html)
        self.assertIn("2025-26", self.html)
        self.assertIn("2026-27", self.html)

    def test_renders_the_after_cutoff_callout_inside_the_chart(self):
        # The callout is drawn as SVG text inside the highlighted band, not a
        # separate note paragraph above the chart.
        self.assertIn("47 registrations", self.html)
        self.assertIn("after Aug 24", self.html)
        self.assertIn("41%", self.html)
        self.assertNotIn('class="cmp-note">47', self.html)
        self.assertIn("Aug 24", self.html)

    def test_renders_the_made_team_callout_with_grade_breakdown(self):
        self.assertIn("41 made a travel team", self.html)
        self.assertIn("87%", self.html)
        self.assertIn('class="cmp-callout-grade" text-anchor="start">3rd<', self.html)
        self.assertIn('class="cmp-callout-grade-n" text-anchor="end">10<', self.html)

    def test_renders_the_before_cutoff_callout_too(self):
        self.assertIn("69 registrations", self.html)
        self.assertIn("through Aug 24", self.html)
        self.assertIn("59%", self.html)
        self.assertIn("55 made a travel team", self.html)
        self.assertIn("80%", self.html)
        self.assertIn('class="cmp-callout-grade" text-anchor="start">2nd<', self.html)

    def test_grade_breakdown_renders_as_a_row_per_grade(self):
        # A proper list -- each grade on its own line, not joined into a
        # paragraph -- with the count right-aligned like a table column.
        tab = _comparison_tab()
        tab["comparison"]["callout_made_team_by_grade"] = [
            ("3rd", 10), ("4th", 6), ("5th", 8), ("6th", 5), ("7th", 8), ("8th", 4)]
        html = render.render_dashboard([tab], "now", "2026-08-14")
        self.assertIn('class="cmp-callout-grade" text-anchor="start">3rd<', html)
        self.assertIn('class="cmp-callout-grade-n" text-anchor="end">10<', html)
        self.assertIn('class="cmp-callout-grade" text-anchor="start">8th<', html)
        self.assertIn('class="cmp-callout-grade-n" text-anchor="end">4<', html)
        self.assertNotIn("3rd 10 &middot;", html)

    def test_scoreboard_is_four_cells(self):
        self.assertEqual(self.html.count('class="board-cell"'), 4)

    def test_pace_delta_is_signed(self):
        self.assertIn(">+34<", self.html)

    def test_dispatches_by_kind_not_by_slug_or_name(self):
        # A registration tab happens to share no special name here; only the
        # explicit "kind" field should route to the comparison renderer.
        self.assertNotIn("Registered</span>", self.html)

    def test_output_passes_the_pii_scan(self):
        piiscan.assert_clean(self.html)

    def test_no_iso_date_leaks_into_the_page(self):
        self.assertNotRegex(self.html, r"\d{4}-\d{2}-\d{2}")

    def test_mixes_cleanly_with_an_ordinary_registration_tab(self):
        html = render.render_dashboard([TABS[0], _comparison_tab()], "now", "2026-08-14")
        self.assertEqual(html.count('class="tab-panel'), 2)
        self.assertIn("Registered</span>", html)  # the registration tab's board
        self.assertIn("cmp-legend", html)  # the comparison tab's board
        piiscan.assert_clean(html)


if __name__ == "__main__":
    unittest.main()
