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


if __name__ == "__main__":
    unittest.main()
