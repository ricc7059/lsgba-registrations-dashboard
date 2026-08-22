"""Overlay this season's Travel Tryout pace against last season's.

Last season is closed and frozen in scripts/history.py. This season comes
from the live registration's own metrics["timeline"] (see aggregate.py),
which build.py re-derives from the latest export every run -- so calling
build_comparison() again after a fresh export is all "this season" needs to
stay current. Nothing here is fixed at authoring time except history.py.

Every ISO date (both this season's, from the live export, and the day math
below) is converted to a day-offset + short "Mon D" label before it leaves
this module. Nothing shaped like YYYY-MM-DD reaches render.py, because
piiscan.py treats that shape as a possible date of birth and refuses to
publish the page (see render.py's _countdown_attrs for the same rule).
"""

import datetime
import re

from scripts import aggregate, history

THIS_YEAR_LABEL = "2026-27"

# The two seasons' exports spell grade differently ("3rd Grade" this season,
# "3rd" last season, per each export's own grade question) -- normalize both
# to the short form before comparing, so a heatmap row lines up across seasons
# instead of splitting into two rows that mean the same grade.
_GRADE_SUFFIX_RE = re.compile(r"\s*grade\s*$", re.IGNORECASE)


def _normalize_grade(label):
    return _GRADE_SUFFIX_RE.sub("", label or "").strip()


def _normalize_grade_points(points):
    normalized = []
    for point in points:
        counts = {}
        for grade, count in point["counts"].items():
            key = _normalize_grade(grade)
            counts[key] = counts.get(key, 0) + count
        normalized.append(dict(point, counts=counts))
    return normalized


def _parse_iso(value):
    year, month, day = (int(part) for part in value.split("-"))
    return datetime.date(year, month, day)


def _zero_fill(dated_points, start, through):
    """One entry per day from start to through inclusive, day-offset keyed.

    Cumulative carries flat across days with no registrations, so a gap in
    the export (a quiet Sunday, a day nobody signed up) does not read as a
    drop back to zero.
    """
    by_date = dict((point["date"], point["new"]) for point in dated_points)
    days = []
    running = 0
    day = 0
    current = start
    while current <= through:
        iso = current.isoformat()
        new = by_date.get(iso, 0)
        running += new
        days.append({"day": day, "label": current.strftime("%b %-d"),
                     "new": new, "cumulative": running})
        current += datetime.timedelta(days=1)
        day += 1
    return days


def _zero_fill_by_grade(dated_points, start, through, grades):
    """Same shape as _zero_fill, but one count per grade per day.

    Every day carries every grade in `grades`, at 0 where nobody in that
    grade registered that day, so a chart can stack them in a fixed order
    without a day silently missing a segment.
    """
    by_date = dict((point["date"], point["counts"]) for point in dated_points)
    days = []
    day = 0
    current = start
    while current <= through:
        counts = by_date.get(current.isoformat(), {})
        by_grade = dict((grade, counts.get(grade, 0)) for grade in grades)
        days.append({"day": day, "label": current.strftime("%b %-d"),
                     "counts": by_grade, "total": sum(by_grade.values())})
        current += datetime.timedelta(days=1)
        day += 1
    return days


def _grade_days_from_offsets(points_by_day, grades, max_day, day_labels):
    """Same shape as _zero_fill_by_grade, but for history.py's day-offset-
    keyed points rather than the live export's date-keyed ones."""
    by_day = dict((point["day"], point["counts"]) for point in points_by_day)
    days = []
    for day in range(max_day + 1):
        counts = by_day.get(day, {})
        by_grade = dict((grade, counts.get(grade, 0)) for grade in grades)
        days.append({"day": day, "label": day_labels[day]["label"],
                     "counts": by_grade, "total": sum(by_grade.values())})
    return days


def _cumulative_at(days, day_index):
    """The last known cumulative at or before day_index; 0 before the series starts."""
    value = 0
    for point in days:
        if point["day"] > day_index:
            break
        value = point["cumulative"]
    return value


def build_comparison(this_year_metrics, today_iso):
    """None if the live registration has no signups yet to compare."""
    timeline = this_year_metrics.get("timeline") or []
    if not timeline:
        return None

    open_date = _parse_iso(timeline[0]["date"])
    today = _parse_iso(today_iso)
    through = max(open_date, today)
    this_year_days = _zero_fill(timeline, open_date, through)
    today_day = (today - open_date).days
    total_to_date = this_year_days[-1]["cumulative"]

    last_year_days = history.TIMELINE
    last_year_max_day = last_year_days[-1]["day"]
    last_year_at_today = (history.TOTAL if today_day > last_year_max_day
                           else _cumulative_at(last_year_days, today_day))

    after_cutoff = sum(point["new"] for point in last_year_days
                        if point["day"] > history.CUTOFF_DAY)

    # Both seasons' grade breakdowns, on one shared, normalized grade list --
    # empty rather than missing when the live export has no grade column, so
    # callers can test truthiness without a KeyError.
    this_year_grade_points = _normalize_grade_points(
        this_year_metrics.get("grade_timeline") or [])
    last_year_grade_points = _normalize_grade_points(history.GRADE_TIMELINE)
    grades = sorted(
        set(grade for point in this_year_grade_points for grade in point["counts"])
        | set(grade for point in last_year_grade_points for grade in point["counts"]),
        key=aggregate.grade_sort_key)
    this_year_grade_days = _zero_fill_by_grade(
        this_year_grade_points, open_date, through, grades)
    last_year_grade_days = _grade_days_from_offsets(
        last_year_grade_points, grades, last_year_max_day, last_year_days)

    return {
        "this_year_label": THIS_YEAR_LABEL,
        "this_year_open_label": open_date.strftime("%b %-d"),
        "this_year_days": this_year_days,
        "this_year_today_day": today_day,
        "this_year_total": total_to_date,
        "last_year_label": history.LABEL,
        "last_year_open_label": history.OPEN_LABEL,
        "last_year_close_label": history.CLOSE_LABEL,
        "last_year_days": last_year_days,
        "last_year_total": history.TOTAL,
        "last_year_at_same_day": last_year_at_today,
        "pace_delta": total_to_date - last_year_at_today,
        "callout_day": history.CUTOFF_DAY,
        "callout_label": history.CUTOFF_LABEL,
        "callout_count": after_cutoff,
        "callout_pct": round(100.0 * after_cutoff / history.TOTAL),
        "domain_days": max(this_year_days[-1]["day"], last_year_max_day),
        "grades": grades,
        "this_year_grade_days": this_year_grade_days,
        "last_year_grade_days": last_year_grade_days,
    }
