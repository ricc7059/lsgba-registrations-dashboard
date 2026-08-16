import json
import os
import tempfile
import unittest

from scripts import state


class SlugTests(unittest.TestCase):
    def test_builds_a_url_safe_slug(self):
        self.assertEqual(
            state.slugify("2026 LSGBA / NSA 3 Day Pre-Tryout Skills Course"),
            "2026-lsgba-nsa-3-day-pre-tryout-skills-course")

    def test_collapses_runs_of_separators(self):
        self.assertEqual(state.slugify("A  --  B"), "a-b")


class LoadSaveTests(unittest.TestCase):
    def test_missing_file_gives_an_empty_shape(self):
        data = state.load(os.path.join(tempfile.mkdtemp(), "state.json"))
        self.assertEqual(data, {"lastRun": None, "registrations": {}})

    def test_round_trips(self):
        path = os.path.join(tempfile.mkdtemp(), "state.json")
        state.save(path, {"lastRun": "x", "registrations": {"1": {"lastCount": 2}}})
        with open(path) as fh:
            self.assertEqual(json.load(fh)["registrations"]["1"]["lastCount"], 2)
        self.assertEqual(state.load(path)["lastRun"], "x")


class DiffTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "lastRun": "2026-08-15T21:00:00-05:00",
            "registrations": {
                "1126331": {"name": "Tryout", "slug": "tryout", "lastCount": 19},
                "1126197": {"name": "Skills", "slug": "skills", "lastCount": 37},
            },
        }

    def test_flags_an_increase(self):
        result = state.diff(self.data, [{"id": "1126331", "name": "Tryout", "count": 23}])
        self.assertTrue(result[0]["changed"])
        self.assertEqual(result[0]["delta"], 4)

    def test_flags_a_decrease(self):
        # A cancellation must trigger a refresh, or the page goes stale.
        result = state.diff(self.data, [{"id": "1126197", "name": "Skills", "count": 36}])
        self.assertTrue(result[0]["changed"])
        self.assertEqual(result[0]["delta"], -1)

    def test_unchanged_count_is_not_flagged(self):
        result = state.diff(self.data, [{"id": "1126197", "name": "Skills", "count": 37}])
        self.assertFalse(result[0]["changed"])
        self.assertEqual(result[0]["delta"], 0)

    def test_first_sighting_is_changed_and_marked_new(self):
        result = state.diff(self.data, [{"id": "999", "name": "Fresh", "count": 5}])
        self.assertTrue(result[0]["changed"])
        self.assertTrue(result[0]["is_new"])
        self.assertIsNone(result[0]["previous"])


class RecordTests(unittest.TestCase):
    def test_records_count_slug_and_export_filename(self):
        data = {"lastRun": None, "registrations": {}}
        state.record_export(data, "1126331", "2026 LSGBA Travel Tryout Registration",
                            23, "lsgba-tryout-2026-08-15-2154.csv")
        entry = data["registrations"]["1126331"]
        self.assertEqual(entry["lastCount"], 23)
        self.assertEqual(entry["lastExport"], "lsgba-tryout-2026-08-15-2154.csv")
        self.assertEqual(entry["slug"], "2026-lsgba-travel-tryout-registration")

    def test_first_recording_has_no_previous_and_zero_delta(self):
        data = {"lastRun": None, "registrations": {}}
        state.record_export(data, "1", "Tryout", 23, "a.csv")
        entry = data["registrations"]["1"]
        self.assertIsNone(entry["previousCount"])
        self.assertEqual(entry["lastDelta"], 0)

    def test_second_recording_captures_previous_and_delta(self):
        # render.py reads previousCount and lastDelta, so record_export must set them.
        data = {"lastRun": None, "registrations": {}}
        state.record_export(data, "1", "Tryout", 23, "a.csv")
        state.record_export(data, "1", "Tryout", 27, "b.csv")
        entry = data["registrations"]["1"]
        self.assertEqual(entry["previousCount"], 23)
        self.assertEqual(entry["lastDelta"], 4)
        self.assertEqual(entry["lastCount"], 27)

    def test_a_drop_records_a_negative_delta(self):
        data = {"lastRun": None, "registrations": {}}
        state.record_export(data, "1", "Tryout", 23, "a.csv")
        state.record_export(data, "1", "Tryout", 22, "b.csv")
        self.assertEqual(data["registrations"]["1"]["lastDelta"], -1)

    def test_a_hand_shortened_slug_survives(self):
        data = {"lastRun": None, "registrations": {"1": {"slug": "travel-tryout"}}}
        state.record_export(data, "1", "2026 LSGBA Travel Tryout Registration",
                            23, "a.csv")
        self.assertEqual(data["registrations"]["1"]["slug"], "travel-tryout")

    def test_recording_stamps_last_run(self):
        data = {"lastRun": "2026-01-01T00:00:00-06:00", "registrations": {}}
        state.record_export(data, "1", "Tryout", 23, "a.csv")
        self.assertNotEqual(data["lastRun"], "2026-01-01T00:00:00-06:00")
        # ISO 8601 with an offset, e.g. 2026-08-15T21:55:00-05:00
        self.assertRegex(data["lastRun"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

    def test_touch_last_run_accepts_an_explicit_stamp(self):
        data = {"lastRun": None, "registrations": {}}
        state.touch_last_run(data, "2026-08-16T09:30:00-05:00")
        self.assertEqual(data["lastRun"], "2026-08-16T09:30:00-05:00")

    def test_recording_preserves_a_hand_edited_event_block(self):
        data = {"lastRun": None, "registrations": {
            "1126331": {"event": {"label": "Aug 24-27", "start": "2026-08-24",
                                  "end": "2026-08-27"}}}}
        state.record_export(data, "1126331", "Tryout", 23, "x.csv")
        self.assertEqual(data["registrations"]["1126331"]["event"]["label"], "Aug 24-27")


if __name__ == "__main__":
    unittest.main()
