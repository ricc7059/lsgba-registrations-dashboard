import unittest

from scripts import compare, history


class NormalizeGradeTests(unittest.TestCase):
    def test_strips_a_trailing_grade_suffix(self):
        self.assertEqual(compare._normalize_grade("3rd Grade"), "3rd")

    def test_leaves_the_short_form_unchanged(self):
        self.assertEqual(compare._normalize_grade("3rd"), "3rd")

    def test_is_case_and_space_insensitive(self):
        self.assertEqual(compare._normalize_grade("3rd   GRADE"), "3rd")

    def test_blank_normalizes_to_empty_string(self):
        self.assertEqual(compare._normalize_grade(""), "")
        self.assertEqual(compare._normalize_grade(None), "")


class BuildComparisonTests(unittest.TestCase):
    def test_none_when_this_years_registration_has_no_signups_yet(self):
        self.assertIsNone(compare.build_comparison({"timeline": []}, "2026-08-13"))

    def test_this_year_open_day_is_the_first_registration_date(self):
        metrics = {"timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}]}
        result = compare.build_comparison(metrics, "2026-08-13")
        self.assertEqual(result["this_year_open_label"], "Aug 13")
        self.assertEqual(result["this_year_days"][0]["day"], 0)

    def test_gap_days_are_zero_filled_with_cumulative_carried_flat(self):
        metrics = {"timeline": [
            {"date": "2026-08-13", "new": 5, "cumulative": 5},
            {"date": "2026-08-16", "new": 3, "cumulative": 8},
        ]}
        result = compare.build_comparison(metrics, "2026-08-16")
        days = result["this_year_days"]
        self.assertEqual([d["day"] for d in days], [0, 1, 2, 3])
        self.assertEqual([d["cumulative"] for d in days], [5, 5, 5, 8])
        self.assertEqual([d["new"] for d in days], [5, 0, 0, 3])

    def test_series_extends_through_today_even_with_no_new_signups(self):
        # Today is two days after the last registration on file -- the
        # cumulative line should hold flat through today, not stop early.
        metrics = {"timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}]}
        result = compare.build_comparison(metrics, "2026-08-15")
        self.assertEqual(result["this_year_days"][-1]["day"], 2)
        self.assertEqual(result["this_year_days"][-1]["cumulative"], 5)
        self.assertEqual(result["this_year_today_day"], 2)

    def test_pace_delta_compares_same_day_offset_not_same_calendar_date(self):
        # This year opened two days later than last year (Aug 13 vs Aug 11).
        # At this year's day 1 (Aug 14), last year's day 1 was Aug 12: 32.
        metrics = {"timeline": [
            {"date": "2026-08-13", "new": 40, "cumulative": 40},
            {"date": "2026-08-14", "new": 0, "cumulative": 40},
        ]}
        result = compare.build_comparison(metrics, "2026-08-14")
        self.assertEqual(result["this_year_today_day"], 1)
        self.assertEqual(result["last_year_at_same_day"], 32)
        self.assertEqual(result["pace_delta"], 40 - 32)

    def test_pace_lookup_past_last_years_season_length_uses_the_final_total(self):
        metrics = {"timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}]}
        far_future = "2026-10-01"  # well past last year's 31-day window
        result = compare.build_comparison(metrics, far_future)
        self.assertEqual(result["last_year_at_same_day"], history.TOTAL)

    def test_callout_counts_only_days_strictly_after_the_cutoff(self):
        metrics = {"timeline": [{"date": "2026-08-13", "new": 1, "cumulative": 1}]}
        result = compare.build_comparison(metrics, "2026-08-13")
        expected = sum(p["new"] for p in history.TIMELINE if p["day"] > history.CUTOFF_DAY)
        self.assertEqual(result["callout_count"], expected)
        self.assertEqual(result["callout_label"], history.CUTOFF_LABEL)

    def test_domain_spans_the_longer_of_the_two_seasons(self):
        metrics = {"timeline": [{"date": "2026-08-13", "new": 1, "cumulative": 1}]}
        result = compare.build_comparison(metrics, "2026-08-13")
        self.assertEqual(result["domain_days"], history.TIMELINE[-1]["day"])

    def test_grades_list_includes_last_seasons_grades_even_with_no_live_grade_data(self):
        # scripts/history.py's 2025-26 season had a 2nd grader -- that grade
        # is in the comparison even though this test's live export has no
        # grade column at all.
        metrics = {"timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}]}
        result = compare.build_comparison(metrics, "2026-08-13")
        self.assertIn("2nd", result["grades"])
        self.assertEqual(result["this_year_grade_days"][0]["counts"]["2nd"], 0)

    def test_normalizes_grade_labels_from_both_seasons_to_the_same_row(self):
        # This season's export says "3rd Grade"; last season's says "3rd" --
        # they must land in the same grade, not split into two rows.
        metrics = {
            "timeline": [{"date": "2026-08-13", "new": 1, "cumulative": 1}],
            "grade_timeline": [{"date": "2026-08-13", "counts": {"3rd Grade": 1}}],
        }
        result = compare.build_comparison(metrics, "2026-08-13")
        self.assertEqual(result["grades"].count("3rd"), 1)
        self.assertNotIn("3rd Grade", result["grades"])

    def test_every_day_carries_every_grade_including_days_with_no_data(self):
        metrics = {
            "timeline": [{"date": "2026-08-13", "new": 3, "cumulative": 3}],
            "grade_timeline": [
                {"date": "2026-08-13", "counts": {"6th Grade": 2, "3rd Grade": 1}},
            ],
        }
        result = compare.build_comparison(metrics, "2026-08-14")
        days = result["this_year_grade_days"]
        self.assertEqual(days[0]["counts"]["3rd"], 1)
        self.assertEqual(days[0]["counts"]["6th"], 2)
        self.assertEqual(days[0]["total"], 3)
        # Day 1 (Aug 14) has no rows in grade_timeline at all -- still carries
        # every grade, at zero, rather than a missing key.
        self.assertEqual(days[1]["counts"]["3rd"], 0)
        self.assertEqual(days[1]["total"], 0)
        self.assertEqual(set(days[0]["counts"]), set(result["grades"]))

    def test_last_year_grade_days_span_the_full_frozen_season(self):
        metrics = {"timeline": [{"date": "2026-08-13", "new": 1, "cumulative": 1}]}
        result = compare.build_comparison(metrics, "2026-08-13")
        last_days = result["last_year_grade_days"]
        self.assertEqual(len(last_days), len(history.TIMELINE))
        self.assertEqual(last_days[-1]["label"], history.CLOSE_LABEL)
        # Known from history.GRADE_TIMELINE day 0: {"4th": 1, "6th": 2, "8th": 1}
        self.assertEqual(last_days[0]["counts"]["4th"], 1)
        self.assertEqual(last_days[0]["counts"]["6th"], 2)
        self.assertEqual(last_days[0]["total"], 4)

    def test_no_iso_date_reaches_the_returned_dict(self):
        metrics = {"timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}]}
        result = compare.build_comparison(metrics, "2026-08-15")

        def walk(value):
            if isinstance(value, dict):
                for v in value.values():
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
            elif isinstance(value, str):
                self.assertNotRegex(value, r"\d{4}-\d{2}-\d{2}")

        walk(result)


if __name__ == "__main__":
    unittest.main()
