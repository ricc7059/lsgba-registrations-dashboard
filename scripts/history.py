"""Frozen 2025-26 Travel Tryout registration timeline.

Aggregate counts only, derived once (via scripts/aggregate.py) from the closed
2025-26 season's SportsEngine export. That export is never committed and is
long gone from ~/Downloads; this is its already-PII-free output, kept here
because last season's registration window will never reopen, so there is no
live file to re-derive it from. No name, order, or row-level data survives --
only a per-day new/cumulative count, exactly what aggregate.aggregate() would
hand back for any other registration.
"""

LABEL = "2025-26"
OPEN_LABEL = "Aug 11"
CLOSE_LABEL = "Sep 10"
TOTAL = 116

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
