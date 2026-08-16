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
