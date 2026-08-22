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

Last season (2025-26: Aug 11 - Sep 10, 2025, 116 total, including a grade
breakdown backfilled from a later re-export — see `history.py`'s docstring) is
frozen in `scripts/history.py` as day-offset counts only — no names, no export
file, no raw CSV. That export is gone and the season will not reopen, so this
data never changes; it does not need to be, and cannot be, refreshed by this
skill. If a future season's dashboard should compare against *this* season
once it closes, freeze this season's numbers into `scripts/history.py` the
same way (see that file's header) and update `THIS_YEAR_LABEL` in
`scripts/compare.py`.

The tab has four charts, all aligned by **day of registration window** (day 0
= the day registration opened), not by calendar date — the two seasons open a
couple of days apart, so a shared day-offset axis is what makes the pace
comparison mean anything:

1. **Cumulative registrations** — both seasons' running totals overlaid.
2. **Daily registrations** — both seasons' new-per-day counts paired bar by
   bar, plus last season's after-cutoff window highlighted, with the callout
   text drawn *inside* that highlighted band rather than as a separate note
   above the chart — the highlight and its explanation are one visual unit.
   The callout has two parts, both last season's numbers only (neither is
   re-evaluated against this season):
   - "N registrations after Aug 24 · X% of last season" — from
     `history.CUTOFF_DAY`/`CUTOFF_LABEL`, as before.
   - "N made a travel team · X%" plus a by-grade breakdown — a one-time
     cross-reference (by name, cross-checked on grade) of those after-cutoff
     registrants against the 2025 team-acceptance roster, frozen as
     `history.MADE_TEAM_AFTER_CUTOFF` / `MADE_TEAM_AFTER_CUTOFF_BY_GRADE`
     (see that constant's comment for the exact method and its one known
     gap: one accepted player had no name match in the registration export
     and is excluded). Like everything else in `history.py`, this can't be
     refreshed by this skill — it was computed once, by hand, from a private
     roster file that is never committed, and it never needs to be
     recomputed unless the underlying source files turn out to be wrong.
3. **Daily registrations by grade** — a heatmap, one grid per season stacked
   vertically (not a stacked bar chart — that read poorly with this many
   grade categories). Rows are grade, columns are day-offset, and cell shade
   is that season's own identity colour (maroon for last season, gold for
   this season) at an opacity scaled to the count, on one shared 0–max scale
   across both grids so "darker" means the same thing in both. This season's
   grid only draws cells through today — a day that hasn't happened yet stays
   blank rather than reading as a false zero.

Both seasons' exports spell grade differently ("3rd Grade" this season, "3rd"
last season, per each export's own grade question) — `compare.py` normalizes
both to the short form before matching a row across seasons, so this doesn't
split into two rows. If a future season's export renames the grade question,
`aggregate.py`'s grade-column detection already handles that the same way it
does for the per-registration "By grade" card; the label just needs to keep
ending in some form of "Grade" (or not) for the normalizer to strip it — see
`compare._normalize_grade`.
