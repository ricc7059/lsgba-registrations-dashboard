import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

from scripts import build, state

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def state_for(exports):
    """Minimal state.json shape: {reg_id: (name, slug, export, lastCount)}."""
    registrations = {}
    for reg_id, (name, slug, export, count) in exports.items():
        registrations[reg_id] = {
            "name": name,
            "slug": slug,
            "lastExport": export,
            "lastCount": count,
            "previousCount": None,
            "lastDelta": 0,
            "event": None,
        }
    return {"lastRun": "2026-08-15T21:55:00-05:00", "registrations": registrations}


class BuildTabsTests(unittest.TestCase):
    def setUp(self):
        # build_tabs warns on stderr by design; keep it out of the test log.
        quiet = contextlib.redirect_stderr(io.StringIO())
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)
        self.downloads = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.downloads, True)
        shutil.copy(os.path.join(FIXTURES, "tryout_sample.csv"),
                    os.path.join(self.downloads, "tryout.csv"))
        shutil.copy(os.path.join(FIXTURES, "skills_sample.csv"),
                    os.path.join(self.downloads, "skills.csv"))

    def test_happy_path_renders_every_registration(self):
        data = state_for({
            "1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 4),
            "1126197": ("Skills Course", "skills-course", "skills.csv", 3),
        })
        tabs, skipped, mismatches = build.build_tabs(data, self.downloads)
        self.assertEqual([tab["slug"] for tab in tabs],
                         ["skills-course", "travel-tryout"])
        self.assertEqual(skipped, [])
        self.assertEqual(mismatches, [])
        self.assertEqual(tabs[1]["metrics"]["total"], 4)
        self.assertEqual(tabs[1]["id"], "1126331")

    def test_missing_export_file_is_reported_as_skipped(self):
        data = state_for({
            "1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 4),
            "1126197": ("Skills Course", "skills-course", "gone.csv", 3),
        })
        tabs, skipped, mismatches = build.build_tabs(data, self.downloads)
        self.assertEqual([tab["slug"] for tab in tabs], ["travel-tryout"])
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["id"], "1126197")
        self.assertEqual(skipped[0]["export"], "gone.csv")

    def test_registration_without_an_export_is_neither_rendered_nor_skipped(self):
        data = state_for({"1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 4)})
        data["registrations"]["999"] = {"name": "Never exported", "lastExport": None}
        tabs, skipped, _ = build.build_tabs(data, self.downloads)
        self.assertEqual(len(tabs), 1)
        self.assertEqual(skipped, [])

    def test_count_mismatch_is_collected_and_still_renders(self):
        data = state_for({"1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 9)})
        tabs, skipped, mismatches = build.build_tabs(data, self.downloads)
        self.assertEqual(len(tabs), 1)
        self.assertEqual(skipped, [])
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["csvCount"], 4)
        self.assertEqual(mismatches[0]["stateCount"], 9)


class MainExitCodeTests(unittest.TestCase):
    def setUp(self):
        self.downloads = tempfile.mkdtemp()
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.downloads, True)
        self.addCleanup(shutil.rmtree, self.work, True)
        shutil.copy(os.path.join(FIXTURES, "tryout_sample.csv"),
                    os.path.join(self.downloads, "tryout.csv"))
        self.state_path = os.path.join(self.work, "state.json")
        self.out_path = os.path.join(self.work, "index.html")

    def run_main(self, data):
        """Run build.main() with argv swapped and its report kept out of the log."""
        state.save(self.state_path, data)
        argv = sys.argv
        sys.argv = ["build.py", "--downloads", self.downloads,
                    "--state", self.state_path, "--out", self.out_path]
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                return build.main()
        finally:
            sys.argv = argv

    def read_page(self):
        with io.open(self.out_path, "r", encoding="utf-8") as handle:
            return handle.read()

    def test_complete_build_exits_zero(self):
        code = self.run_main(state_for(
            {"1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 4)}))
        self.assertEqual(code, 0)
        self.assertIn("Travel Tryout", self.read_page())

    def test_missing_export_exits_non_zero_but_still_writes_the_page(self):
        code = self.run_main(state_for({
            "1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 4),
            "1126197": ("Skills Course", "skills-course", "gone.csv", 3),
        }))
        self.assertEqual(code, 1)
        page = self.read_page()
        self.assertIn("Travel Tryout", page)
        self.assertNotIn("Skills Course", page)

    def test_count_mismatch_alone_does_not_fail_the_build(self):
        code = self.run_main(state_for(
            {"1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 99)}))
        self.assertEqual(code, 0)

    def test_a_travel_tryout_registration_gets_a_second_comparison_tab(self):
        code = self.run_main(state_for(
            {"1126331": ("Travel Tryout", "travel-tryout", "tryout.csv", 4)}))
        self.assertEqual(code, 0)
        page = self.read_page()
        self.assertIn("Registration Comparison to Last Season", page)

    def test_a_registration_that_is_not_travel_tryout_gets_no_comparison_tab(self):
        code = self.run_main(state_for(
            {"1126197": ("Skills Course", "skills-course", "tryout.csv", 4)}))
        self.assertEqual(code, 0)
        page = self.read_page()
        self.assertNotIn("Registration Comparison to Last Season", page)


class FindTravelTryoutTabTests(unittest.TestCase):
    def test_matches_case_insensitively_regardless_of_survey_id(self):
        # A brand-new survey id gets minted every season, so matching has to
        # go by name, not by a hardcoded id from this year's state.json.
        tabs = [{"id": "999999", "name": "2027 LSGBA Travel Tryout Registration"}]
        self.assertEqual(build.find_travel_tryout_tab(tabs)["id"], "999999")

    def test_none_when_no_registration_is_named_travel_tryout(self):
        tabs = [{"id": "1", "name": "Skills Course"}]
        self.assertIsNone(build.find_travel_tryout_tab(tabs))

    def test_none_on_an_empty_tab_list(self):
        self.assertIsNone(build.find_travel_tryout_tab([]))


class BuildComparisonTabTests(unittest.TestCase):
    def test_none_without_a_travel_tryout_tab(self):
        tabs = [{"id": "1", "name": "Skills Course", "metrics": {"timeline": []}}]
        self.assertIsNone(build.build_comparison_tab(tabs, "2026-08-15"))

    def test_none_when_the_travel_tryout_tab_has_no_signups_yet(self):
        tabs = [{"id": "1", "name": "Travel Tryout", "metrics": {"timeline": []}}]
        self.assertIsNone(build.build_comparison_tab(tabs, "2026-08-15"))

    def test_carries_the_matched_tabs_priority_and_the_comparison_payload(self):
        tabs = [{
            "id": "1126331", "name": "Travel Tryout", "priority": 0,
            "metrics": {"timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}]},
        }]
        tab = build.build_comparison_tab(tabs, "2026-08-15")
        self.assertEqual(tab["kind"], "comparison")
        self.assertEqual(tab["priority"], 0)
        self.assertEqual(tab["metrics"]["total"], 5)
        self.assertIn("comparison", tab)


if __name__ == "__main__":
    unittest.main()
