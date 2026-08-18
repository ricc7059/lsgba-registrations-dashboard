"""Build index.html from state.json and the exports it points at.

Usage:
  python3 scripts/build.py [--dry-run] [--downloads DIR]
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import aggregate, parse, piiscan, render, state  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOWNLOADS = os.path.expanduser("~/Downloads")


def build_tabs(data, downloads):
    """Return (tabs, skipped, mismatches).

    `skipped` holds registrations that state.json expected to render but could
    not, which is a failed build even though a page still gets written.
    `mismatches` holds count disagreements, which the caller must relay.
    """
    tabs = []
    skipped = []
    mismatches = []
    registrations = data.get("registrations", {})
    for reg_id in sorted(registrations):
        entry = registrations.get(reg_id)
        if not entry or not entry.get("lastExport"):
            continue
        path = os.path.join(downloads, entry["lastExport"])
        if not os.path.exists(path):
            print("WARNING: missing export %s, skipping %s" % (path, reg_id),
                  file=sys.stderr)
            skipped.append({"id": reg_id, "name": entry.get("name") or reg_id,
                            "export": entry["lastExport"], "path": path})
            continue
        metrics = aggregate.aggregate(parse.parse_export(path))
        if metrics["total"] != entry.get("lastCount"):
            message = ("%s has %d CSV rows but state says %s"
                       % (reg_id, metrics["total"], entry.get("lastCount")))
            print("WARNING: %s" % message, file=sys.stderr)
            mismatches.append({"id": reg_id, "name": entry.get("name") or reg_id,
                               "csvCount": metrics["total"],
                               "stateCount": entry.get("lastCount"),
                               "message": message})
        tabs.append({
            "id": reg_id,
            "slug": entry.get("slug") or reg_id,
            "name": entry.get("name") or reg_id,
            "event": entry.get("event"),
            "delta": entry.get("lastDelta", 0),
            "previous": entry.get("previousCount"),
            "priority": entry.get("priority", 999),
            "metrics": metrics,
        })
    return tabs, skipped, mismatches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--downloads", default=DEFAULT_DOWNLOADS)
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    parser.add_argument("--out", default=os.path.join(REPO, "index.html"))
    args = parser.parse_args()

    data = state.load(args.state)
    now = datetime.datetime.now()
    tabs, skipped, mismatches = build_tabs(data, args.downloads)
    html = render.render_dashboard(
        tabs, now.strftime("%b %-d, %Y %-I:%M %p"), now.strftime("%Y-%m-%d"))

    piiscan.assert_clean(html)  # fail closed before anything touches disk

    with open(args.out, "w") as handle:
        handle.write(html)

    print("wrote %s with %d tab(s)" % (args.out, len(tabs)))
    for mismatch in mismatches:
        print("count mismatch: %s" % mismatch["message"])
    if args.dry_run:
        print("dry run: not committing or pushing")

    if skipped:
        # The page still got written so a human can look at it, but it is
        # missing a registration. Exit non-zero so the caller stops before
        # committing a partial dashboard over a complete one.
        for item in skipped:
            print("ERROR: %s (%s) was not rendered: export %s is missing"
                  % (item["id"], item["name"], item["export"]), file=sys.stderr)
        print("ERROR: incomplete build, %d registration(s) skipped"
              % len(skipped), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
