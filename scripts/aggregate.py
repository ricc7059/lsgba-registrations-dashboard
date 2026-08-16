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
