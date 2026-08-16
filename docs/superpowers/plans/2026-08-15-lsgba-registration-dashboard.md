# LSGBA Registration Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/lsgba-registration-dashboard` skill that checks every Enabled SportsEngine registration, exports a fresh Quick Report CSV for any whose entry count moved, and rebuilds a tabbed GitHub Pages dashboard from those exports.

**Architecture:** Two halves with a clean seam. The browser half — discovery, reading counts, clicking export — is agent-driven through Chrome DevTools MCP and lives in `SKILL.md`. The data half — parsing, aggregating, rendering, PII scanning — is deterministic Python in `scripts/`, unit tested, and knows nothing about browsers. `state.json` is the only thing that crosses the seam.

**Tech Stack:** Python 3.9.6, standard library only. `unittest` for tests. Hand-rolled inline SVG for charts. No pip installs, no CDN, no chart library.

**Spec:** `docs/superpowers/specs/2026-08-15-lsgba-registration-dashboard-design.md`

## Global Constraints

- **Python 3.9.6.** No `match`, no PEP 604 `X | Y` annotations, no `dict[str, int]` builtin generics at runtime.
- **Standard library only.** No `pip install` at any point. Tests run with `python3 -m unittest discover tests`.
- **`index.html` is fully self-contained.** No external CSS, JS, fonts, or images. No `fetch`. Data is inlined.
- **Registrations are never combined.** No cross-registration totals, KPI band, or merged timeline anywhere in the output.
- **No financial data.** The skill never opens an order, payment, or discount page. `Order Status`, `Gross`, `Net`, and `Service Fee` columns are dropped at parse time.
- **PII never reaches the page.** Denylist at parse time, plus a fail-closed scan before every push.
- **Exports live in `/Users/ricci/Downloads` and are never committed.**
- Repo: `ricc7059/lsgba-registrations-dashboard`, public. Local clone: `/Users/ricci/lsgba-registrations-dashboard`.

## Known SportsEngine Behaviors

These were verified against live exports on 2026-08-15. Do not re-derive them.

| Behavior | Detail |
|---|---|
| Export link | `a#exportCsvUnsaved` on `/survey/show/<id>` |
| Download filename | `unnamed_report.csv`; collides as `unnamed_report (1).csv`, `(2)`, … |
| Pagination | The export contains **all** rows regardless of the 25-row page limit |
| Leading bytes | The literal 6 ASCII characters `﻿`, **not** a BOM. `utf-8-sig` will not remove it |
| Registration Date format | `08/12/2026, 10:38pm CDT` |
| Column shape | 9 columns; only column index 4 varies between registrations |

Column headers as of 2026-08-15:

```
First Name, Last Name, Date of Birth,
Athlete's current grade (entering Fall 2026),
<registration-specific question>,
Registration Date, Order Number, Account Email, Order Status
```

Registration-specific question is `Interested in coaching for the 2026-27 travel season?` on the tryout and `What sessions will your player be attending?` on the skills course.

## File Structure

```
lsgba-registrations-dashboard/
  .gitignore              blocks *.csv
  README.md
  state.json              counts, slugs, event dates — committed
  index.html              generated
  scripts/
    __init__.py
    parse.py              CSV -> rows, PII dropped
    aggregate.py          rows -> metrics
    state.py              load/save/diff state.json
    render.py             metrics -> HTML
    piiscan.py            fail-closed scan
    check.py              CLI: discovered counts -> diff
    record.py             CLI: record a successful export
    build.py              CLI: state -> index.html
  tests/
    __init__.py
    fixtures/
      tryout_sample.csv       synthetic, real headers
      skills_sample.csv       synthetic, real headers
      poisoned.html
    test_parse.py
    test_aggregate.py
    test_state.py
    test_render.py
    test_piiscan.py
  docs/superpowers/{specs,plans}/
```

Skill lives outside the repo at `~/.claude/skills/lsgba-registration-dashboard/SKILL.md`.

**Why three CLIs.** `check.py` runs before any export and decides whether there is work. `record.py` runs after each successful export so state only advances on success. `build.py` runs once at the end. Splitting them keeps `state.json` from advancing past a failed export.

---

### Task 1: Repo scaffolding and the PII scanner

The safety rail goes in first, before anything can generate HTML.

**Files:**
- Create: `.gitignore`, `README.md`, `scripts/__init__.py`, `tests/__init__.py`
- Create: `scripts/piiscan.py`
- Test: `tests/test_piiscan.py`, `tests/fixtures/poisoned.html`

**Interfaces:**
- Consumes: nothing
- Produces: `piiscan.scan(html: str) -> list` returning a list of `(kind, match)` tuples; `piiscan.assert_clean(html: str) -> None` raising `piiscan.PIIFound`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
*.csv
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 2: Create the package markers**

```bash
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 3: Write the poisoned fixture**

Create `tests/fixtures/poisoned.html`:

```html
<html><body>
<p>Contact parent@example.com about this</p>
<p>DOB 03/18/2015</p>
</body></html>
```

- [ ] **Step 4: Write the failing test**

Create `tests/test_piiscan.py`:

```python
import os
import unittest

from scripts import piiscan

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class ScanTests(unittest.TestCase):
    def test_clean_html_produces_no_findings(self):
        html = "<html><body><p>23 registered, 6th grade leads with 9</p></body></html>"
        self.assertEqual(piiscan.scan(html), [])

    def test_detects_email_address(self):
        findings = piiscan.scan("<p>reach me at parent@example.com</p>")
        self.assertIn("email", [kind for kind, _ in findings])

    def test_detects_date_of_birth_pattern(self):
        findings = piiscan.scan("<p>born 03/18/2015</p>")
        self.assertIn("date", [kind for kind, _ in findings])

    def test_iso_dates_are_not_flagged(self):
        # The timeline axis uses ISO dates and must not trip the scan.
        self.assertEqual(piiscan.scan("<text>2026-08-14</text>"), [])

    def test_assert_clean_raises_on_poisoned_fixture(self):
        with open(os.path.join(FIXTURES, "poisoned.html")) as fh:
            html = fh.read()
        with self.assertRaises(piiscan.PIIFound):
            piiscan.assert_clean(html)

    def test_assert_clean_passes_on_clean_html(self):
        piiscan.assert_clean("<p>37 registered</p>")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run it and watch it fail**

Run: `cd /Users/ricci/lsgba-registrations-dashboard && python3 -m unittest tests.test_piiscan -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.piiscan'`

- [ ] **Step 6: Implement the scanner**

Create `scripts/piiscan.py`:

```python
"""Fail-closed check that generated HTML carries no athlete PII."""

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# MM/DD/YYYY — the shape SportsEngine uses for Date of Birth. ISO dates
# (YYYY-MM-DD) are used by the timeline axis and are deliberately not matched.
US_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")


class PIIFound(Exception):
    """Raised when generated output contains something that must not be published."""


def scan(html):
    """Return a list of (kind, matched_text) for every suspected PII hit."""
    findings = []
    for match in EMAIL_RE.findall(html):
        findings.append(("email", match))
    for match in US_DATE_RE.findall(html):
        findings.append(("date", match))
    return findings


def assert_clean(html):
    """Raise PIIFound if the HTML contains anything resembling PII."""
    findings = scan(html)
    if findings:
        detail = ", ".join("%s:%s" % (kind, value) for kind, value in findings)
        raise PIIFound("refusing to publish, found %d item(s): %s" % (len(findings), detail))
```

- [ ] **Step 7: Run the tests**

Run: `python3 -m unittest tests.test_piiscan -v`
Expected: PASS, 6 tests

- [ ] **Step 8: Write the README**

Create `README.md`:

```markdown
# LSGBA Registrations Dashboard

Aggregate view of open LSGBA registrations, published at
https://ricc7059.github.io/lsgba-registrations-dashboard/

Rebuilt by the `/lsgba-registration-dashboard` Claude Code skill, which checks
each Enabled registration in SportsEngine and re-exports only the ones whose
entry count has moved.

**This repo is public and contains aggregate counts only.** Raw Quick Report
exports stay in `~/Downloads` and are blocked by `.gitignore`. A fail-closed
scan runs before every push.

Tests: `python3 -m unittest discover tests`
```

- [ ] **Step 9: Commit**

```bash
git add .gitignore README.md scripts tests
git commit -m "Add PII scanner and repo scaffolding"
```

---

### Task 2: CSV parser

**Files:**
- Create: `scripts/parse.py`
- Test: `tests/test_parse.py`, `tests/fixtures/tryout_sample.csv`, `tests/fixtures/skills_sample.csv`

**Interfaces:**
- Consumes: nothing
- Produces: `parse.parse_export(path) -> dict` shaped `{"columns": [str], "rows": [dict]}`, where every dict maps a surviving column name to its cell value. Also `parse.strip_leading_bom_literal(text) -> str`.

- [ ] **Step 1: Write the fixtures**

Fixtures are synthetic — real headers, invented people. Never commit a real export.

**Critical:** each fixture must begin with the six ASCII characters backslash,
`u`, `F`, `E`, `F`, `F` — *not* a real byte-order mark. Typing this by hand in
an editor is error-prone because editors and clipboards silently convert it, so
generate the files with this script instead:

```bash
python3 - <<'PY'
import io, os

os.makedirs("tests/fixtures", exist_ok=True)
PREFIX = "\\uFEFF"  # six literal characters, exactly what SportsEngine emits

tryout = PREFIX + """First Name,Last Name,Date of Birth,Athlete's current grade (entering Fall 2026),Interested in coaching for the 2026-27 travel season?,Registration Date,Order Number,Account Email,Order Status
Ada,Fake,01/02/2015,6th Grade,Head Coach,"08/13/2026, 12:47pm CDT",AAAA11111,one@example.com,Paid
Bea,Fake,02/03/2016,5th Grade,,"08/13/2026, 09:03pm CDT",BBBB22222,two@example.com,Open
Cyd,Fake,03/04/2017,4th Grade,Assistant Coach,"08/14/2026, 07:07am CDT",CCCC33333,three@example.com,Paid
Dee,Fake,04/05/2015,6th Grade,,"08/14/2026, 11:33am CDT",DDDD44444,four@example.com,Paid
"""

skills = PREFIX + """First Name,Last Name,Date of Birth,Athlete's current grade (entering Fall 2026),What sessions will your player be attending?,Registration Date,Order Number,Account Email,Order Status
Eve,Fake,05/06/2014,7th Grade,Advanced,"08/12/2026, 10:38pm CDT",EEEE55555,five@example.com,Paid
Fay,Fake,06/07/2017,4th Grade,Intermediate,"08/13/2026, 10:35am CDT",FFFF66666,six@example.com,Paid
Gia,Fake,07/08/2012,8th Grade,Advanced,"08/13/2026, 02:51pm CDT",GGGG77777,seven@example.com,Paid
"""

for name, body in (("tryout_sample.csv", tryout), ("skills_sample.csv", skills)):
    with io.open(os.path.join("tests/fixtures", name), "w", encoding="utf-8") as fh:
        fh.write(body)
print("fixtures written")
PY
```

Verify the prefix is the literal six characters, not a BOM:

```bash
head -c 6 tests/fixtures/tryout_sample.csv | xxd
```

Expected: `5c75 4645 4646` — that is `﻿` as ASCII. If you see `efbb bf`
you have written a real BOM and the fixture is wrong.

- [ ] **Step 2: Write the failing test**

Create `tests/test_parse.py`:

```python
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
```

- [ ] **Step 3: Run it and watch it fail**

Run: `python3 -m unittest tests.test_parse -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.parse'`

- [ ] **Step 4: Implement the parser**

Create `scripts/parse.py`:

```python
"""Read a SportsEngine Quick Report export, dropping PII at the door."""

import csv
import io

# Columns that must never be loaded into memory, matched case-insensitively.
# Order Status, Gross, Net and Service Fee are dropped as financial data,
# which this project deliberately does not report on.
PII_COLUMNS = {
    "first name",
    "last name",
    "date of birth",
    "order number",
    "account email",
    "order status",
    "attached",
    "gross",
    "net",
    "service fee",
}

# Six literal characters: backslash, u, F, E, F, F. NOT a byte-order mark.
# SportsEngine emits the escape sequence itself rather than the character it
# denotes, so utf-8-sig decoding does not remove it.
BOM_LITERAL = "\\uFEFF"
REAL_BOM = u"﻿"


def strip_leading_bom_literal(text):
    """Remove SportsEngine's literal backslash-uFEFF prefix, or a real BOM."""
    if text.startswith(BOM_LITERAL):
        return text[len(BOM_LITERAL):]
    if text.startswith(REAL_BOM):
        return text[len(REAL_BOM):]
    return text


def parse_export(path):
    """Parse an export into {'columns': [...], 'rows': [{...}]} with PII removed."""
    with io.open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()

    reader = csv.reader(io.StringIO(strip_leading_bom_literal(raw)))
    all_rows = list(reader)
    if not all_rows:
        return {"columns": [], "rows": []}

    header = [strip_leading_bom_literal(name).strip() for name in all_rows[0]]
    keep = [i for i, name in enumerate(header) if name.lower() not in PII_COLUMNS]
    columns = [header[i] for i in keep]

    rows = []
    for raw_row in all_rows[1:]:
        if not any(cell.strip() for cell in raw_row):
            continue
        row = {}
        for i in keep:
            row[header[i]] = raw_row[i].strip() if i < len(raw_row) else ""
        rows.append(row)

    return {"columns": columns, "rows": rows}
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest tests.test_parse -v`
Expected: PASS, 10 tests

- [ ] **Step 6: Verify against the real exports**

The real files are gitignored, so this is a one-off manual check, not a test.

```bash
python3 -c "
from scripts import parse
for p in ['/Users/ricci/Downloads/lsgba-travel-tryout-2026-08-15-2154.csv',
          '/Users/ricci/Downloads/lsgba-skills-course-2026-08-15-2155.csv']:
    r = parse.parse_export(p)
    print(p.split('/')[-1], '->', len(r['rows']), 'rows,', r['columns'])
"
```

Expected: 23 rows for the tryout, 37 for the skills course, three surviving columns each.

- [ ] **Step 7: Commit**

```bash
git add scripts/parse.py tests/test_parse.py tests/fixtures
git commit -m "Add CSV parser with PII denylist and SportsEngine BOM-literal fix"
```

---

### Task 3: Aggregator

**Files:**
- Create: `scripts/aggregate.py`
- Test: `tests/test_aggregate.py`

**Interfaces:**
- Consumes: `parse.parse_export(path) -> {"columns": [...], "rows": [...]}`
- Produces:
  - `aggregate.parse_registration_date(value) -> str` returning `YYYY-MM-DD`
  - `aggregate.grade_sort_key(label) -> tuple`
  - `aggregate.aggregate(parsed) -> dict` shaped:

```python
{
  "total": 23,
  "grades": [("3rd Grade", 3), ("4th Grade", 6), ...],
  "dimensions": [
      {"question": "Interested in coaching...?",
       "values": [("Head Coach", 1), ("Assistant Coach", 2), ("No response", 20)]}
  ],
  "timeline": [{"date": "2026-08-13", "new": 5, "cumulative": 5}, ...],
}
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_aggregate.py`:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_aggregate -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.aggregate'`

- [ ] **Step 3: Implement the aggregator**

Create `scripts/aggregate.py`:

```python
"""Turn parsed export rows into publishable counts. Counts only, never people."""

import collections
import datetime
import re

# A column with more than this many distinct answers is treated as free text
# rather than a category. Comment boxes are where identifying details get typed,
# so they are dropped rather than charted.
MAX_DIMENSION_CARDINALITY = 10

NO_RESPONSE = "No response"

GRADE_RE = re.compile(r"^\s*(\d+)")
DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})")


def parse_registration_date(value):
    """'08/12/2026, 10:38pm CDT' -> '2026-08-12'. Returns '' if unparseable."""
    match = DATE_RE.match(value or "")
    if not match:
        return ""
    month, day, year = (int(part) for part in match.groups())
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return ""


def grade_sort_key(label):
    """Sort '3rd Grade' before '10th Grade'; anything unrecognized sorts last."""
    match = GRADE_RE.match(label or "")
    if match:
        return (0, int(match.group(1)), label)
    return (1, 0, label or "")


def _is_grade_column(name):
    return "grade" in name.lower()


def _is_date_column(name):
    return "registration date" in name.lower()


def aggregate(parsed):
    """Build the metrics dict for one registration."""
    rows = parsed.get("rows", [])
    columns = parsed.get("columns", [])

    grade_column = next((c for c in columns if _is_grade_column(c)), None)
    date_column = next((c for c in columns if _is_date_column(c)), None)

    grades = []
    if grade_column:
        counter = collections.Counter(
            row.get(grade_column) or NO_RESPONSE for row in rows)
        grades = sorted(counter.items(), key=lambda pair: grade_sort_key(pair[0]))

    dimensions = []
    for column in columns:
        if column == grade_column or column == date_column:
            continue
        counter = collections.Counter(row.get(column) or NO_RESPONSE for row in rows)
        if len(counter) > MAX_DIMENSION_CARDINALITY:
            continue
        # Highest count first; ties broken alphabetically so output is stable.
        values = sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
        dimensions.append({"question": column, "values": values})

    timeline = []
    if date_column:
        per_day = collections.Counter()
        for row in rows:
            iso = parse_registration_date(row.get(date_column, ""))
            if iso:
                per_day[iso] += 1
        running = 0
        for iso in sorted(per_day):
            running += per_day[iso]
            timeline.append({"date": iso, "new": per_day[iso], "cumulative": running})

    return {
        "total": len(rows),
        "grades": grades,
        "dimensions": dimensions,
        "timeline": timeline,
    }
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest tests.test_aggregate -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Sanity check against the real exports**

```bash
python3 -c "
from scripts import parse, aggregate
r = aggregate.aggregate(parse.parse_export('/Users/ricci/Downloads/lsgba-skills-course-2026-08-15-2155.csv'))
print('total', r['total'])
print('grades', r['grades'])
print('dimensions', r['dimensions'])
"
```

Expected: total 37, and the session dimension reading Advanced 24 / Intermediate 13.

- [ ] **Step 6: Commit**

```bash
git add scripts/aggregate.py tests/test_aggregate.py
git commit -m "Add schema-agnostic aggregator"
```

---

### Task 4: State handling

**Files:**
- Create: `scripts/state.py`, `state.json`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `state.load(path) -> dict` — returns `{"lastRun": None, "registrations": {}}` when the file is absent
  - `state.save(path, data) -> None`
  - `state.diff(data, discovered) -> list` where `discovered` is `[{"id": str, "name": str, "count": int}]` and each result is `{"id", "name", "count", "previous", "delta", "is_new", "changed"}`
  - `state.record_export(data, reg_id, name, count, export_filename) -> None` mutating `data` in place
  - `state.slugify(name) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_state.py`:

```python
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

    def test_recording_preserves_a_hand_edited_event_block(self):
        data = {"lastRun": None, "registrations": {
            "1126331": {"event": {"label": "Aug 24-27", "start": "2026-08-24",
                                  "end": "2026-08-27"}}}}
        state.record_export(data, "1126331", "Tryout", 23, "x.csv")
        self.assertEqual(data["registrations"]["1126331"]["event"]["label"], "Aug 24-27")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_state -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.state'`

- [ ] **Step 3: Implement state handling**

Create `scripts/state.py`:

```python
"""Read, write, and diff the run state. Counts and dates only."""

import io
import json
import os
import re

EMPTY = {"lastRun": None, "registrations": {}}


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower())
    return slug.strip("-")


def load(path):
    if not os.path.exists(path):
        return {"lastRun": None, "registrations": {}}
    with io.open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("lastRun", None)
    data.setdefault("registrations", {})
    return data


def save(path, data):
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
        handle.write("\n")


def diff(data, discovered):
    """Compare discovered counts against state. Movement in EITHER direction counts."""
    results = []
    for item in discovered:
        entry = data.get("registrations", {}).get(item["id"])
        previous = entry.get("lastCount") if entry else None
        is_new = previous is None
        delta = 0 if is_new else item["count"] - previous
        results.append({
            "id": item["id"],
            "name": item["name"],
            "count": item["count"],
            "previous": previous,
            "delta": delta,
            "is_new": is_new,
            "changed": is_new or delta != 0,
        })
    return results


def record_export(data, reg_id, name, count, export_filename):
    """Advance state for one registration. Only called after a successful export."""
    registrations = data.setdefault("registrations", {})
    entry = registrations.setdefault(reg_id, {})
    previous = entry.get("lastCount")

    entry["name"] = name
    entry["slug"] = entry.get("slug") or slugify(name)
    entry["previousCount"] = previous
    entry["lastDelta"] = 0 if previous is None else count - previous
    entry["lastCount"] = count
    entry["lastExport"] = export_filename
    # 'event' is hand-maintained and must survive every automated write.
    entry.setdefault("event", None)
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest tests.test_state -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Seed `state.json` with today's real values**

Create `state.json`:

```json
{
  "lastRun": "2026-08-15T21:55:00-05:00",
  "registrations": {
    "1126197": {
      "event": {
        "end": "2026-08-20",
        "label": "Aug 18–20",
        "start": "2026-08-18"
      },
      "lastCount": 37,
      "lastExport": "lsgba-skills-course-2026-08-15-2155.csv",
      "name": "2026 LSGBA / NSA 3 Day Pre-Tryout Skills Course",
      "slug": "skills-course"
    },
    "1126331": {
      "event": {
        "end": "2026-08-27",
        "label": "Aug 24–27",
        "start": "2026-08-24"
      },
      "lastCount": 23,
      "lastExport": "lsgba-travel-tryout-2026-08-15-2154.csv",
      "name": "2026 LSGBA Travel Tryout Registration",
      "slug": "travel-tryout"
    }
  }
}
```

The slugs are deliberately shorter than what `slugify` would produce, because they appear in the export filenames the user sees in Downloads. `record_export` only fills a slug in when one is missing, so these hand-set values survive every future run.

Note there is no `previousCount` or `lastDelta` here. That is correct — the first build renders "First run" against each tab, and real deltas appear from the second run onward.

- [ ] **Step 6: Commit**

```bash
git add scripts/state.py tests/test_state.py state.json
git commit -m "Add state load/save/diff and seed today's counts"
```

---

### Task 5: Renderer

**Files:**
- Create: `scripts/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `aggregate.aggregate(...)` output
- Produces: `render.render_dashboard(tabs, generated_at, today) -> str`, where `tabs` is a list of
  `{"slug": str, "name": str, "metrics": dict, "event": dict or None, "delta": int, "previous": int or None}`
  and `generated_at` / `today` are strings. Also `render.days_until(start, today) -> int or None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_render.py`:

```python
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

    def test_shows_a_positive_delta_with_a_sign(self):
        self.assertIn("+4", self.html)

    def test_shows_no_change_when_delta_is_zero(self):
        self.assertIn("No change", self.html)

    def test_shows_the_countdown(self):
        self.assertIn("9 days", self.html)

    def test_renders_dimension_labels(self):
        self.assertIn("Advanced", self.html)
        self.assertIn("Intermediate", self.html)

    def test_draws_svg_charts(self):
        self.assertIn("<svg", self.html)

    def test_has_no_external_references(self):
        for forbidden in ["http://", "https://cdn", "<script src", "<link rel=\"stylesheet\""]:
            self.assertNotIn(forbidden, self.html)

    def test_escapes_html_in_labels(self):
        tabs = [dict(TABS[0], name="Tryout <script>alert(1)</script>")]
        html = render.render_dashboard(tabs, "now", "2026-08-15")
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_output_passes_the_pii_scan(self):
        piiscan.assert_clean(self.html)

    def test_handles_no_active_registrations(self):
        html = render.render_dashboard([], "now", "2026-08-15")
        self.assertIn("No active registrations", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_render -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.render'`

- [ ] **Step 3: Implement the renderer**

Create `scripts/render.py`. Palette tokens live at the top so the look can be
retuned in one place.

```python
"""Render the tabbed dashboard as one self-contained HTML document."""

import datetime

MAROON = "#7B1E2B"
MAROON_LIGHT = "#A32B3D"
GOLD = "#E0B44C"
GOLD_DIM = "#8A6E2F"
GROUND = "#14161A"
PANEL = "#1D2026"
PANEL_EDGE = "#2B3038"
TEXT = "#F2F3F5"
TEXT_DIM = "#9AA1AC"


def escape(text):
    return (str(text)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def days_until(start, today):
    if not start:
        return None
    start_date = datetime.date(*[int(p) for p in start.split("-")])
    today_date = datetime.date(*[int(p) for p in today.split("-")])
    return (start_date - today_date).days


def _countdown_text(event, today):
    if not event or not event.get("start"):
        return ""
    days = days_until(event["start"], today)
    if days is None:
        return ""
    if days > 1:
        return "%s &middot; %d days out" % (escape(event.get("label", "")), days)
    if days == 1:
        return "%s &middot; tomorrow" % escape(event.get("label", ""))
    if days == 0:
        return "%s &middot; today" % escape(event.get("label", ""))
    return "%s &middot; finished" % escape(event.get("label", ""))


def _delta_text(tab):
    if tab.get("previous") is None:
        return "First run"
    delta = tab.get("delta", 0)
    if delta > 0:
        return "+%d since last run" % delta
    if delta < 0:
        return "%d since last run" % delta
    return "No change since last run"


def _bar_chart(pairs):
    """Horizontal bars as a plain HTML grid — crisper than SVG at small sizes."""
    if not pairs:
        return '<p class="empty">No responses yet.</p>'
    top = max(count for _, count in pairs) or 1
    rows = []
    for label, count in pairs:
        width = max(2.0, 100.0 * count / top)
        rows.append(
            '<div class="bar-row">'
            '<span class="bar-label">%s</span>'
            '<span class="bar-track"><span class="bar-fill" style="width:%.1f%%"></span></span>'
            '<span class="bar-value">%d</span>'
            '</div>' % (escape(label), width, count))
    return '<div class="bars">%s</div>' % "".join(rows)


def _timeline_chart(points):
    """Cumulative line with per-day bars behind it, drawn as inline SVG."""
    if not points:
        return '<p class="empty">No signups yet.</p>'

    width, height, pad = 620, 200, 28
    inner_w = width - pad * 2
    inner_h = height - pad * 2
    peak = max(point["cumulative"] for point in points) or 1
    daily_peak = max(point["new"] for point in points) or 1
    step = inner_w / float(max(1, len(points) - 1)) if len(points) > 1 else 0.0

    bars = []
    for index, point in enumerate(points):
        x = pad + step * index if len(points) > 1 else pad + inner_w / 2.0
        bar_h = inner_h * (point["new"] / float(daily_peak)) * 0.55
        bar_w = max(6.0, min(26.0, step * 0.5)) if len(points) > 1 else 26.0
        bars.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s" opacity="0.45"/>'
            % (x - bar_w / 2.0, pad + inner_h - bar_h, bar_w, bar_h, GOLD_DIM))

    coords = []
    for index, point in enumerate(points):
        x = pad + step * index if len(points) > 1 else pad + inner_w / 2.0
        y = pad + inner_h - inner_h * (point["cumulative"] / float(peak))
        coords.append((x, y))

    line = " ".join("%.1f,%.1f" % point for point in coords)
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x, y, GOLD)
                   for x, y in coords)
    labels = "".join(
        '<text x="%.1f" y="%d" class="axis" text-anchor="middle">%s</text>'
        % (coords[i][0], height - 8, points[i]["date"][5:].replace("-", "/"))
        for i in range(len(points)))

    return (
        '<svg viewBox="0 0 %d %d" class="timeline" role="img" '
        'aria-label="Cumulative signups over time">'
        '%s<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5" '
        'stroke-linejoin="round" stroke-linecap="round"/>%s%s'
        '<text x="%d" y="%d" class="axis">%d total</text></svg>'
        % (width, height, "".join(bars), line, GOLD, dots, labels,
           pad, pad - 10, peak))


def _panel(tab, today, is_first):
    metrics = tab["metrics"]
    dimension_blocks = []
    for dimension in metrics.get("dimensions", []):
        dimension_blocks.append(
            '<section class="block"><h3>%s</h3>%s</section>'
            % (escape(dimension["question"]), _bar_chart(dimension["values"])))

    return (
        '<div class="tab-panel%s" id="panel-%s" role="tabpanel">'
        '  <div class="headline">'
        '    <div class="figure"><span class="figure-number">%d</span>'
        '         <span class="figure-caption">Registered</span></div>'
        '    <div class="meta"><p class="countdown">%s</p><p class="delta">%s</p></div>'
        '  </div>'
        '  <section class="block"><h3>By grade</h3>%s</section>'
        '  %s'
        '  <section class="block"><h3>Signups over time</h3>%s</section>'
        '</div>'
        % (" is-active" if is_first else "", escape(tab["slug"]),
           metrics.get("total", 0), _countdown_text(tab.get("event"), today),
           _delta_text(tab), _bar_chart(metrics.get("grades", [])),
           "".join(dimension_blocks), _timeline_chart(metrics.get("timeline", []))))


STYLE = """
:root{--maroon:%s;--maroon-light:%s;--gold:%s;--gold-dim:%s;--ground:%s;
--panel:%s;--edge:%s;--text:%s;--dim:%s}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--text);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
-webkit-font-smoothing:antialiased}
header{background:linear-gradient(135deg,var(--maroon),var(--maroon-light));
padding:22px 20px;border-bottom:3px solid var(--gold)}
header h1{margin:0;font-size:1.15rem;letter-spacing:.16em;text-transform:uppercase;
font-weight:800}
header p{margin:6px 0 0;color:rgba(255,255,255,.82);font-size:.8rem}
.wrap{max-width:960px;margin:0 auto;padding:0 16px 56px}
.tabs{display:flex;gap:8px;overflow-x:auto;padding:16px 0;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab-button{flex:0 0 auto;background:var(--panel);color:var(--dim);border:1px solid var(--edge);
border-radius:999px;padding:10px 18px;font-size:.82rem;font-weight:700;cursor:pointer;
letter-spacing:.04em;white-space:nowrap}
.tab-button.is-active{background:var(--maroon);color:#fff;border-color:var(--gold)}
.tab-panel{display:none}
.tab-panel.is-active{display:block}
.headline{display:flex;flex-wrap:wrap;align-items:flex-end;gap:20px;
background:var(--panel);border:1px solid var(--edge);border-radius:14px;padding:22px 24px}
.figure-number{font-size:3.6rem;font-weight:800;color:var(--gold);line-height:1;
letter-spacing:-.02em;display:block}
.figure-caption{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--dim)}
.meta{margin-left:auto;text-align:right}
.countdown{margin:0;font-size:.95rem;font-weight:700}
.delta{margin:4px 0 0;font-size:.82rem;color:var(--gold)}
.block{background:var(--panel);border:1px solid var(--edge);border-radius:14px;
padding:20px 24px;margin-top:16px}
.block h3{margin:0 0 16px;font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;
color:var(--dim);font-weight:700}
.bar-row{display:grid;grid-template-columns:minmax(96px,34%%) 1fr 42px;align-items:center;
gap:12px;margin-bottom:10px}
.bar-label{font-size:.86rem;color:var(--text)}
.bar-track{background:#000;border-radius:5px;height:14px;overflow:hidden}
.bar-fill{display:block;height:100%%;border-radius:5px;
background:linear-gradient(90deg,var(--gold-dim),var(--gold))}
.bar-value{font-size:.9rem;font-weight:700;text-align:right;color:var(--gold)}
.timeline{width:100%%;height:auto}
.axis{fill:var(--dim);font-size:11px}
.empty{color:var(--dim);font-size:.86rem;margin:0}
footer{color:var(--dim);font-size:.72rem;text-align:center;padding:8px 16px 32px}
@media(max-width:560px){
.figure-number{font-size:2.8rem}
.meta{margin-left:0;text-align:left;width:100%%}
.bar-row{grid-template-columns:minmax(76px,42%%) 1fr 34px}}
""" % (MAROON, MAROON_LIGHT, GOLD, GOLD_DIM, GROUND, PANEL, PANEL_EDGE, TEXT, TEXT_DIM)

SCRIPT = """
document.querySelectorAll('.tab-button').forEach(function(button){
  button.addEventListener('click', function(){
    document.querySelectorAll('.tab-button').forEach(function(other){
      other.classList.remove('is-active');
      other.setAttribute('aria-selected','false');
    });
    document.querySelectorAll('.tab-panel').forEach(function(panel){
      panel.classList.remove('is-active');
    });
    button.classList.add('is-active');
    button.setAttribute('aria-selected','true');
    document.getElementById('panel-' + button.dataset.slug).classList.add('is-active');
  });
});
"""


def render_dashboard(tabs, generated_at, today):
    if tabs:
        buttons = "".join(
            '<button class="tab-button%s" data-slug="%s" role="tab" aria-selected="%s">%s</button>'
            % (" is-active" if i == 0 else "", escape(tab["slug"]),
               "true" if i == 0 else "false", escape(tab["name"]))
            for i, tab in enumerate(tabs))
        panels = "".join(_panel(tab, today, i == 0) for i, tab in enumerate(tabs))
        body = ('<nav class="tabs" role="tablist">%s</nav>%s' % (buttons, panels))
    else:
        body = '<div class="block"><p class="empty">No active registrations.</p></div>'

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        "<title>LSGBA Registrations</title><style>%s</style></head><body>"
        "<header><h1>LSGBA Registrations</h1><p>Updated %s</p></header>"
        '<div class="wrap">%s</div>'
        "<footer>Aggregate counts only. Rebuilt on demand from SportsEngine.</footer>"
        "<script>%s</script></body></html>\n"
        % (STYLE, escape(generated_at), body, SCRIPT))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest tests.test_render -v`
Expected: PASS, 18 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/render.py tests/test_render.py
git commit -m "Add tabbed dark maroon and gold renderer"
```

---

### Task 6: The three CLIs

**Files:**
- Create: `scripts/check.py`, `scripts/record.py`, `scripts/build.py`

**Interfaces:**
- Consumes: `parse`, `aggregate`, `state`, `render`, `piiscan`
- Produces: three command-line entry points, all run from the repo root

- [ ] **Step 1: Write `scripts/check.py`**

```python
"""Decide whether any registration moved. Exit 0 if yes, 1 if nothing to do.

Usage:
  python3 scripts/check.py --counts '[{"id":"1126331","name":"Tryout","count":23}]'
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import state  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", required=True,
                        help='JSON list of {"id","name","count"}')
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    args = parser.parse_args()

    data = state.load(args.state)
    results = state.diff(data, json.loads(args.counts))
    print(json.dumps(results, indent=2))

    changed = [r for r in results if r["changed"]]
    if not changed:
        print("\nNo change since %s" % (data.get("lastRun") or "never"), file=sys.stderr)
        return 1
    print("\n%d registration(s) changed" % len(changed), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write `scripts/record.py`**

```python
"""Record one successful export into state.json.

Usage:
  python3 scripts/record.py --id 1126331 --name "2026 LSGBA Travel Tryout Registration" \
      --count 23 --export lsgba-travel-tryout-2026-08-16-0930.csv
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import state  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--export", required=True)
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    args = parser.parse_args()

    data = state.load(args.state)
    state.record_export(data, args.id, args.name, args.count, args.export)
    state.save(args.state, data)
    print("recorded %s -> %d entries, %s" % (args.id, args.count, args.export))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `scripts/build.py`**

```python
"""Build index.html from state.json and the exports it points at.

Usage:
  python3 scripts/build.py [--dry-run] [--downloads DIR]
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import aggregate, parse, piiscan, render, state  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOWNLOADS = os.path.expanduser("~/Downloads")


def build_tabs(data, downloads, active_ids=None):
    tabs = []
    registrations = data.get("registrations", {})
    ids = active_ids if active_ids is not None else sorted(registrations)
    for reg_id in ids:
        entry = registrations.get(reg_id)
        if not entry or not entry.get("lastExport"):
            continue
        path = os.path.join(downloads, entry["lastExport"])
        if not os.path.exists(path):
            print("WARNING: missing export %s, skipping %s" % (path, reg_id),
                  file=sys.stderr)
            continue
        metrics = aggregate.aggregate(parse.parse_export(path))
        if metrics["total"] != entry.get("lastCount"):
            print("WARNING: %s has %d CSV rows but state says %s"
                  % (reg_id, metrics["total"], entry.get("lastCount")), file=sys.stderr)
        tabs.append({
            "slug": entry.get("slug") or reg_id,
            "name": entry.get("name") or reg_id,
            "event": entry.get("event"),
            "delta": entry.get("lastDelta", 0),
            "previous": entry.get("previousCount"),
            "metrics": metrics,
        })
    return tabs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--downloads", default=DEFAULT_DOWNLOADS)
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    parser.add_argument("--out", default=os.path.join(REPO, "index.html"))
    args = parser.parse_args()

    data = state.load(args.state)
    now = datetime.datetime.now()
    tabs = build_tabs(data, args.downloads)
    html = render.render_dashboard(
        tabs, now.strftime("%b %-d, %Y %-I:%M %p"), now.strftime("%Y-%m-%d"))

    piiscan.assert_clean(html)  # fail closed before anything touches disk

    with open(args.out, "w") as handle:
        handle.write(html)

    print("wrote %s with %d tab(s)" % (args.out, len(tabs)))
    if args.dry_run:
        print("dry run: not committing or pushing")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full suite**

Run: `python3 -m unittest discover tests -v`
Expected: PASS, all tests

- [ ] **Step 5: Build the page for real, dry run**

```bash
python3 scripts/build.py --dry-run && open index.html
```

Expected: two tabs, tryout showing 23, skills course showing 37 with Advanced 24 / Intermediate 13. Look at it at phone width in the browser's responsive mode.

- [ ] **Step 6: Prove the PII rail actually fires**

```bash
python3 -c "
from scripts import piiscan
html = open('index.html').read().replace('</footer>', 'parent@example.com</footer>')
try:
    piiscan.assert_clean(html)
    print('FAIL: scanner did not catch the email')
except piiscan.PIIFound as exc:
    print('OK, refused:', exc)
"
```

Expected: `OK, refused: ...`

- [ ] **Step 7: Commit**

```bash
git add scripts/check.py scripts/record.py scripts/build.py index.html
git commit -m "Add check, record, and build CLIs"
```

---

### Task 7: The skill

**Files:**
- Create: `~/.claude/skills/lsgba-registration-dashboard/SKILL.md`

**Interfaces:**
- Consumes: the three CLIs from Task 6
- Produces: `/lsgba-registration-dashboard`

- [ ] **Step 1: Write the skill**

Create `~/.claude/skills/lsgba-registration-dashboard/SKILL.md`:

````markdown
---
name: lsgba-registration-dashboard
description: Use when the user wants to refresh the LSGBA registration dashboard, check whether new athletes have registered, or export the latest SportsEngine Quick Report CSVs. Checks every Enabled registration, exports only the ones whose entry count moved, and rebuilds the published GitHub Pages dashboard.
---

# LSGBA Registration Dashboard

Repo: `/Users/ricci/lsgba-registrations-dashboard`
Published: https://ricc7059.github.io/lsgba-registrations-dashboard/

Exports land in `/Users/ricci/Downloads` and are never committed.

## 1. Discover the active registrations

Navigate Chrome to `https://lsgba.sportngin.com/survey/list`.

If you land on a login page, STOP and tell the user to log into SportsEngine
in Chrome. Do not try to authenticate.

Read the **Enabled** tab only. For each row collect the registration name and
the survey ID from its `/survey/show/<id>` link.

## 2. Read each entry count

For each registration, navigate to `/survey/show/<id>` and read the
`TOTAL ENTRIES` figure from the header.

## 3. Decide whether there is work

```bash
cd /Users/ricci/lsgba-registrations-dashboard
python3 scripts/check.py --counts '[{"id":"1126331","name":"...","count":23}]'
```

Exit code 1 means nothing moved. Report "no change since \<lastRun\>" and STOP.
Do not export, rebuild, commit, or push.

Exit code 0 means at least one registration changed. Continue with only the
ones whose `changed` is `true`.

## 4. Export each changed registration

For each changed registration:

1. Navigate to `/survey/show/<id>`.
2. Click the export link:
   ```javascript
   () => { document.querySelector('#exportCsvUnsaved').click(); return 'clicked'; }
   ```
3. Poll `~/Downloads` for a new `unnamed_report*.csv` for up to 30 seconds.
4. **Rename it immediately** to `lsgba-<slug>-YYYY-MM-DD-HHMM.csv`. The download
   is always called `unnamed_report.csv` and collides as `unnamed_report (1).csv`,
   so leaving it in place makes the next export ambiguous.
5. Record it:
   ```bash
   python3 scripts/record.py --id <id> --name "<name>" --count <n> --export <filename>
   ```

If no file appears within 30 seconds, fall back to reading the report table out
of the DOM and writing the CSV yourself, paging through all results — the table
paginates at 25 rows. **Say so in your report.** A silent fallback hides a
broken export.

## 5. Rebuild and publish

```bash
python3 scripts/build.py
python3 -m unittest discover tests
git add -A && git commit -m "Refresh dashboard: <summary>" && git push
```

`build.py` runs the PII scan and refuses to write if it trips. If it raises
`PIIFound`, STOP and report which pattern matched. Do not bypass it.

Pages redeploys automatically on push, usually within a minute.

## 6. Report back

Tell the user, per registration: the new total, the delta, and whether the
fallback fired. Finish with the dashboard URL.

## Notes

- Never open an order, payment, or discount page. This skill does not report
  financials.
- A registration with no `event` block in `state.json` renders without a
  countdown. Ask the user for its dates and add them by hand.
- Use `--dry-run` on `build.py` to inspect the page without committing.
````

- [ ] **Step 2: Verify the skill is discoverable**

Run: `ls ~/.claude/skills/lsgba-registration-dashboard/SKILL.md`
Expected: the path exists. The skill appears as `/lsgba-registration-dashboard` in a new session.

- [ ] **Step 3: Commit a copy into the repo for reference**

```bash
mkdir -p skill
cp ~/.claude/skills/lsgba-registration-dashboard/SKILL.md skill/SKILL.md
git add skill/SKILL.md
git commit -m "Vendor a copy of the skill definition"
```

---

### Task 8: Publish

**Files:**
- Modify: nothing in code — this is repo creation and the first live run

- [ ] **Step 1: Confirm the working tree is clean and tests pass**

```bash
cd /Users/ricci/lsgba-registrations-dashboard
python3 -m unittest discover tests
git status --short
```

Expected: all tests pass, nothing uncommitted.

- [ ] **Step 2: Last look for anything sensitive before the repo goes public**

```bash
git ls-files | grep -i "\.csv$" && echo "STOP: a CSV is tracked" || echo "OK: no CSVs tracked"
python3 -c "
from scripts import piiscan
piiscan.assert_clean(open('index.html').read())
print('OK: index.html is clean')
"
```

Both must pass. If a CSV is tracked, remove it with `git rm --cached` and fix
`.gitignore` before continuing.

- [ ] **Step 3: Create the GitHub repo and push**

```bash
gh repo create ricc7059/lsgba-registrations-dashboard --public \
  --source=. --remote=origin --description "Aggregate view of open LSGBA registrations"
git push -u origin main
```

- [ ] **Step 4: Enable Pages from the main branch root**

```bash
gh api -X POST repos/ricc7059/lsgba-registrations-dashboard/pages \
  -f "source[branch]=main" -f "source[path]=/" || \
gh api -X PUT repos/ricc7059/lsgba-registrations-dashboard/pages \
  -f "source[branch]=main" -f "source[path]=/"
```

- [ ] **Step 5: Wait for the deploy and confirm it serves**

```bash
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    https://ricc7059.github.io/lsgba-registrations-dashboard/)
  echo "attempt $i: $code"
  [ "$code" = "200" ] && break
  sleep 15
done
```

Expected: `200`. First deploys can take a couple of minutes.

- [ ] **Step 6: Verify what is actually published**

```bash
curl -s https://ricc7059.github.io/lsgba-registrations-dashboard/ > /tmp/published.html
python3 -c "
from scripts import piiscan
piiscan.assert_clean(open('/tmp/published.html').read())
print('OK: published page carries no PII')
"
grep -c "tab-button" /tmp/published.html
```

Expected: the scan passes and two tab buttons are present.

- [ ] **Step 7: Open it and hand it over**

```bash
open https://ricc7059.github.io/lsgba-registrations-dashboard/
```

Show the user the live URL and confirm the numbers match SportsEngine: tryout
23, skills course 37 with Advanced 24 and Intermediate 13.

---

## Self-Review Notes

**Spec coverage.** Discovery, count-reading, diff, short-circuit, export,
aggregation, rebuild, and report map to Tasks 7, 7, 4, 7, 7, 3, 6, 7. Tabbed
layout and dark maroon/gold styling are Task 5. The three-layer PII rail is
Tasks 1, 2, and 6. State schema is Task 4. Error handling is spread across
Tasks 6 and 7. Testing is Task 6 Steps 4–6 and Task 8 Step 2.

**Deviation from the spec.** The spec's denylist named `Attached`, which turns
out to be a UI-only column absent from the CSV. It stays in the denylist as a
harmless guard, and `Gross`, `Net`, and `Service Fee` were added after seeing
them in the June exports.

**Defects caught during self-review and fixed inline.** (1) `build.py` read
`previousCount` and `lastDelta` from state, but `record_export` never wrote
them — every delta would have rendered as "First run" forever. `record_export`
now captures both, with tests covering the increase, decrease, and first-run
cases. (2) The fixtures and BOM tests originally carried the prefix as inline
literal text, which editors and clipboards silently convert into a real
byte-order mark — the exact bug the parser exists to handle. Fixtures are now
generated by script with a hexdump check, and the tests build the prefix from
an explicit escaped constant.

**Deferred.** `--dry-run` on `build.py` writes `index.html` rather than a temp
file, so a dry run does leave the working tree dirty. That is deliberate: the
point is to look at the real file before committing.
