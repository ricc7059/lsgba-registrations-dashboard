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

Read the exit code exactly:

- **0** — at least one registration changed. Continue with only the ones whose
  `changed` is `true`.
- **3** — nothing moved. Report "no change since \<lastRun\>" and STOP. Do not
  export, rebuild, commit, or push.
- **2** — bad input or unreadable state. Nothing was compared, so you know
  nothing. Report the error message and STOP. Never report "no change" on a 2.

If stderr carries `WARNING: ... is in state.json but was not discovered`, a
registration you should have found in step 1 is missing. Say so in your report.

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

**Run these one at a time and stop on the first non-zero exit.** `build.py`
exits non-zero when a registration in `state.json` could not be rendered —
almost always because its export is no longer in `~/Downloads`. It still writes
`index.html` so you can look at it, but that page is missing a tab and must not
be committed over the good one. Re-export the missing registration (step 4) and
build again. Do not commit a build that exited non-zero.

`build.py` also runs the PII scan and refuses to write if it trips. If it raises
`PIIFound`, STOP and report which pattern matched — the message gives the kind
and count only, and deliberately does not echo the matched values. Do not
bypass it.

If `build.py` prints `count mismatch: ...`, the CSV row count and the count read
off the SportsEngine page disagree. The build is deliberately allowed to
continue; carry the discrepancy into your report.

Pages redeploys automatically on push, usually within a minute.

Whenever a currently-Enabled registration's name contains "Travel Tryout",
`build.py` also appends a second, composite **"Registration Comparison to
Last Season"** tab overlaying that registration's live timeline against last
season's frozen 2025-26 numbers (`scripts/history.py`) — no extra step needed;
it is derived fresh from the same export every time this build step runs. See
"Season comparison tab" under Notes below.

## 6. Report back

Tell the user, per registration: the new total, the delta, and whether the
fallback fired. Also relay, verbatim, anything the tools warned about:

- any `count mismatch:` line from `build.py` (CSV rows vs. the page total),
- any registration `build.py` skipped for a missing export,
- any registration `check.py` flagged as present in `state.json` but not
  discovered.

A warning nobody reads is the same as no warning. Finish with the dashboard URL.

## Notes

- Never open an order, payment, or discount page. This skill does not report
  financials.
- Stopping at step 3 leaves nothing stale. The countdown is recomputed in the
  browser on every page load from the event date, so it stays correct on days
  nobody registers. Only the counts and the "Updated" stamp are fixed at build
  time, and those genuinely have not changed. Do not add a daily rebuild to
  refresh the countdown.
- A registration with no `event` block in `state.json` renders without a
  countdown. Ask the user for its dates and add them by hand.
- `--dry-run` on `build.py` writes `index.html` exactly as a normal run does; it
  only skips the commit-and-push step and says so. The regenerated page is left
  in the working tree, so a later `git add -A` will sweep it up. It is a
  "stop before publishing" switch, not a "change nothing on disk" switch.

## Season comparison tab

`build.py` matches the live registration by name (`"travel tryout"`,
case-insensitive) rather than by survey id, because SportsEngine mints a new
id for this registration every season — no state.json edit is needed when
next year's id shows up. Whichever tab it matches becomes "this season"; its
metrics already come from the export you just parsed in step 5, so the
comparison tab always reflects the count you just recorded, with no separate
export or record step of its own. If no Enabled registration's name contains
"Travel Tryout", or that registration has zero signups so far, the comparison
tab is simply omitted — this is normal outside the tryout registration window,
not an error.

"This season's" day-offset in every chart on this tab is measured from the
live registration's own opening day, zero-filled by `compare.py` through the
build's own today — so a same-day registration (e.g. one recorded at 9am and
built at 11am) is already in the day it belongs to, with no lag. Verified
directly once (2026-08-22): a single new registrant that day showed up as
`{"date": "2026-08-22", "new": 1, ...}` in `aggregate.aggregate()`'s
timeline, as the last day-column in the by-grade heatmap, and as a small
bar on the daily chart — genuinely a "1"-count bar, easy to mistake for
missing at a glance next to a 10+ count neighbour, not actually absent. If
this is ever in doubt again, check `metrics["timeline"][-1]` (or
`grade_timeline[-1]`) from the just-parsed export directly rather than
eyeballing the rendered chart.

Last season (2025-26: Aug 11 - Sep 10, 2025, 116 total, including a grade
breakdown backfilled from a later re-export — see `history.py`'s docstring) is
frozen in `scripts/history.py` as day-offset counts only — no names, no export
file, no raw CSV. That export is gone and the season will not reopen, so this
data never changes; it does not need to be, and cannot be, refreshed by this
skill. If a future season's dashboard should compare against *this* season
once it closes, freeze this season's numbers into `scripts/history.py` the
same way (see that file's header) and update `THIS_YEAR_LABEL` in
`scripts/compare.py`.

The tab has five charts. The cumulative chart aligns by **day of
registration window** (day 0 = the day registration opened) rather than
calendar date, deliberately — the two seasons open a couple of days apart,
and a shared day-offset axis is what makes a same-point-in-season pace
comparison mean anything. The daily bar chart aligns by **actual calendar
date** instead — a bar under the "Aug 13" tick is that season's real Aug 13,
not whatever day-of-window happened to land there. `compare.py`'s
`calendar_shift` is the gap in days between the two seasons' opening dates
(e.g. +2 when this season opens Aug 13 and last season opened Aug 11); the
daily chart shifts this season's bars by that amount before plotting them,
so the two seasons' actual matching dates line up instead of their
day-*offsets*. This distinction matters: before this shift existed, this
season's Aug 13 registrations were plotted under an "Aug 11" label (borrowed
from last season, which is the axis's calendar reference), which read as if
they had happened two days before the registration actually opened.

The by-grade heatmap grids (below) are the one chart that does *not* use
`calendar_shift` — this season's grid is deliberately plain day-of-window,
left-aligned from its own day 0, not calendar-aligned under last season's
grid above it. An earlier version of this skill did calendar-align it (the
same way the daily chart still does); the user asked for that to be reverted
so this season's grid stays compact and its Total column sits right next to
it instead of out at the far edge of a full-width canvas — see chart 3
below.

1. **Cumulative registrations** — both seasons' running totals overlaid, by
   day-of-window (not calendar-shifted — see above).
2. **Daily registrations** — both seasons' new-per-day counts paired bar by
   bar, calendar-aligned. The chart carries **two** callouts, one for on-or-before Aug 24
   ("through Aug 24"), one for after, both last season's numbers only
   (neither is re-evaluated against this season), each with the same two
   parts:
   - "N registrations {through/after} Aug 24 · X% of last season" — from
     `history.CUTOFF_DAY`/`CUTOFF_LABEL`, as before.
   - "N made a travel team · X%" plus a by-grade breakdown — a one-time
     cross-reference (by name, cross-checked on grade) of that half-season's
     registrants against the 2025 team-acceptance roster, frozen as
     `history.MADE_TEAM_AFTER_CUTOFF`/`_BY_GRADE` and
     `history.MADE_TEAM_BEFORE_CUTOFF`/`_BY_GRADE` (see the after-cutoff
     constant's comment for the exact method and its one known gap: one
     accepted player had no name match in the registration export and is
     excluded from both). Like everything else in `history.py`, this can't
     be refreshed by this skill — it was computed once, by hand, from a
     private roster file that is never committed, and it never needs to be
     recomputed unless the underlying source files turn out to be wrong.

   Only the after-Aug-24 half of the chart gets the highlighted gold
   background — the before half's callout sits on the plain chart, so
   "highlighted" keeps meaning one specific thing. Both callouts are small
   plain text (see `render._callout_block`): headline stats on the left,
   the grade tally as an actual list — one row per grade, count
   right-aligned — on the right of a hairline divider, no backdrop box.
   Text this small and unboxed is legible because it is deliberately kept
   short and drawn *after* the bars (last in the SVG source, see
   `_comparison_bar_svg`), not because it is large or has its own card —
   if a future edit adds more lines here, keep it terse, and keep the
   draw order last, so a tall bar never paints over it.
3. **Daily registrations by grade** — a heatmap, one grid per season stacked
   vertically (not a stacked bar chart — that read poorly with this many
   grade categories). Last season's grid spans the full season (up to 31
   columns, `domain_days`-wide); this season's grid is compact — only as many
   columns as it actually has days, left-aligned from its own day 0 (see the
   calendar-alignment note above) — so its canvas is only as wide as it needs
   to be and its **Total** column lands immediately to its right, not out at
   a fixed 860px edge with a lot of empty space in between. Column pixel
   width (`slot`, in `_comparison_heatmap_svg`) is still derived from last
   season's full-width canvas, so a day is the same width in both grids even
   though this season's is narrower overall — pass `n_cols=<this season's day
   count>` to get that; leaving it unset renders the full-width grid, which
   is what last season's call still does. Rows are grade, columns are
   day-offset, and cell shade is that season's own identity colour (maroon
   for last season, gold for this season) at an opacity scaled to the count,
   on one shared 0–max scale across both grids so "darker" means the same
   thing in both. This season's grid only draws cells through today — a day
   that hasn't happened yet stays blank rather than reading as a false zero.

   Every nonzero cell is directly labelled with its count (see
   `_comparison_heatmap_svg`); text colour is picked per cell, not fixed, by
   `_cell_text_colour` — it blends the cell's own colour with the card
   surface at that cell's actual opacity and computes the blended shade's
   relative luminance, so a barely-shaded cell (near the dark surface) gets
   light text and a fully-saturated gold cell (itself light) gets dark ink,
   both calculated rather than assumed. Each row also ends in a **Total**
   column past a hairline divider — that grade's sum across every day shown,
   not just the visible range, so it stays right even though the two grids
   don't span the same number of columns (last season's is the full 31-day
   window; this season's stops at today).
4. **Grade-cohort flow** — a diverging bar chart in the space this season's
   compact heatmap frees up to its right, centered in that space
   (`.cmp-flow-block{margin:0 auto}` in the stylesheet, so the row's leftover
   width past the compact heatmap splits evenly onto both sides of the
   block) rather than sitting flush against the compact heatmap or pinned to
   the far right edge. See `_flow_diagram_svg`. It compares last season's
   grade *G* against this
   season's grade *G+1* — the same cohort of students, one grade further
   along (last season's 3rd grade is this season's 4th grade) — as one row
   per transition, bars extending right/green (`FLOW_POS`, this season's
   cohort grew) or left/red (`FLOW_NEG`, it shrank) from a zero centerline.
   `compare._grade_flow` builds the data (`comparison["grade_flow"]`): it
   only emits a row when the *next* grade actually appears somewhere in the
   shared `grades` list — so 8th grade (this club has never had a 9th) gets
   no row at all, not an invented "graduated" category, while a grade that
   exists in `grades` but currently has zero registrants still gets a real
   (and informative) negative-delta row. The signed delta is always drawn as
   a visible label, never colour alone — inside the bar near its outward tip
   when the bar is wide enough to hold it, otherwise just outside the tip, on
   the side moving *away* from the row's grade-transition label (this
   avoids a label collision that showed up once as "5th→6th-10" when a
   near-max-magnitude bar's outside label ran into the axis text — see
   `_flow_diagram_svg`'s docstring). Its rows share row height/spacing with
   the heatmap beside it (`_heatmap_height`) so the two line up visually,
   though the flow diagram is normally one row shorter (no 8th-grade row).
   FLOW_POS/FLOW_NEG were validated with the dataviz skill's
   `validate_palette.js` against the card's dark surface: PASS on lightness,
   chroma, and contrast; the colorblind-separation check is a WARN, which is
   legal only with a secondary encoding — satisfied here by both the
   left/right position and the always-visible signed number.

All charts on this tab that have a day axis (cumulative, daily bars, both
heatmap grids) label **every day**, not every 5th — with up to 31 possible
days that only fits by rotating each label -90° (see
`_vertical_axis_labels`). The rotation anchor matters: it must sit just past
the plot's own baseline (axis line, or the heatmap grid's bottom edge) with
the label extending *away* from the plot into the padding reserved for it —
anchoring near the SVG's outer edge instead leaves most of the label with
nowhere to render and it clips silently (this happened once: only each
label's last character survived, e.g. "Day 12" showing as "2"). If a label
ever looks truncated again, check the anchor's distance from the SVG's own
bottom edge first.

Both seasons' exports spell grade differently ("3rd Grade" this season, "3rd"
last season, per each export's own grade question) — `compare.py` normalizes
both to the short form before matching a row across seasons, so this doesn't
split into two rows. If a future season's export renames the grade question,
`aggregate.py`'s grade-column detection already handles that the same way it
does for the per-registration "By grade" card; the label just needs to keep
ending in some form of "Grade" (or not) for the normalizer to strip it — see
`compare._normalize_grade`.
