# LSGBA Registration Dashboard — Design

**Date:** 2026-08-15
**Skill:** `/lsgba-registration-dashboard`
**Repo:** `ricc7059/lsgba-registrations-dashboard` (public)
**Published at:** `https://ricc7059.github.io/lsgba-registrations-dashboard/`

## Purpose

Give the LSGBA board a single link that shows how each open registration is
filling, refreshed on demand. Running the skill checks every Enabled
registration in SportsEngine, exports a fresh Quick Report CSV for any whose
entry count has moved, and rebuilds the published dashboard from those exports.

## Non-goals

- No financial reporting. The skill never opens an order, payment, or discount
  page.
- No per-athlete detail on the published page. Aggregate counts only.
- No scheduled or unattended runs. Manual invocation only.
- No cross-registration totals. Registrations are never combined.

## Components

| Piece | Location | Purpose |
|---|---|---|
| Skill | `~/.claude/skills/lsgba-registration-dashboard/SKILL.md` | The procedure |
| Local repo | `/Users/ricci/lsgba-registrations-dashboard` | Site source and state |
| State | `<repo>/state.json` | Last-seen counts, slugs, event dates |
| Dashboard | `<repo>/index.html` | Self-contained page, data inlined |
| Exports | `/Users/ricci/Downloads/lsgba-<slug>-YYYY-MM-DD-HHMM.csv` | Raw CSVs, never committed |

The page is a single self-contained `index.html` with its data inlined as a JS
object. No `data.json` fetch, no CDN, no external assets — one file that either
works or doesn't, which is the right trade for a page the board relies on.

## Flow

1. **Discover.** Open `https://lsgba.sportngin.com/survey/list`. Read the
   **Enabled** tab. Collect `{surveyId, name}` for every row. No hardcoded IDs.
2. **Read counts.** For each, open `/survey/show/<surveyId>` and read the
   `TOTAL ENTRIES` figure.
3. **Diff.** Compare against `state.json`. A registration is *changed* if its
   count differs from `lastCount` in either direction, or if it has no prior
   entry (first sighting).
4. **Short-circuit.** If nothing changed: report `no change since <lastRun>`
   and stop. No CSV, no rebuild, no commit, no push.
5. **Export.** For each changed registration, click `Export to Excel (.csv)`
   on its Quick Report, wait for the download, then move and rename the newest
   file in `~/Downloads` to `lsgba-<slug>-YYYY-MM-DD-HHMM.csv`.
6. **Aggregate.** Parse the CSVs into counts only (see *Data contract*).
7. **Rebuild.** Regenerate `index.html`, run the PII scan, commit, push.
   GitHub Pages redeploys on push.
8. **Report.** Tell the user which registrations moved, by how much, their new
   totals, and the dashboard URL.

### First run

`state.json` is absent or empty, so every Enabled registration counts as
changed and gets exported. This is correct, not a special case.

### Login

If step 1 lands on a login page instead of the registration list, stop
immediately and tell the user to log into SportsEngine in Chrome. Do not
attempt to authenticate.

## Export mechanism

**Primary (Approach A):** click the real `Export to Excel (.csv)` link
(`a#exportCsvUnsaved`) and take the file SportsEngine produces. This is the
genuine export, identical to what the user would download by hand.

Identify the downloaded file as the newest `*.csv` in `~/Downloads` whose mtime
is after the click. Wait up to 30 seconds.

**Fallback (Approach B):** if no file appears within the timeout, read the
report table out of the DOM and write the CSV directly, paging through the
result set until all rows are captured (the Quick Report paginates at 25 rows).
When the fallback fires, say so in the run report — a silent fallback would
hide a broken export.

## Data contract

Quick Report columns are configured per registration and will differ between
them, so the aggregation must not assume a fixed schema. It reads the header
row and classifies each column by role.

**Never read (PII denylist):**
`First Name`, `Last Name`, `Date Of Birth`, `Account Email`, `Order Number`,
`Attached`, `Order Status`

These columns are dropped at parse time. They are never loaded into the object
that becomes the page.

**Recognized by role:**

- Any header containing `grade` → the grade dimension. Ordered
  3rd → 8th, with anything unrecognized sorted last.
- Any header containing `registration date` → the timeline dimension.

**Everything else** that survives the denylist and has 10 or fewer distinct
values becomes an additional categorical dimension, charted as its own bar
group under the tab. This is what makes the skill survive form changes: today
it picks up *"What sessions will your player be attending?"* on the skills
course and *"Interested in coaching for the 2026-27 travel season?"* on the
tryout, without either being named in code. A new question next season charts
itself.

Columns with more than 10 distinct values are ignored, on the theory that a
high-cardinality free-text field is a comment box, not a dimension — and
comment boxes are exactly where a parent writes something identifying.

### Per-tab metrics

- Total entries — CSV row count, cross-checked against the page's
  `TOTAL ENTRIES`. Report a warning if they disagree.
- Delta since last run.
- Days until the event, from the `events` block in `state.json`.
- Headcount by grade.
- One bar group per additional categorical dimension.
- Cumulative signups by day, and new signups per day, both derived from
  `Registration Date`.

The full signup curve rebuilds from the current CSV on every run, because every
row carries its own registration timestamp. No historical snapshots to store or
keep consistent.

## Dashboard

**Structure — tabbed, one tab per Enabled registration. Registrations are never
combined.** There is no cross-registration KPI band, no shared total, and no
merged timeline. The header carries only the LSGBA identity and the last-updated
timestamp. Tabs are generated from whatever came back in step 1, so a third
registration produces a third tab with no code change.

Each tab is self-contained:

```
┌──────────────────────────────────────────────┐
│ LSGBA REGISTRATIONS      Updated Aug 15 9:45 │
├──────────────────────────────────────────────┤
│ ▎TRAVEL TRYOUT ▕  SKILLS COURSE              │
├──────────────────────────────────────────────┤
│  23              Aug 24–27 · 9 days out      │
│  REGISTERED      +4 since last run           │
│                                              │
│  BY GRADE                                    │
│   3rd ███ 3      4th ██████ 6                │
│   5th ████ 4     6th █████████ 9   7th █ 1   │
│                                              │
│  COACHING INTEREST                           │
│   Head Coach █ 1     Assistant ██ 2          │
│                                              │
│  SIGNUPS OVER TIME                           │
│      ╱‾‾‾                                    │
│   ╱‾‾                                        │
└──────────────────────────────────────────────┘
```

**Style — dark broadcast ground with LSGBA maroon and gold.** Charcoal
background, maroon for the header band and the active tab, gold for bar fills
and the headline numbers, large condensed type on the big figures. Tokens are
defined once at the top of the stylesheet so the palette can be retuned in one
place.

Charts are hand-rolled inline SVG. No chart library, consistent with the
self-contained-single-file rule. Responsive down to phone width, since that is
where board members will actually open the link; tabs collapse to a scrollable
row and bar groups reflow to one column.

## The PII rail

Three independent layers, because this is the part that must not fail:

1. `.gitignore` blocks `*.csv` and `Downloads/` outright. A raw export cannot
   be committed by accident.
2. The parser drops denylisted columns at read time, so names, dates of birth,
   and emails never reach the aggregation object.
3. Before every push, scan the generated `index.html` for `@`-shaped email
   addresses and `NN/NN/NNNN` date-of-birth patterns. **Fail closed** — if the
   scan trips, abort the push and report it rather than publishing.

## State

```json
{
  "lastRun": "2026-08-15T21:45:00-05:00",
  "registrations": {
    "1126331": {
      "name": "2026 LSGBA Travel Tryout Registration",
      "slug": "travel-tryout",
      "lastCount": 23,
      "lastExport": "lsgba-travel-tryout-2026-08-15-2145.csv",
      "event": { "label": "Aug 24–27", "start": "2026-08-24", "end": "2026-08-27" }
    }
  }
}
```

`state.json` is committed. It holds counts and dates only — nothing sensitive.
The `event` block is hand-editable; the skill never overwrites a date the user
has set, and prompts for dates when it first sees a registration it has no
event entry for.

A registration that leaves the Enabled tab keeps its state entry but loses its
tab. Nothing is deleted, and if it is re-enabled its history is still there.

## Error handling

| Condition | Behavior |
|---|---|
| Redirected to login | Stop, tell the user to log into SportsEngine |
| No Enabled registrations | Publish a page stating none are active |
| Download times out | Fall back to DOM scrape, report the fallback |
| CSV row count ≠ page total | Build anyway, report the discrepancy |
| New registration, no event dates | Prompt for dates before building |
| PII scan trips | Abort before push, report which pattern matched |

## Testing

- `--dry-run` performs discovery, diff, export, and page generation, then stops
  before commit and push, leaving `index.html` on disk for local review.
- Verify the export mechanism end to end once during implementation before
  committing to Approach A.
- Verify the PII scan by feeding it a deliberately poisoned page and confirming
  it aborts.
- Confirm the skills-course export contains all 37 rows, not just the 25 on the
  visible page.
- Check the rendered page at phone width.

## Open items

None blocking. Palette values and the exact grade ordering are tunable after
the first render.
