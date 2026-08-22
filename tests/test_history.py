import unittest

from scripts import history


class HistoryIntegrityTests(unittest.TestCase):
    def test_days_are_contiguous_from_zero(self):
        self.assertEqual([point["day"] for point in history.TIMELINE],
                         list(range(len(history.TIMELINE))))

    def test_cumulative_is_a_running_sum_of_new(self):
        running = 0
        for point in history.TIMELINE:
            running += point["new"]
            self.assertEqual(point["cumulative"], running)

    def test_final_cumulative_matches_total(self):
        self.assertEqual(history.TIMELINE[-1]["cumulative"], history.TOTAL)

    def test_open_and_close_labels_match_the_first_and_last_day(self):
        self.assertEqual(history.TIMELINE[0]["label"], history.OPEN_LABEL)
        self.assertEqual(history.TIMELINE[-1]["label"], history.CLOSE_LABEL)

    def test_cutoff_day_points_at_the_cutoff_label(self):
        cutoff_point = history.TIMELINE[history.CUTOFF_DAY]
        self.assertEqual(cutoff_point["label"], history.CUTOFF_LABEL)

    def test_no_iso_dates_anywhere_in_the_frozen_data(self):
        # Only day-offsets and short "Mon D" labels belong here -- an ISO date
        # would eventually reach render.py and trip the PII scanner.
        for point in history.TIMELINE:
            self.assertNotRegex(point["label"], r"\d{4}-\d{2}-\d{2}")


class GradeTimelineIntegrityTests(unittest.TestCase):
    def test_every_day_offset_is_valid_and_unique(self):
        days = [point["day"] for point in history.GRADE_TIMELINE]
        self.assertEqual(len(days), len(set(days)))
        self.assertTrue(all(0 <= d <= history.TIMELINE[-1]["day"] for d in days))

    def test_grade_totals_by_day_match_the_new_registrations_timeline(self):
        # GRADE_TIMELINE was backfilled from a re-export of the same 116 rows
        # (see history.py's docstring) -- every day's grade counts must sum
        # to that same day's "new" in TIMELINE, or the two files have drifted.
        new_by_day = dict((p["day"], p["new"]) for p in history.TIMELINE)
        for point in history.GRADE_TIMELINE:
            total = sum(point["counts"].values())
            self.assertEqual(total, new_by_day[point["day"]],
                             "day %d: grade counts sum to %d, TIMELINE says %d"
                             % (point["day"], total, new_by_day[point["day"]]))

    def test_grand_total_across_all_grades_matches_total(self):
        grand_total = sum(count for point in history.GRADE_TIMELINE
                          for count in point["counts"].values())
        self.assertEqual(grand_total, history.TOTAL)

    def test_grade_labels_are_short_form_not_export_verbatim(self):
        # "3rd", not "3rd Grade" -- compare.py normalizes this season's export
        # to match this short form, not the other way around.
        for point in history.GRADE_TIMELINE:
            for grade in point["counts"]:
                self.assertNotRegex(grade, r"(?i)grade")


class MadeTeamAfterCutoffIntegrityTests(unittest.TestCase):
    def test_by_grade_breakdown_sums_to_the_total(self):
        self.assertEqual(sum(history.MADE_TEAM_AFTER_CUTOFF_BY_GRADE.values()),
                         history.MADE_TEAM_AFTER_CUTOFF)

    def test_cannot_exceed_the_total_after_cutoff_registrations(self):
        # Every made-team player counted here must also be one of the
        # after-cutoff registrants CUTOFF_DAY already defines.
        after_cutoff_total = sum(point["new"] for point in history.TIMELINE
                                 if point["day"] > history.CUTOFF_DAY)
        self.assertLessEqual(history.MADE_TEAM_AFTER_CUTOFF, after_cutoff_total)

    def test_grade_labels_are_short_form(self):
        for grade in history.MADE_TEAM_AFTER_CUTOFF_BY_GRADE:
            self.assertNotRegex(grade, r"(?i)grade")


if __name__ == "__main__":
    unittest.main()
