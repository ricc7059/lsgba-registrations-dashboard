import os
import unittest

from scripts import parse

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
TRYOUT = os.path.join(FIXTURES, "tryout_sample.csv")
SKILLS = os.path.join(FIXTURES, "skills_sample.csv")


BOM_LITERAL = "\\uFEFF"   # six characters: backslash u F E F F
REAL_BOM = "﻿"       # one character: the actual byte-order mark


class BomLiteralTests(unittest.TestCase):
    def test_strips_the_literal_six_character_prefix(self):
        # SportsEngine writes the characters backslash-u-F-E-F-F, not a real BOM.
        self.assertEqual(
            parse.strip_leading_bom_literal(BOM_LITERAL + "First Name"), "First Name")

    def test_leaves_text_without_the_prefix_alone(self):
        self.assertEqual(parse.strip_leading_bom_literal("First Name"), "First Name")

    def test_strips_a_real_bom_too(self):
        self.assertEqual(
            parse.strip_leading_bom_literal(REAL_BOM + "First Name"), "First Name")


class ParseExportTests(unittest.TestCase):
    def test_first_column_name_is_not_corrupted(self):
        result = parse.parse_export(TRYOUT)
        self.assertNotIn(BOM_LITERAL + "First Name", result["columns"])
        self.assertNotIn(REAL_BOM + "First Name", result["columns"])

    def test_pii_columns_are_dropped(self):
        result = parse.parse_export(TRYOUT)
        for dropped in ["First Name", "Last Name", "Date of Birth",
                        "Order Number", "Account Email", "Order Status"]:
            self.assertNotIn(dropped, result["columns"])

    def test_surviving_columns_are_the_useful_ones(self):
        result = parse.parse_export(TRYOUT)
        self.assertEqual(result["columns"], [
            "Athlete's current grade (entering Fall 2026)",
            "Interested in coaching for the 2026-27 travel season?",
            "Registration Date",
        ])

    def test_row_count_matches_the_file(self):
        self.assertEqual(len(parse.parse_export(TRYOUT)["rows"]), 4)
        self.assertEqual(len(parse.parse_export(SKILLS)["rows"]), 3)

    def test_rows_carry_only_surviving_columns(self):
        row = parse.parse_export(TRYOUT)["rows"][0]
        self.assertEqual(row["Athlete's current grade (entering Fall 2026)"], "6th Grade")
        self.assertNotIn("Account Email", row)

    def test_no_email_survives_anywhere_in_the_parsed_rows(self):
        for path in (TRYOUT, SKILLS):
            blob = repr(parse.parse_export(path))
            self.assertNotIn("@example.com", blob)

    def test_the_variable_question_survives_on_each_registration(self):
        tryout = parse.parse_export(TRYOUT)["columns"]
        skills = parse.parse_export(SKILLS)["columns"]
        self.assertIn("Interested in coaching for the 2026-27 travel season?", tryout)
        self.assertIn("What sessions will your player be attending?", skills)


if __name__ == "__main__":
    unittest.main()
