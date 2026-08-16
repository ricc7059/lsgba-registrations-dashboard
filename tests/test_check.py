import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

from scripts import check, state

STATE = {
    "lastRun": "2026-08-15T21:55:00-05:00",
    "registrations": {
        "1126331": {"name": "Tryout", "slug": "tryout", "lastCount": 23},
        "1126197": {"name": "Skills", "slug": "skills", "lastCount": 37},
    },
}


class ParseCountsTests(unittest.TestCase):
    def test_accepts_a_well_formed_payload(self):
        parsed = check.parse_counts('[{"id": 1126331, "name": "Tryout", "count": 23}]')
        self.assertEqual(parsed[0]["id"], "1126331")

    def test_rejects_malformed_json(self):
        with self.assertRaises(ValueError):
            check.parse_counts("[{not json}]")

    def test_rejects_a_missing_key(self):
        with self.assertRaises(ValueError):
            check.parse_counts('[{"id": "1", "name": "Tryout"}]')

    def test_rejects_a_non_numeric_count(self):
        with self.assertRaises(ValueError):
            check.parse_counts('[{"id": "1", "name": "Tryout", "count": "23"}]')


class ExitCodeTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work, True)
        self.state_path = os.path.join(self.work, "state.json")
        state.save(self.state_path, STATE)

    def run_check(self, counts, stderr=None):
        """Run check.main() with argv swapped and its report kept out of the log."""
        argv = sys.argv
        sys.argv = ["check.py", "--counts", counts, "--state", self.state_path]
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(stderr or io.StringIO()):
                return check.main()
        finally:
            sys.argv = argv

    def test_change_exits_zero(self):
        payload = json.dumps([{"id": "1126331", "name": "Tryout", "count": 25},
                              {"id": "1126197", "name": "Skills", "count": 37}])
        self.assertEqual(self.run_check(payload), check.EXIT_CHANGED)

    def test_no_change_exits_three(self):
        payload = json.dumps([{"id": "1126331", "name": "Tryout", "count": 23},
                              {"id": "1126197", "name": "Skills", "count": 37}])
        self.assertEqual(self.run_check(payload), check.EXIT_NO_CHANGE)

    def test_malformed_json_exits_two(self):
        self.assertEqual(self.run_check("{oops"), check.EXIT_ERROR)

    def test_missing_key_exits_two(self):
        self.assertEqual(self.run_check('[{"id": "1126331", "name": "Tryout"}]'),
                         check.EXIT_ERROR)

    def test_undiscovered_registration_is_warned_about(self):
        # Only one of the two known registrations was discovered: a discovery
        # miss must not look like a quiet no-op.
        payload = json.dumps([{"id": "1126331", "name": "Tryout", "count": 23}])
        captured = io.StringIO()
        code = self.run_check(payload, stderr=captured)
        self.assertEqual(code, check.EXIT_NO_CHANGE)
        self.assertIn("1126197", captured.getvalue())
        self.assertIn("not discovered", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
