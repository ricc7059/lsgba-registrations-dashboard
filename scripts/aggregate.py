"""Turn parsed export rows into publishable counts. Counts only, never people."""

import collections
import datetime
import re

# A column with more than this many distinct answers is treated as free text
# rather than a category. Comment boxes are where identifying details get typed,
# so they are dropped rather than charted.
MAX_DIMENSION_CARDINALITY = 10

# A published label longer than this is prose, not a category. Real categorical
# answers ("Advanced", "Head Coach", "6th Grade") are short; a sentence typed
# into a text box is where identifying detail shows up.
MAX_DIMENSION_VALUE_LENGTH = 40

# Below this many rows, "every value is distinct" is unremarkable, so the
# identifier test only applies from three rows up.
MIN_ROWS_FOR_IDENTIFIER_TEST = 3

NO_RESPONSE = "No response"

GRADE_RE = re.compile(r"^\s*(\d+)")
DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})")

# A column is only treated as the grade column if its values actually look like
# grades. "grade" appearing in a header is not enough: a question such as
# "What grade and school does your player attend?" would otherwise publish
# free-text answers verbatim, unbounded, at any row count.
GRADE_VALUE_RE = re.compile(
    r"^(K|Pre-K|Kindergarten|\d{1,2}(st|nd|rd|th))(\s+Grade)?$", re.IGNORECASE)


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


def is_grade_value(value):
    """True for a grade-shaped answer, or for a blank (which buckets later)."""
    text = (value or "").strip()
    if not text:
        return True
    return bool(GRADE_VALUE_RE.match(text))


def _values_look_like_grades(rows, column):
    return all(is_grade_value(row.get(column)) for row in rows)


def _is_publishable_dimension(counter, row_count):
    """Gate every generic dimension before it can reach the page.

    Cardinality alone is not enough: every registration passes through a phase
    with ten or fewer entries, and in that phase a per-row-unique column (an
    athlete name, a phone number) has ten or fewer distinct values and would
    publish verbatim.
    """
    if len(counter) > MAX_DIMENSION_CARDINALITY:
        return False
    # Every value distinct means the column identifies rows rather than
    # categorising them. A ratio test was considered and rejected: on a young
    # registration with five signups across four grades it drops legitimate
    # data, which is exactly when the board most wants to watch signups.
    if row_count >= MIN_ROWS_FOR_IDENTIFIER_TEST and len(counter) == row_count:
        return False
    if any(len(value) > MAX_DIMENSION_VALUE_LENGTH for value in counter):
        return False
    return True


# Answers whose natural order is a rank, not a volume. Anything listed here
# sorts ahead of everything else in the order given; add to this list when a
# new question has answers that should read in a set order. Everything not
# listed falls back to most-common-first.
LABEL_PRIORITY = [
    "head coach",
    "assistant coach",
]


def _value_sort_key(pair):
    label, count = pair
    try:
        rank = LABEL_PRIORITY.index((label or "").strip().lower())
    except ValueError:
        # Unranked: highest count first, ties broken alphabetically so the
        # output is stable between runs.
        return (1, 0, -count, label)
    return (0, rank, 0, "")


def _crosstab(rows, grade_column, column, ordered_values):
    """Break one already-publishable question down by grade.

    Non-responses are excluded from the breakdown and reported separately: a
    question 20 of 23 people skipped would otherwise bury the three who
    answered. Both columns have already cleared the publishability gates, so
    this introduces no new values to the page — only a second view of them.
    """
    categories = [value for value in ordered_values if value != NO_RESPONSE]
    if not categories:
        return None

    per_grade = collections.OrderedDict()
    skipped = 0
    for row in rows:
        answer = row.get(column) or NO_RESPONSE
        if answer == NO_RESPONSE:
            skipped += 1
            continue
        grade = row.get(grade_column) or NO_RESPONSE
        per_grade.setdefault(grade, collections.Counter())[answer] += 1

    table = []
    for grade in sorted(per_grade, key=grade_sort_key):
        counts = per_grade[grade]
        table.append({
            "grade": grade,
            "counts": dict(counts),
            "total": sum(counts.values()),
        })

    if not table:
        return None
    return {"question": column, "categories": categories,
            "rows": table, "skipped": skipped}


def aggregate(parsed):
    """Build the metrics dict for one registration."""
    rows = parsed.get("rows", [])
    columns = parsed.get("columns", [])

    grade_column = next((c for c in columns if _is_grade_column(c)), None)
    date_column = next((c for c in columns if _is_date_column(c)), None)

    grades = []
    if grade_column and not _values_look_like_grades(rows, grade_column):
        # The header matched but the answers are not grades, so this is some
        # other question that happens to contain the word. Drop the block
        # entirely rather than publish free text.
        grade_column = None
    if grade_column:
        counter = collections.Counter(
            row.get(grade_column) or NO_RESPONSE for row in rows)
        grades = sorted(counter.items(), key=lambda pair: grade_sort_key(pair[0]))

    dimensions = []
    crosstabs = []
    for column in columns:
        if column == grade_column or column == date_column:
            continue
        counter = collections.Counter(row.get(column) or NO_RESPONSE for row in rows)
        if not _is_publishable_dimension(counter, len(rows)):
            continue
        values = sorted(counter.items(), key=_value_sort_key)
        dimensions.append({"question": column, "values": values})
        if grade_column:
            crosstabs.append(
                _crosstab(rows, grade_column, column, [label for label, _ in values]))

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
        "crosstabs": [table for table in crosstabs if table],
        "timeline": timeline,
    }
