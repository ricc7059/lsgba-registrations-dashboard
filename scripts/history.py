"""Frozen 2025-26 Travel Tryout registration timeline.

Aggregate counts only, derived once (via scripts/aggregate.py) from the closed
2025-26 season's SportsEngine export. That export is never committed and is
long gone from ~/Downloads; this is its already-PII-free output, kept here
because last season's registration window will never reopen, so there is no
live file to re-derive it from. No name, order, or row-level data survives --
only per-day new/cumulative/grade counts, exactly what aggregate.aggregate()
would hand back for any other registration.

The original 2025-26 export carried no grade column; GRADE_TIMELINE below was
backfilled from a later re-export that added one (same 116 rows, same dates --
verified against TIMELINE's day-by-day totals before replacing this file).
"""

import datetime

LABEL = "2025-26"
OPEN_LABEL = "Aug 11"
CLOSE_LABEL = "Sep 10"
TOTAL = 116

# A real date, not just OPEN_LABEL's display string -- compare.py needs it to
# work out how many calendar days apart the two seasons' openings are (e.g.
# this season opening Aug 13 is 2 days after this Aug 11), so the daily chart
# and heatmap can align "same calendar day" rather than "same day-of-window".
# Never rendered directly: piiscan.py reads any YYYY-MM-DD shape as a
# possible date of birth, so this stays server-side arithmetic only.
OPEN_DATE = datetime.date(2025, 8, 11)

# One entry per calendar day of the registration window, day 0 = opening day.
TIMELINE = [
    {"day": 0, "label": "Aug 11", "new": 4, "cumulative": 4},
    {"day": 1, "label": "Aug 12", "new": 28, "cumulative": 32},
    {"day": 2, "label": "Aug 13", "new": 7, "cumulative": 39},
    {"day": 3, "label": "Aug 14", "new": 5, "cumulative": 44},
    {"day": 4, "label": "Aug 15", "new": 3, "cumulative": 47},
    {"day": 5, "label": "Aug 16", "new": 1, "cumulative": 48},
    {"day": 6, "label": "Aug 17", "new": 3, "cumulative": 51},
    {"day": 7, "label": "Aug 18", "new": 6, "cumulative": 57},
    {"day": 8, "label": "Aug 19", "new": 1, "cumulative": 58},
    {"day": 9, "label": "Aug 20", "new": 3, "cumulative": 61},
    {"day": 10, "label": "Aug 21", "new": 3, "cumulative": 64},
    {"day": 11, "label": "Aug 22", "new": 0, "cumulative": 64},
    {"day": 12, "label": "Aug 23", "new": 5, "cumulative": 69},
    {"day": 13, "label": "Aug 24", "new": 0, "cumulative": 69},
    {"day": 14, "label": "Aug 25", "new": 0, "cumulative": 69},
    {"day": 15, "label": "Aug 26", "new": 2, "cumulative": 71},
    {"day": 16, "label": "Aug 27", "new": 2, "cumulative": 73},
    {"day": 17, "label": "Aug 28", "new": 1, "cumulative": 74},
    {"day": 18, "label": "Aug 29", "new": 5, "cumulative": 79},
    {"day": 19, "label": "Aug 30", "new": 4, "cumulative": 83},
    {"day": 20, "label": "Aug 31", "new": 1, "cumulative": 84},
    {"day": 21, "label": "Sep 1", "new": 3, "cumulative": 87},
    {"day": 22, "label": "Sep 2", "new": 2, "cumulative": 89},
    {"day": 23, "label": "Sep 3", "new": 2, "cumulative": 91},
    {"day": 24, "label": "Sep 4", "new": 5, "cumulative": 96},
    {"day": 25, "label": "Sep 5", "new": 4, "cumulative": 100},
    {"day": 26, "label": "Sep 6", "new": 4, "cumulative": 104},
    {"day": 27, "label": "Sep 7", "new": 3, "cumulative": 107},
    {"day": 28, "label": "Sep 8", "new": 4, "cumulative": 111},
    {"day": 29, "label": "Sep 9", "new": 3, "cumulative": 114},
    {"day": 30, "label": "Sep 10", "new": 2, "cumulative": 116},
]

# Day index for August 24, 2025 -- the "registrations after Aug 24" callout
# on the daily chart sums everything with day > CUTOFF_DAY.
CUTOFF_DAY = 13
CUTOFF_LABEL = "Aug 24"

# Grade breakdown by day-offset, only for days with at least one registration
# -- a day absent here carried zero for every grade, same convention as
# aggregate.aggregate()'s grade_timeline. Grade labels are the export's own
# short form ("3rd", not "3rd Grade"); compare.py normalizes both seasons to
# this form before matching them up. The 2025-26 export originally carried no
# grade column at all (see the module docstring history) -- re-export added
# one, so this is filled in from that re-export, same aggregate-only rule as
# everything else here.
GRADE_TIMELINE = [
    {"day": 0, "counts": {"4th": 1, "6th": 2, "8th": 1}},
    {"day": 1, "counts": {"3rd": 7, "4th": 3, "5th": 7, "6th": 4, "7th": 3, "8th": 4}},
    {"day": 2, "counts": {"4th": 1, "5th": 5, "7th": 1}},
    {"day": 3, "counts": {"3rd": 2, "4th": 2, "8th": 1}},
    {"day": 4, "counts": {"5th": 2, "8th": 1}},
    {"day": 5, "counts": {"4th": 1}},
    {"day": 6, "counts": {"5th": 1, "7th": 2}},
    {"day": 7, "counts": {"3rd": 2, "4th": 1, "5th": 2, "6th": 1}},
    {"day": 8, "counts": {"7th": 1}},
    {"day": 9, "counts": {"5th": 2, "6th": 1}},
    {"day": 10, "counts": {"3rd": 1, "5th": 1, "8th": 1}},
    {"day": 12, "counts": {"2nd": 1, "3rd": 2, "4th": 1, "5th": 1}},
    {"day": 15, "counts": {"4th": 1, "5th": 1}},
    {"day": 16, "counts": {"3rd": 1, "5th": 1}},
    {"day": 17, "counts": {"4th": 1}},
    {"day": 18, "counts": {"2nd": 1, "3rd": 3, "7th": 1}},
    {"day": 19, "counts": {"3rd": 1, "4th": 1, "5th": 1, "6th": 1}},
    {"day": 20, "counts": {"3rd": 1}},
    {"day": 21, "counts": {"3rd": 1, "4th": 2}},
    {"day": 22, "counts": {"3rd": 1, "6th": 1}},
    {"day": 23, "counts": {"3rd": 1, "7th": 1}},
    {"day": 24, "counts": {"3rd": 1, "5th": 2, "7th": 1, "8th": 1}},
    {"day": 25, "counts": {"6th": 1, "7th": 1, "8th": 2}},
    {"day": 26, "counts": {"3rd": 2, "6th": 2}},
    {"day": 27, "counts": {"5th": 1, "6th": 1, "7th": 1}},
    {"day": 28, "counts": {"4th": 1, "5th": 1, "7th": 2}},
    {"day": 29, "counts": {"5th": 1, "8th": 2}},
    {"day": 30, "counts": {"5th": 1, "7th": 1}},
]

# Of the 47 after-cutoff registrants (day > CUTOFF_DAY, see above), how many
# went on to make a travel team. One-time cross-reference: matched by
# (first name, last name) -- and cross-checked on grade, since three players
# had a birth-year/day typo in one of the two source files -- against the
# 2025 team-acceptance roster (travel_team_acceptance_2025.csv). Like every
# other export this project touches, that roster is never committed and this
# is its aggregate-only result: no name, DOB, or row-level detail survives.
# One accepted player had no name match in the registration export at all
# (a data-entry spelling difference, most likely) and is excluded here, same
# as anyone else this join can't place.
MADE_TEAM_AFTER_CUTOFF = 41
MADE_TEAM_AFTER_CUTOFF_BY_GRADE = {
    "3rd": 10, "4th": 6, "5th": 8, "6th": 5, "7th": 8, "8th": 4,
}

# The mirror stat: of the 69 registrants through CUTOFF_DAY (day <=
# CUTOFF_DAY, i.e. on or before Aug 24), how many made a travel team. Same
# one-time cross-reference, same source, same exclusion of the one accepted
# player with no name match in the registration export.
MADE_TEAM_BEFORE_CUTOFF = 55
MADE_TEAM_BEFORE_CUTOFF_BY_GRADE = {
    "2nd": 1, "3rd": 10, "4th": 9, "5th": 20, "6th": 4, "7th": 7, "8th": 4,
}
