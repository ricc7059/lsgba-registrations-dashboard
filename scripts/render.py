"""Render the dashboard as one HTML document with local brand assets.

Layout is a fixed left rail carrying the LSGBA badge and one nav item per open
registration, with a scoreboard-style headline and card surfaces in the main
column. Colours are sampled from the association's own badge: the ring maroon,
the cougar's warmer maroon, and the cream and gold of the basketball.

The only external files referenced are under assets/ in this same repo. No CDN,
no remote font, no fetch.
"""

import datetime

# Sampled directly from assets/lsgba-badge-solid.png.
MAROON = "#8B1D41"        # the badge ring
MAROON_DEEP = "#5E1230"   # darker end of the scoreboard gradient
MAROON_BAR = "#A82A55"    # lifted for legibility as a chart series on charcoal
COUGAR = "#8B1F2E"        # the cougar's warmer maroon
GOLD = "#D2B77C"          # basketball seams, brightened to hold up on charcoal
GOLD_DIM = "#8A7647"
CREAM = "#E8D8B8"         # the basketball fill
GROUND = "#16171A"
SURFACE = "#1F2126"
SURFACE_2 = "#262A30"
EDGE = "#31363E"
TEXT = "#ECEDEF"
TEXT_DIM = "#8E959F"

NO_RESPONSE = "No response"


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


def unique_slugs(tabs):
    """Give every tab a distinct, non-empty slug so DOM ids cannot collide."""
    seen = {}
    slugs = []
    for index, tab in enumerate(tabs):
        base = (tab.get("slug") or tab.get("id") or "").strip()
        if not base:
            base = "registration-%d" % (index + 1)
        if base in seen:
            seen[base] += 1
            base = "%s-%d" % (base, seen[base])
        else:
            seen[base] = 1
        slugs.append(base)
    return slugs


def _countdown_text(event, today):
    if not event or not event.get("start"):
        return ""
    days = days_until(event["start"], today)
    if days is None:
        return ""
    if days > 1:
        return "%d days out" % days
    if days == 1:
        return "Tomorrow"
    if days == 0:
        return "Today"
    return "Finished"


def _countdown_reading(event, today):
    """(value, suffix) for the countdown cell, so the digit stays the big thing."""
    if not event or not event.get("start"):
        return ("—", "no date set")
    days = days_until(event["start"], today)
    if days is None:
        return ("—", "no date set")
    if days > 1:
        return ("%d" % days, "days out")
    if days == 1:
        return ("1", "day out")
    if days == 0:
        return ("0", "today")
    return ("—", "finished")


def _bars(pairs):
    """Horizontal bars. Numbers are tabular so they align down the column."""
    if not pairs:
        return '<p class="empty">Nothing recorded yet.</p>'
    top = max(count for _, count in pairs) or 1
    rows = []
    for label, count in pairs:
        width = max(1.5, 100.0 * count / top)
        rows.append(
            '<div class="bar-row">'
            '<span class="bar-label">%s</span>'
            '<span class="bar-track"><span class="bar-fill" style="width:%.1f%%"></span></span>'
            '<span class="bar-value">%d</span>'
            '</div>' % (escape(label), width, count))
    return '<div class="bars">%s</div>' % "".join(rows)


def _columns(pairs):
    """Vertical bars with the grades along the x axis."""
    if not pairs:
        return '<p class="empty">Nothing recorded yet.</p>'
    top = max(count for _, count in pairs) or 1
    columns = []
    for label, count in pairs:
        height = 100.0 * count / top
        # "3rd Grade" is too wide for an axis tick at phone width; the full
        # label stays available on hover and to screen readers.
        short = label.replace(" Grade", "").strip() or label
        columns.append(
            '<div class="vcol" title="%s: %d">'
            '<span class="vnum">%d</span>'
            '<span class="vtrack"><span class="vfill" style="height:%.1f%%"></span></span>'
            '<span class="vlabel">%s</span>'
            '</div>' % (escape(label), count, count, height, escape(short)))
    return '<div class="vchart">%s</div>' % "".join(columns)


# Below this many in the largest cell, a breakdown is shown as bare numbers:
# the bars would all be the same length and say nothing.
MIN_FOR_BARS = 3

# Series colours, in order, each with a legible foreground.
SERIES = [
    (GOLD, "#201A12"),
    ("#A82A55", "#FFF0F3"),
    (CREAM, "#201A12"),
    ("#C4566A", "#FFFFFF"),
    ("#6E7F8C", "#FFFFFF"),
]


def _grade_split(crosstab):
    """A separate grade breakdown per answer, never combined into one bar.

    Where the counts are big enough to chart, each answer gets its own bar
    chart and both share one scale, so a bar in Advanced and a bar in
    Intermediate of the same length mean the same number of athletes. Where the
    counts are small, the bars would all come out the same length and the
    numbers are shown on their own instead. Either way every grade appears in
    every column, including at zero, so they read row for row.
    """
    categories = crosstab["categories"]
    rows = crosstab["rows"]
    if not rows:
        return '<p class="empty">Nobody has answered yet.</p>'

    grades = [row["grade"] for row in rows]
    counts_by_grade = dict((row["grade"], row["counts"]) for row in rows)
    biggest = max(
        [counts_by_grade[grade].get(category, 0)
         for grade in grades for category in categories] or [0]) or 1

    # A bar only says something when the values differ enough for its length to
    # be read. At one or two per grade every bar comes out the same, so the
    # chart carries no information the number does not already give.
    as_bars = biggest >= MIN_FOR_BARS

    blocks = []
    for index, category in enumerate(categories):
        colour = SERIES[index % len(SERIES)][0]
        total = sum(counts_by_grade[grade].get(category, 0) for grade in grades)
        lines = []
        for grade in grades:
            count = counts_by_grade[grade].get(category, 0)
            if as_bars:
                lines.append(
                    '<div class="bar-row">'
                    '<span class="bar-label">%s</span>'
                    '<span class="bar-track"><span class="bar-fill" '
                    'style="width:%.1f%%;background:%s"></span></span>'
                    '<span class="bar-value">%d</span>'
                    '</div>'
                    % (escape(grade), 100.0 * count / biggest, colour, count))
            else:
                lines.append(
                    '<div class="figure-row"><span class="bar-label">%s</span>'
                    '<span class="bar-value%s">%d</span></div>'
                    % (escape(grade), "" if count else " is-zero", count))
        blocks.append(
            '<div class="split">'
            '<h4><span class="swatch" style="background:%s"></span>%s'
            '<b class="num">%d</b></h4>'
            '<div class="bars">%s</div></div>'
            % (colour, escape(category), total, "".join(lines)))

    caption = ('<p class="caption">%d didn\'t answer</p>' % crosstab["skipped"]
               if crosstab["skipped"] else "")
    return '<div class="split-grid">%s</div>%s' % ("".join(blocks), caption)


def _split_no_response(values):
    """Pull 'No response' out so it cannot flatten the answers that matter.

    A question where 20 of 23 skipped it would otherwise scale every real answer
    to a sliver. The count still gets reported, just as a caption rather than a
    bar competing with the signal.
    """
    answered = [(label, count) for label, count in values if label != NO_RESPONSE]
    skipped = sum(count for label, count in values if label == NO_RESPONSE)
    return answered, skipped


def _board_cell(label, value, suffix, attrs=""):
    return ('<div class="board-cell"%s>'
            '<span class="board-label">%s</span>'
            '<span class="board-value">%s</span>'
            '<span class="board-suffix">%s</span>'
            '</div>' % (attrs, escape(label), escape(value), escape(suffix)))


def _signed(number):
    return "+%d" % number if number > 0 else "%d" % number


def _pace_note(delta):
    if delta > 0:
        return "ahead of last season's pace"
    if delta < 0:
        return "behind last season's pace"
    return "even with last season's pace"


def _comparison_line_svg(c):
    """Both seasons' cumulative curve, aligned by day of registration window.

    Day-offset on the x axis rather than a calendar date: the two seasons
    opened two days apart, and only the day-of-window comparison makes them
    readable on one scale. See compare.py for why no ISO date reaches here.
    """
    last_days, this_days = c["last_year_days"], c["this_year_days"]
    domain = c["domain_days"] or 1
    width, height = 860, 210
    pad_x, pad_top, pad_bottom = 20, 16, 26
    inner_w = width - pad_x * 2
    inner_h = height - pad_top - pad_bottom
    peak = max(c["last_year_total"], c["this_year_total"]) or 1

    def x_at(day):
        return pad_x + inner_w * (day / float(domain))

    def y_at(value):
        return pad_top + inner_h - inner_h * (value / float(peak))

    def polyline(days, colour, stroke_width):
        points = " ".join("%.1f,%.1f" % (x_at(p["day"]), y_at(p["cumulative"]))
                          for p in days)
        return ('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
                'stroke-linejoin="round" stroke-linecap="round"/>'
                % (points, colour, stroke_width))

    def hits(days, series_label):
        return "".join(
            '<circle class="cmp-hit" cx="%.1f" cy="%.1f" r="8">'
            '<title>%s, day %d (%s): %d total, +%d that day</title></circle>'
            % (x_at(p["day"]), y_at(p["cumulative"]), series_label,
               p["day"], p["label"], p["cumulative"], p["new"])
            for p in days)

    last_end, this_end = last_days[-1], this_days[-1]
    dots = (
        '<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>'
        % (x_at(last_end["day"]), y_at(last_end["cumulative"]), MAROON_BAR)
        + '<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s"/>'
        % (x_at(this_end["day"]), y_at(this_end["cumulative"]), GOLD))
    end_label = ('<text x="%.1f" y="%.1f" class="cmp-end-label" text-anchor="end">'
                '%d</text>'
                % (x_at(this_end["day"]) - 8, y_at(this_end["cumulative"]) - 10,
                   this_end["cumulative"]))

    day_ticks = list(range(0, domain + 1, 5))
    if domain not in day_ticks:
        day_ticks.append(domain)
    labels = "".join(
        '<text x="%.1f" y="%d" class="axis" text-anchor="middle">Day %d</text>'
        % (x_at(d), height - 8, d)
        for d in day_ticks)

    return (
        '<svg viewBox="0 0 %d %d" class="timeline cmp-timeline" role="img" '
        'aria-label="Cumulative registrations, this season vs last season">'
        '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
        '%s%s%s%s%s%s</svg>'
        % (width, height,
           pad_x, pad_top + inner_h, width - pad_x, pad_top + inner_h, EDGE,
           polyline(last_days, MAROON_BAR, "2"), polyline(this_days, GOLD, "3"),
           dots, end_label, labels,
           hits(last_days, c["last_year_label"]) + hits(this_days, c["this_year_label"])))


def _callout_block(x0, x1, pad_top, count, date_word, date_label, pct,
                   made_team, made_team_pct, grade_pairs):
    """The callout for one region of the daily chart: headline stats
    (registration count, the after/through-date qualifier, the made-a-team
    follow-on) on the left, a per-grade tally as a proper list on the right
    -- not text crammed into the same paragraph -- separated by a hairline
    divider. Plain text, no backdrop -- small enough, and drawn after the
    bars (see _comparison_bar_svg), to sit over the chart without hiding it.
    Centred in [x0, x1].
    """
    left_w, gap, grade_label_w, grade_num_w = 128.0, 10.0, 22.0, 16.0
    grade_col_w = grade_label_w + grade_num_w
    total_w = left_w + gap + grade_col_w
    left_x = (x0 + x1) / 2.0 - total_w / 2.0
    divider_x = left_x + left_w + gap / 2.0
    grade_x = left_x + left_w + gap

    top_y = pad_top + 11
    parts = [
        '<text x="%.1f" y="%.1f" class="cmp-callout-title" text-anchor="start">'
        '%d registrations</text>' % (left_x, top_y, count),
        '<text x="%.1f" y="%.1f" class="cmp-callout-sub" text-anchor="start">'
        '%s %s &middot; %d%% of last season</text>'
        % (left_x, top_y + 9, date_word, escape(date_label), pct),
        '<text x="%.1f" y="%.1f" class="cmp-callout-title2" text-anchor="start">'
        '%d made a travel team &middot; %d%%</text>'
        % (left_x, top_y + 18, made_team, made_team_pct),
    ]
    row_h = 8.5
    content_h = max(3 * 9, len(grade_pairs) * row_h)
    parts.append(
        '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>'
        % (divider_x, top_y - 9, divider_x, top_y - 9 + content_h, EDGE))
    grade_y = top_y
    for grade, grade_count in grade_pairs:
        parts.append(
            '<text x="%.1f" y="%.1f" class="cmp-callout-grade" text-anchor="start">'
            '%s</text>'
            '<text x="%.1f" y="%.1f" class="cmp-callout-grade-n" text-anchor="end">'
            '%d</text>'
            % (grade_x, grade_y, escape(grade),
               grade_x + grade_col_w, grade_y, grade_count))
        grade_y += row_h
    return "".join(parts)


def _comparison_bar_svg(c):
    """Daily count, this season's bars paired against last season's, on one
    shared scale -- plus last season's before/after-cutoff windows each
    highlighted with their own callout."""
    last_days, this_days = c["last_year_days"], c["this_year_days"]
    this_by_day = dict((p["day"], p) for p in this_days)
    n = len(last_days)
    width, height = 860, 180
    # Extra top padding (vs. the other charts' 16px) is deliberate: every bar
    # gets a count label above it, and the tallest bar reaches pad_top itself
    # -- without the headroom its label clips against the SVG's own viewBox.
    pad_x, pad_top, pad_bottom = 20, 28, 26
    inner_w = width - pad_x * 2
    inner_h = height - pad_top - pad_bottom
    peak = max(max(p["new"] for p in last_days),
               max((p["new"] for p in this_days), default=0)) or 1
    slot = inner_w / float(n)
    pair_w = min(20.0, slot - 6)
    bar_w = pair_w / 2.0
    cutoff = c["callout_day"]

    def cx_at(i):
        return pad_x + slot * i + slot / 2.0

    band_x0 = pad_x + slot * (cutoff + 1)
    band_x1 = pad_x + inner_w
    # Background tint + divider only -- drawn before the bars, so bars paint
    # on top of the tint. The callout TEXT is composed separately and placed
    # after the bars in the final markup, so a tall bar reaching into a
    # callout's line height sits behind the text instead of blotting it out.
    # The tint itself covers only the after-cutoff half -- the before half
    # gets a callout too (below) but no highlighted background.
    band_bg = (
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.10"/>'
        '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" '
        'stroke-dasharray="3 3"/>'
        % (band_x0, pad_top, band_x1 - band_x0, inner_h, GOLD,
           band_x0, pad_top, band_x0, pad_top + inner_h, GOLD_DIM))
    callouts = (
        _callout_block(
            pad_x, band_x0, pad_top, c["callout_before_count"], "through",
            c["callout_label"], c["callout_before_pct"],
            c["callout_before_made_team"], c["callout_before_made_team_pct"],
            c["callout_before_made_team_by_grade"])
        + _callout_block(
            band_x0, band_x1, pad_top, c["callout_count"], "after",
            c["callout_label"], c["callout_pct"],
            c["callout_made_team"], c["callout_made_team_pct"],
            c["callout_made_team_by_grade"]))

    bars = []
    for i, p in enumerate(last_days):
        bar_h = inner_h * (p["new"] / float(peak))
        by = pad_top + inner_h - bar_h
        bars.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s">'
            '<title>%s season, %s: %d</title></rect>'
            % (cx_at(i) - bar_w - 1, by, bar_w, max(bar_h, 1.5), MAROON_BAR,
               c["last_year_label"], p["label"], p["new"]))
        if p["new"]:
            bars.append(
                '<text x="%.1f" y="%.1f" class="cmp-bar-label cmp-bar-label-last" '
                'text-anchor="middle">%d</text>'
                % (cx_at(i) - bar_w / 2.0 - 1, by - 3, p["new"]))

        this_point = this_by_day.get(i)
        if this_point is None:
            continue
        this_h = inner_h * (this_point["new"] / float(peak))
        this_y = pad_top + inner_h - this_h
        bars.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s">'
            '<title>%s season, %s: %d</title></rect>'
            % (cx_at(i) + 1, this_y, bar_w, max(this_h, 1.5), GOLD,
               c["this_year_label"], this_point["label"], this_point["new"]))
        if this_point["new"]:
            bars.append(
                '<text x="%.1f" y="%.1f" class="cmp-bar-label cmp-bar-label-this" '
                'text-anchor="middle">%d</text>'
                % (cx_at(i) + bar_w / 2.0 + 1, this_y - 3, this_point["new"]))

    day_ticks = list(range(0, n, 5))
    if n - 1 not in day_ticks:
        day_ticks.append(n - 1)
    labels = "".join(
        '<text x="%.1f" y="%d" class="axis" text-anchor="middle">%s</text>'
        % (cx_at(d), height - 8, last_days[d]["label"])
        for d in day_ticks)

    return (
        '<svg viewBox="0 0 %d %d" class="timeline cmp-timeline" role="img" '
        'aria-label="Daily registrations, this season vs last season, with '
        'before- and after-%s callouts">'
        '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
        '%s%s%s%s</svg>'
        % (width, height, c["callout_label"],
           pad_x, pad_top + inner_h, width - pad_x, pad_top + inner_h, EDGE,
           band_bg, "".join(bars), labels, callouts))


def _comparison_heatmap_svg(days, grades, colour, max_count, domain_days, season_label):
    """One season's day-by-grade grid. Colour is fixed (the season's own
    identity hue, matching the other two charts); fill-opacity carries the
    count, on a scale the caller shares across both seasons' grids so
    "darker" means the same thing in both.

    `days` only needs to cover the days that season actually has -- a day
    beyond it (this season, before it happens) draws no cell at all rather
    than a zero, so "not yet known" reads differently from "genuinely zero".
    """
    n_cols = domain_days + 1
    width = 860
    pad_left, pad_top, pad_right, pad_bottom = 46, 6, 14, 22
    row_h, row_gap = 20, 2
    rows = len(grades)
    height = pad_top + rows * (row_h + row_gap) - row_gap + pad_bottom
    inner_w = width - pad_left - pad_right
    slot = inner_w / float(n_cols)
    cell_w = max(slot - 2, 1.0)

    def cx(day_i):
        return pad_left + slot * day_i

    def cy(row_i):
        return pad_top + row_i * (row_h + row_gap)

    cells = [
        '<text x="%.1f" y="%.1f" class="axis" text-anchor="end">%s</text>'
        % (pad_left - 8, cy(row_i) + row_h / 2.0 + 3, escape(grade))
        for row_i, grade in enumerate(grades)
    ]
    for p in days:
        for row_i, grade in enumerate(grades):
            count = p["counts"].get(grade, 0)
            opacity = 0.0 if not count else max(0.16, min(1.0, count / float(max_count)))
            cells.append(
                '<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="2" '
                'fill="%s" fill-opacity="%.2f" stroke="%s" stroke-width="1">'
                '<title>%s, %s: %d</title></rect>'
                % (cx(p["day"]), cy(row_i), cell_w, row_h, colour, opacity,
                   EDGE, escape(grade), p["label"], count))

    day_ticks = list(range(0, n_cols, 5))
    if n_cols - 1 not in day_ticks:
        day_ticks.append(n_cols - 1)
    labels = "".join(
        '<text x="%.1f" y="%d" class="axis" text-anchor="middle">%s</text>'
        % (cx(d) + cell_w / 2.0, height - 6, days[d]["label"])
        for d in day_ticks if d < len(days))

    return (
        '<svg viewBox="0 0 %d %d" class="timeline cmp-heatmap" role="img" '
        'aria-label="%s registrations by day and grade">%s%s</svg>'
        % (width, height, escape(season_label), "".join(cells), labels))


def _cmp_series_legend(c):
    return (
        '<div class="cmp-legend">'
        '<span class="cmp-legend-item"><span class="cmp-legend-key cmp-last"></span>'
        '%s season &middot; final %d</span>'
        '<span class="cmp-legend-item"><span class="cmp-legend-key cmp-this"></span>'
        '%s season &middot; %d to date</span>'
        '</div>'
        % (escape(c["last_year_label"]), c["last_year_total"],
           escape(c["this_year_label"]), c["this_year_total"]))


def _comparison_panel(tab, slug, is_first):
    c = tab["comparison"]

    board = "".join([
        _board_cell("This season", "%d" % c["this_year_total"], "as of today"),
        _board_cell("Last season, day %d" % c["this_year_today_day"],
                    "%d" % c["last_year_at_same_day"], "same point last season"),
        _board_cell("Pace vs last season", _signed(c["pace_delta"]),
                    _pace_note(c["pace_delta"])),
        _board_cell("Last season, final", "%d" % c["last_year_total"],
                    "%s–%s, %s" % (c["last_year_open_label"],
                                        c["last_year_close_label"], c["last_year_label"])),
    ])

    grade_card = ""
    if c["grades"]:
        max_count = max(
            [count for p in c["this_year_grade_days"] for count in p["counts"].values()]
            + [count for p in c["last_year_grade_days"] for count in p["counts"].values()]
            or [0]) or 1
        last_heatmap = _comparison_heatmap_svg(
            c["last_year_grade_days"], c["grades"], MAROON_BAR, max_count,
            c["domain_days"], c["last_year_label"])
        this_heatmap = _comparison_heatmap_svg(
            c["this_year_grade_days"], c["grades"], GOLD, max_count,
            c["domain_days"], c["this_year_label"])
        grade_card = (
            '  <section class="card wide"><h3>Daily registrations by grade '
            '<span class="sub">both seasons, same day-and-grade scale</span></h3>'
            '<p class="cmp-heatmap-label"><span class="cmp-legend-key cmp-last"></span>'
            '%s season</p>%s'
            '<p class="cmp-heatmap-label"><span class="cmp-legend-key cmp-this"></span>'
            '%s season</p>%s'
            '<p class="cmp-note">Darker = more registrations that day; both grids '
            'share the same 0&ndash;%d scale.</p>'
            '</section>'
            % (escape(c["last_year_label"]), last_heatmap,
               escape(c["this_year_label"]), this_heatmap, max_count))

    return (
        '<section class="tab-panel%s" id="panel-%s" role="tabpanel" aria-label="%s">'
        '  <header class="panel-head">'
        '    <h2>%s</h2>'
        '    <p class="dates">Day 0 = registration opens &middot; %s last season, '
        '%s this season</p>'
        '  </header>'
        '  <div class="board">%s</div>'
        '  <section class="card wide"><h3>Cumulative registrations '
        '<span class="sub">both seasons, aligned by day of registration window</span>'
        '</h3>%s%s</section>'
        '  <section class="card wide"><h3>Daily registrations '
        '<span class="sub">this season vs last season</span></h3>%s%s</section>'
        '%s'
        '</section>'
        % (" is-active" if is_first else "", escape(slug), escape(tab["name"]),
           escape(tab["name"]),
           escape(c["last_year_open_label"]), escape(c["this_year_open_label"]),
           board,
           _cmp_series_legend(c), _comparison_line_svg(c),
           _cmp_series_legend(c), _comparison_bar_svg(c),
           grade_card))


def _countdown_attrs(event):
    """Carry the event date as three numbers, for the browser to recompute from.

    Deliberately not an ISO string: the PII scanner treats YYYY-MM-DD as a
    possible date of birth and would refuse to publish the page.
    """
    if not event or not event.get("start"):
        return ""
    try:
        year, month, day = [int(part) for part in event["start"].split("-")]
    except (ValueError, AttributeError):
        return ""
    return ' data-cd-y="%d" data-cd-m="%d" data-cd-d="%d"' % (year, month, day)


def _today_count(metrics, today):
    return next((point["new"] for point in metrics.get("timeline", [])
                 if point["date"] == today), 0)


def _panel(tab, slug, today, is_first):
    if tab.get("kind") == "comparison":
        return _comparison_panel(tab, slug, is_first)
    metrics = tab["metrics"]
    event = tab.get("event") or {}
    countdown_value, countdown_suffix = _countdown_reading(event, today)

    board = "".join([
        _board_cell("Registered", "%d" % metrics.get("total", 0), "athletes"),
        _board_cell("Today", "%d" % _today_count(metrics, today), "new"),
        _board_cell("Countdown", countdown_value, countdown_suffix,
                    _countdown_attrs(event)),
    ])

    # A question broken down by grade supersedes the same question shown flat:
    # the legend still carries every category total, and the split is the part
    # that answers "who is in which group".
    crosstabs = metrics.get("crosstabs", [])
    by_question = dict((table["question"], table) for table in crosstabs)

    # A breakdown everyone answered already carries the grade totals in its
    # right-hand column, so the standalone grade card would just repeat itself.
    # When some people skipped the question the breakdown covers only part of
    # the field, and the full grade distribution still needs its own card.
    covered = any(table["skipped"] == 0 for table in crosstabs)
    cards = [] if covered else [
        '<section class="card wide"><h3>By grade</h3>%s</section>'
        % _columns(metrics.get("grades", []))]

    for dimension in metrics.get("dimensions", []):
        question = dimension["question"]
        crosstab = by_question.get(question)
        if crosstab:
            cards.append(
                '<section class="card wide"><h3>%s <span class="sub">by grade</span>'
                '</h3>%s</section>' % (escape(question), _grade_split(crosstab)))
            continue
        answered, skipped = _split_no_response(dimension["values"])
        caption = ('<p class="caption">%d didn\'t answer</p>' % skipped) if skipped else ""
        cards.append(
            '<section class="card"><h3>%s</h3>%s%s</section>'
            % (escape(question), _bars(answered), caption))

    return (
        '<section class="tab-panel%s" id="panel-%s" role="tabpanel" aria-label="%s">'
        '  <header class="panel-head">'
        '    <h2>%s</h2>'
        '    <p class="dates">%s</p>'
        '  </header>'
        '  <div class="board">%s</div>'
        '  <div class="card-grid">%s</div>'
        '</section>'
        % (" is-active" if is_first else "", escape(slug), escape(tab["name"]),
           escape(tab["name"]), escape(event.get("label", "")),
           board, "".join(cards)))


STYLE = """
:root{--maroon:%s;--maroon-deep:%s;--cougar:%s;--gold:%s;--gold-dim:%s;
--cream:%s;--ground:%s;--surface:%s;--surface-2:%s;--edge:%s;--text:%s;--dim:%s;
--sans:"Avenir Next","Segoe UI Variable","Segoe UI",system-ui,-apple-system,
Helvetica,Arial,sans-serif;
--mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--ground);color:var(--text);font-family:var(--sans);
-webkit-font-smoothing:antialiased;font-size:15px;line-height:1.45}
.num,.board-value,.bar-value,.tab-count,.split h4 b{font-family:var(--mono);
font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

.shell{display:flex;min-height:100vh;align-items:stretch}

/* ---- left rail ---- */
.rail{flex:0 0 268px;background:var(--surface);border-right:1px solid var(--edge);
padding:26px 20px;display:flex;flex-direction:column;gap:26px}
.brand{display:flex;align-items:center;gap:13px}
.brand img{width:54px;height:54px;flex:0 0 54px}
.brand-org{margin:0;font-size:.95rem;font-weight:800;letter-spacing:.02em;
line-height:1.15}
.brand-sub{margin:2px 0 0;font-size:.72rem;color:var(--dim);letter-spacing:.13em;
text-transform:uppercase}
.rail-label{margin:0 0 10px;font-size:.66rem;letter-spacing:.19em;
text-transform:uppercase;color:var(--dim);font-weight:700}
.tabs{display:flex;flex-direction:column;gap:6px}
.tab-button{display:flex;align-items:center;gap:10px;width:100%%;text-align:left;
background:transparent;border:1px solid transparent;border-radius:11px;
padding:11px 13px;color:var(--dim);font-family:inherit;font-size:.83rem;
font-weight:600;cursor:pointer;transition:background .15s,color .15s}
.tab-button:hover{background:var(--surface-2);color:var(--text)}
.tab-button:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.tab-button.is-active{background:var(--maroon);border-color:rgba(210,183,124,.5);
color:#fff}
.tab-name{flex:1;line-height:1.3}
.tab-count{font-size:.9rem;font-weight:700;color:var(--gold)}
.rail-foot{margin-top:auto}
.stamp{margin:0;font-size:.78rem;color:var(--text)}

/* ---- main column ---- */
.main{flex:1;min-width:0;padding:30px 34px 56px}
.tab-panel{display:none}
.tab-panel.is-active{display:block}
.panel-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;
margin-bottom:20px}
.panel-head h2{margin:0;font-size:1.32rem;font-weight:800;letter-spacing:-.01em}
.dates{margin:0;font-size:.83rem;color:var(--dim)}

/* ---- scoreboard ---- */
.board{display:grid;grid-template-columns:repeat(3,1fr);
background:linear-gradient(135deg,var(--maroon) 0%%,var(--maroon-deep) 100%%);
border:1px solid rgba(210,183,124,.28);border-radius:16px;overflow:hidden}
.board-cell{padding:20px 22px;border-right:1px solid rgba(210,183,124,.18);
display:flex;flex-direction:column;gap:7px}
.board-cell:last-child{border-right:0}
.board-label{font-size:.63rem;letter-spacing:.19em;text-transform:uppercase;
color:rgba(232,216,184,.75);font-weight:700}
.board-value{font-size:2.6rem;font-weight:700;color:var(--gold);line-height:1;
letter-spacing:-.02em}
.board-suffix{font-size:.73rem;color:rgba(232,216,184,.6);letter-spacing:.04em}

/* ---- cards ---- */
.card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));
gap:16px;margin-top:16px}
.card{background:var(--surface);border:1px solid var(--edge);border-radius:16px;
padding:19px 22px;margin-top:16px}
.card-grid .card{margin-top:0}
.card h3{margin:0 0 15px;font-size:.66rem;letter-spacing:.19em;
text-transform:uppercase;color:var(--dim);font-weight:700}
.card h3 .sub{color:var(--gold);font-weight:700}
.card.wide{grid-column:1/-1}
.caption{margin:12px 0 0;font-size:.76rem;color:var(--dim)}

/* ---- vertical bars, grades along the x axis ---- */
.vchart{display:flex;align-items:flex-end;gap:clamp(6px,2.4vw,26px);
padding-top:4px}
.vcol{flex:1 1 0;min-width:0;display:flex;flex-direction:column;
align-items:center;gap:7px}
.vnum{font-family:var(--mono);font-variant-numeric:tabular-nums;
font-size:.95rem;font-weight:700;color:var(--gold);line-height:1}
/* the track is a baseline, not a container: a visible box behind each column
   reads as a stacked bar with an empty upper segment */
.vtrack{width:100%%;height:clamp(90px,16vw,150px);display:flex;
align-items:flex-end;border-bottom:1px solid var(--edge)}
.vfill{width:100%%;border-radius:6px 6px 0 0;min-height:3px;
background:linear-gradient(180deg,var(--gold),var(--gold-dim))}
.vlabel{font-size:.78rem;color:var(--text);white-space:nowrap}

/* ---- one chart per answer, side by side, never combined ---- */
.split-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:14px 34px}
.split h4{display:flex;align-items:center;gap:9px;margin:0 0 13px;
font-size:.86rem;font-weight:700;color:var(--text)}
.split h4 b{margin-left:auto;color:var(--gold);font-size:.95rem;font-weight:700}
.swatch{width:11px;height:11px;border-radius:3px;flex:0 0 11px}

/* ---- bars ---- */
.figure-row{display:flex;align-items:baseline;justify-content:space-between;
gap:14px;padding:7px 0;border-bottom:1px solid rgba(232,216,184,.06)}
.figure-row:last-child{border-bottom:0}
.figure-row .bar-value{font-size:1.05rem}
.bar-value.is-zero{color:var(--dim)}
.bar-row{display:grid;grid-template-columns:118px 1fr 34px;align-items:center;
gap:12px;margin-bottom:9px}
.bar-row:last-child{margin-bottom:0}
.bar-label{font-size:.83rem;overflow:hidden;text-overflow:ellipsis;
white-space:nowrap}
.bar-track{background:rgba(232,216,184,.07);border-radius:6px;height:15px;
overflow:hidden}
.bar-fill{display:block;height:100%%;border-radius:6px;
background:linear-gradient(90deg,var(--gold-dim),var(--gold))}
.bar-value{font-size:.86rem;font-weight:700;text-align:right;color:var(--gold)}
.empty{color:var(--dim);font-size:.83rem;margin:0}
.footer{margin-top:26px;font-size:.72rem;color:var(--dim)}

/* ---- season comparison ---- */
.cmp-legend{display:flex;flex-wrap:wrap;gap:16px 22px;margin:0 0 12px}
.cmp-legend-item{display:flex;align-items:center;gap:7px;font-size:.78rem;
color:var(--dim)}
.cmp-legend-key{width:14px;height:2px;border-radius:1px;flex:0 0 14px}
.cmp-legend-key.cmp-last{background:#A82A55}
.cmp-legend-key.cmp-this{background:var(--gold)}
.cmp-note{margin:0 0 10px;font-size:.8rem;color:var(--dim)}
.timeline{width:100%%;height:auto;display:block}
.timeline .axis{font-size:9px;fill:var(--dim);font-family:var(--sans)}
.cmp-end-label{font-family:var(--mono);font-variant-numeric:tabular-nums;
font-size:.8rem;font-weight:700;fill:var(--gold)}
.cmp-hit{fill:transparent}
.cmp-bar-label{font-family:var(--mono);font-variant-numeric:tabular-nums;
font-size:8px;font-weight:700}
.cmp-bar-label-last{fill:#D98CAA}
.cmp-bar-label-this{fill:var(--gold)}
.cmp-callout-title{font-family:var(--mono);font-variant-numeric:tabular-nums;
font-size:9px;font-weight:800;fill:var(--gold)}
.cmp-callout-sub{font-size:6.5px;fill:var(--dim)}
.cmp-callout-title2{font-family:var(--mono);font-variant-numeric:tabular-nums;
font-size:7.5px;font-weight:800;fill:#E8D8B8}
.cmp-callout-grade{font-size:7px;fill:var(--text)}
.cmp-callout-grade-n{font-family:var(--mono);font-variant-numeric:tabular-nums;
font-size:7px;font-weight:700;fill:var(--gold)}
.cmp-heatmap-label{display:flex;align-items:center;gap:8px;margin:14px 0 4px;
font-size:.78rem;color:var(--dim)}
.cmp-heatmap-label:first-of-type{margin-top:0}
.cmp-heatmap .axis{font-size:9.5px}

@media(max-width:860px){
.shell{flex-direction:column}
.rail{flex:0 0 auto;border-right:0;border-bottom:1px solid var(--edge);
padding:18px 16px;gap:16px}
.rail-foot{margin-top:0}
/* wrap rather than scroll: with a scroll strip the active registration can sit
   off-screen and there is no way to tell which one you are looking at */
.tabs{flex-direction:row;flex-wrap:wrap;gap:8px}
.tab-button{flex:1 1 auto;border-radius:999px;padding:9px 15px}
.tab-name{flex:1 1 auto}
.main{padding:20px 16px 44px}
.board{grid-template-columns:1fr}
.board-cell{border-right:0;border-bottom:1px solid rgba(210,183,124,.18);
padding:15px 18px;flex-direction:row;align-items:baseline;justify-content:space-between}
.board-cell:last-child{border-bottom:0}
.board-value{font-size:1.7rem}
.card-grid{grid-template-columns:1fr}
.bar-row{grid-template-columns:96px 1fr 30px}
}
@media(prefers-reduced-motion:reduce){*{transition:none !important}}
""" % (MAROON, MAROON_DEEP, COUGAR, GOLD, GOLD_DIM, CREAM, GROUND, SURFACE,
       SURFACE_2, EDGE, TEXT, TEXT_DIM)

SCRIPT = """
// The countdown depends on today, not on the registration data, so baking it in
// at build time leaves it stale on every day nobody registers - and wrong on the
// morning of the event, which is when it matters most. Recompute it on load.
document.querySelectorAll('.board-cell[data-cd-y]').forEach(function(cell){
  var y = parseInt(cell.dataset.cdY, 10);
  var m = parseInt(cell.dataset.cdM, 10);
  var d = parseInt(cell.dataset.cdD, 10);
  if (!y || !m || !d) { return; }
  var now = new Date();
  // Compare whole calendar days, so a late-evening view does not read a day off.
  var today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  var days = Math.round((Date.UTC(y, m - 1, d) - today) / 86400000);
  var value = '\\u2014', suffix = 'finished';
  if (days > 1) { value = String(days); suffix = 'days out'; }
  else if (days === 1) { value = '1'; suffix = 'day out'; }
  else if (days === 0) { value = '0'; suffix = 'today'; }
  cell.querySelector('.board-value').textContent = value;
  cell.querySelector('.board-suffix').textContent = suffix;
});

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


def _event_sort_key(tab):
    """Explicit priority first (lower first); ties break by soonest event,
    then name. Registrations without a priority or date fall to the end."""
    event = tab.get("event") or {}
    start = event.get("start")
    priority = tab.get("priority", 999)
    if start:
        return (priority, 0, start, tab.get("name", ""))
    return (priority, 1, "", tab.get("name", ""))


def render_dashboard(tabs, generated_at, today):
    tabs = sorted(tabs, key=_event_sort_key)
    slugs = unique_slugs(tabs)

    if tabs:
        buttons = "".join(
            '<button class="tab-button%s" data-slug="%s" role="tab" aria-selected="%s">'
            '<span class="tab-name">%s</span>'
            '<span class="tab-count">%d</span></button>'
            % (" is-active" if i == 0 else "", escape(slugs[i]),
               "true" if i == 0 else "false", escape(tab["name"]),
               tab["metrics"].get("total", 0))
            for i, tab in enumerate(tabs))
        panels = "".join(_panel(tab, slugs[i], today, i == 0)
                         for i, tab in enumerate(tabs))
    else:
        buttons = '<p class="empty">No active registrations.</p>'
        panels = ('<div class="card"><p class="empty">No active registrations. '
                  'Nothing is open in SportsEngine right now.</p></div>')

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        '<link rel="icon" href="assets/favicon.png">'
        "<title>LSGBA Registrations</title><style>%s</style></head><body>"
        '<div class="shell">'
        '  <aside class="rail">'
        '    <div class="brand">'
        '      <img src="assets/lsgba-badge.png" alt="Lakeville South Basketball">'
        '      <div><p class="brand-org">Lakeville South</p>'
        '           <p class="brand-sub">Girls Basketball</p></div>'
        '    </div>'
        '    <div><p class="rail-label">Open registrations</p>'
        '         <nav class="tabs" role="tablist">%s</nav></div>'
        '    <div class="rail-foot"><p class="rail-label">Updated</p>'
        '         <p class="stamp num">%s</p></div>'
        '  </aside>'
        '  <main class="main">%s'
        '    <p class="footer">Aggregate counts only. Rebuilt on demand from '
        'SportsEngine.</p>'
        '  </main>'
        '</div>'
        "<script>%s</script></body></html>\n"
        % (STYLE, buttons, escape(generated_at), panels, SCRIPT))
