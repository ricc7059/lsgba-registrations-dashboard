"""Decide whether any registration moved.

Exit codes are distinct on purpose, because "nothing moved" and "I could not
tell" must never look the same to the caller:

  0  at least one registration changed — export and rebuild
  3  nothing changed — stop, there is no work
  2  bad input or unreadable state — nothing was compared, fix and retry

Usage:
  python3 scripts/check.py --counts '[{"id":"1126331","name":"Tryout","count":23}]'
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import state  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXIT_CHANGED = 0
EXIT_ERROR = 2
EXIT_NO_CHANGE = 3


def parse_counts(raw):
    """Return a validated list of {'id','name','count'}. Raises ValueError."""
    try:
        discovered = json.loads(raw)
    except ValueError as error:
        raise ValueError("--counts is not valid JSON: %s" % error)
    if not isinstance(discovered, list):
        raise ValueError("--counts must be a JSON list of objects")
    for index, item in enumerate(discovered):
        if not isinstance(item, dict):
            raise ValueError("--counts[%d] is not an object" % index)
        for key in ("id", "name", "count"):
            if key not in item:
                raise ValueError("--counts[%d] is missing %r" % (index, key))
        if not isinstance(item["count"], int) or isinstance(item["count"], bool):
            raise ValueError("--counts[%d] count must be a whole number" % index)
        item["id"] = str(item["id"])
    return discovered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", required=True,
                        help='JSON list of {"id","name","count"}')
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    args = parser.parse_args()

    try:
        discovered = parse_counts(args.counts)
    except ValueError as error:
        print("ERROR: %s" % error, file=sys.stderr)
        return EXIT_ERROR

    try:
        data = state.load(args.state)
        results = state.diff(data, discovered)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print("ERROR: could not compare counts against %s: %s"
              % (args.state, error), file=sys.stderr)
        return EXIT_ERROR

    print(json.dumps(results, indent=2))

    # A registration that state knows about but discovery did not report is a
    # discovery miss, not a quiet no-op. Say so.
    seen = set(item["id"] for item in discovered)
    for reg_id in sorted(data.get("registrations", {})):
        if reg_id not in seen:
            entry = data["registrations"][reg_id]
            print("WARNING: %s (%s) is in state.json but was not discovered"
                  % (reg_id, entry.get("name") or "unnamed"), file=sys.stderr)

    changed = [r for r in results if r["changed"]]
    if not changed:
        print("\nNo change since %s" % (data.get("lastRun") or "never"), file=sys.stderr)
        return EXIT_NO_CHANGE
    print("\n%d registration(s) changed" % len(changed), file=sys.stderr)
    return EXIT_CHANGED


# check.py deliberately does not stamp lastRun on a no-change run. It is a
# read-only probe: writing state.json here would dirty the working tree of a
# run that is about to stop before committing, and that stray diff would ride
# along with the next real refresh. lastRun means "when the dashboard last
# moved", and state.touch_last_run is available to anything that moves it.
if __name__ == "__main__":
    sys.exit(main())
