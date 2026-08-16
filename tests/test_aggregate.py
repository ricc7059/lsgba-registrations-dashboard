import os
import unittest

from scripts import aggregate, parse

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
TRYOUT = os.path.join(FIXTURES, "tryout_sample.csv")
SKILLS = os.path.join(FIXTURES, "skills_sample.csv")


class DateTests(unittest.TestCase):
    def test_parses_sportsengine_timestamp(self):
        self.assertEqual(
            aggregate.parse_registration_date("08/12/2026, 10:38pm CDT"), "2026-08-12")

    def test_parses_morning_timestamp(self):
        self.assertEqual(
            aggregate.parse_registration_date("08/14/2026, 07:07am CDT"), "2026-08-14")

    def test_unparseable_value_returns_empty_string(self):
        self.assertEqual(aggregate.parse_registration_date("who knows"), "")


class GradeOrderTests(unittest.TestCase):
    def test_grades_sort_numerically_not_alphabetically(self):
        labels = ["6th Grade", "3rd Grade", "8th Grade", "4th Grade"]
        self.assertEqual(
            sorted(labels, key=aggregate.grade_sort_key),
            ["3rd Grade", "4th Grade", "6th Grade", "8th Grade"])

    def test_unrecognized_labels_sort_last(self):
        labels = ["Kindergarten", "5th Grade"]
        self.assertEqual(sorted(labels, key=aggregate.grade_sort_key)[0], "5th Grade")


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.tryout = aggregate.aggregate(parse.parse_export(TRYOUT))
        self.skills = aggregate.aggregate(parse.parse_export(SKILLS))

    def test_total_is_the_row_count(self):
        self.assertEqual(self.tryout["total"], 4)
        self.assertEqual(self.skills["total"], 3)

    def test_grades_are_counted_and_ordered(self):
        self.assertEqual(self.tryout["grades"],
                         [("4th Grade", 1), ("5th Grade", 1), ("6th Grade", 2)])

    def test_grade_column_is_not_repeated_as_a_dimension(self):
        questions = [d["question"] for d in self.tryout["dimensions"]]
        self.assertNotIn("Athlete's current grade (entering Fall 2026)", questions)

    def test_registration_date_is_not_a_dimension(self):
        questions = [d["question"] for d in self.tryout["dimensions"]]
        self.assertNotIn("Registration Date", questions)

    def test_variable_question_becomes_a_dimension_without_being_named(self):
        self.assertEqual([d["question"] for d in self.tryout["dimensions"]],
                         ["Interested in coaching for the 2026-27 travel season?"])
        self.assertEqual([d["question"] for d in self.skills["dimensions"]],
                         ["What sessions will your player be attending?"])

    def test_blank_answers_bucket_as_no_response(self):
        values = dict(self.tryout["dimensions"][0]["values"])
        self.assertEqual(values["No response"], 2)

    def test_dimension_values_sort_by_count_descending(self):
        counts = [count for _, count in self.skills["dimensions"][0]["values"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_high_cardinality_columns_are_ignored(self):
        parsed = {
            "columns": ["Comments"],
            "rows": [{"Comments": "note %d" % i} for i in range(12)],
        }
        self.assertEqual(aggregate.aggregate(parsed)["dimensions"], [])

    def test_timeline_is_cumulative_and_date_ordered(self):
        timeline = self.tryout["timeline"]
        self.assertEqual([point["date"] for point in timeline],
                         ["2026-08-13", "2026-08-14"])
        self.assertEqual([point["new"] for point in timeline], [2, 2])
        self.assertEqual([point["cumulative"] for point in timeline], [2, 4])

    def test_timeline_is_empty_when_there_are_no_rows(self):
        self.assertEqual(aggregate.aggregate({"columns": [], "rows": []})["timeline"], [])


if __name__ == "__main__":
    unittest.main()
