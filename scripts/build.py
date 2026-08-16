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
    tabs = []
    registrations = data.get("registrations", {})
    for reg_id in sorted(registrations):
        entry = registrations.get(reg_id)
        if not entry or not entry.get("lastExport"):
            continue
        path = os.path.join(downloads, entry["lastExport"])
        if not os.path.exists(path):
            print("WARNING: missing export %s, skipping %s" % (path, reg_id),
                  file=sys.stderr)
            continue
        metrics = aggregate.aggregate(parse.parse_export(path))
        if metrics["total"] != entry.get("lastCount"):
            print("WARNING: %s has %d CSV rows but state says %s"
                  % (reg_id, metrics["total"], entry.get("lastCount")), file=sys.stderr)
        tabs.append({
            "slug": entry.get("slug") or reg_id,
            "name": entry.get("name") or reg_id,
            "event": entry.get("event"),
            "delta": entry.get("lastDelta", 0),
            "previous": entry.get("previousCount"),
            "metrics": metrics,
        })
    return tabs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--downloads", default=DEFAULT_DOWNLOADS)
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    parser.add_argument("--out", default=os.path.join(REPO, "index.html"))
    args = parser.parse_args()

    data = state.load(args.state)
    now = datetime.datetime.now()
    tabs = build_tabs(data, args.downloads)
    html = render.render_dashboard(
        tabs, now.strftime("%b %-d, %Y %-I:%M %p"), now.strftime("%Y-%m-%d"))

    piiscan.assert_clean(html)  # fail closed before anything touches disk

    with open(args.out, "w") as handle:
        handle.write(html)

    print("wrote %s with %d tab(s)" % (args.out, len(tabs)))
    if args.dry_run:
        print("dry run: not committing or pushing")


if __name__ == "__main__":
    main()
