import collections
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


class GradeValueTests(unittest.TestCase):
    def test_accepts_the_real_grade_shapes(self):
        for value in ["3rd Grade", "8th Grade", "10th", "1st grade", "K",
                      "Pre-K", "Kindergarten", "", "   "]:
            self.assertTrue(aggregate.is_grade_value(value), value)

    def test_rejects_free_text(self):
        for value in ["6th grade at St. Mary's", "Ada goes to Jefferson Elementary",
                      "not sure yet", "6th Grade, Riverside Middle"]:
            self.assertFalse(aggregate.is_grade_value(value), value)


class GradeColumnGuardTests(unittest.TestCase):
    def test_a_grade_and_school_question_publishes_nothing(self):
        # "What grade and school does your player attend?" matches the header
        # rule but its answers are free text, so the block must be dropped.
        parsed = {
            "columns": ["What grade and school does your player attend?"],
            "rows": [{"What grade and school does your player attend?":
                      "%dth grade at School %d" % (i, i)} for i in range(20)],
        }
        result = aggregate.aggregate(parsed)
        self.assertEqual(result["grades"], [])
        self.assertEqual(result["dimensions"], [])

    def test_a_short_free_text_grade_column_is_still_dropped(self):
        parsed = {
            "columns": ["Grade / School"],
            "rows": [{"Grade / School": "6th, Jefferson"},
                     {"Grade / School": "6th, Jefferson"},
                     {"Grade / School": "5th, Riverside"}],
        }
        self.assertEqual(aggregate.aggregate(parsed)["grades"], [])

    def test_a_real_grade_column_with_blanks_still_publishes(self):
        parsed = {
            "columns": ["Athlete's current grade"],
            "rows": [{"Athlete's current grade": "6th Grade"},
                     {"Athlete's current grade": "6th Grade"},
                     {"Athlete's current grade": ""}],
        }
        self.assertEqual(aggregate.aggregate(parsed)["grades"],
                         [("6th Grade", 2), ("No response", 1)])


class PublishableDimensionTests(unittest.TestCase):
    def test_cardinality_cap_still_applies(self):
        counter = collections.Counter("value %d" % i for i in range(11))
        self.assertFalse(aggregate._is_publishable_dimension(counter, 40))

    def test_every_value_unique_is_treated_as_an_identifier(self):
        counter = collections.Counter(["Ada F", "Bea G", "Cy H", "Di J", "Eve K"])
        self.assertFalse(aggregate._is_publishable_dimension(counter, 5))

    def test_two_rows_two_values_is_not_an_identifier(self):
        counter = collections.Counter(["Advanced", "Intermediate"])
        self.assertTrue(aggregate._is_publishable_dimension(counter, 2))

    def test_five_signups_across_four_grades_still_publishes(self):
        # The case the rejected ratio test would have thrown away.
        counter = collections.Counter(["3rd", "4th", "5th", "6th", "6th"])
        self.assertTrue(aggregate._is_publishable_dimension(counter, 5))

    def test_long_values_are_dropped(self):
        counter = collections.Counter(["Yes", "N" + "o" * 45])
        self.assertFalse(aggregate._is_publishable_dimension(counter, 20))


class SmallRegistrationLeakTests(unittest.TestCase):
    def test_a_five_row_export_publishes_no_per_row_unique_column(self):
        columns = ["Athlete Nickname", "Team Preference"]
        names = ["Ada", "Bea", "Cy", "Di", "Eve"]
        prefs = ["Blue", "Blue", "Gold", "Gold", "Blue"]
        parsed = {"columns": columns,
                  "rows": [{"Athlete Nickname": names[i], "Team Preference": prefs[i]}
                           for i in range(5)]}
        questions = [d["question"] for d in aggregate.aggregate(parsed)["dimensions"]]
        self.assertEqual(questions, ["Team Preference"])

    def test_iso_dates_in_a_five_row_export_do_not_publish(self):
        parsed = {"columns": ["Signup Day"],
                  "rows": [{"Signup Day": "2026-08-%02d" % (10 + i)} for i in range(5)]}
        self.assertEqual(aggregate.aggregate(parsed)["dimensions"], [])


if __name__ == "__main__":
    unittest.main()
