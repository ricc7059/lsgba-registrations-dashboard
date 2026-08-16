"""Decide whether any registration moved. Exit 0 if yes, 1 if nothing to do.

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", required=True,
                        help='JSON list of {"id","name","count"}')
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    args = parser.parse_args()

    data = state.load(args.state)
    results = state.diff(data, json.loads(args.counts))
    print(json.dumps(results, indent=2))

    changed = [r for r in results if r["changed"]]
    if not changed:
        print("\nNo change since %s" % (data.get("lastRun") or "never"), file=sys.stderr)
        return 1
    print("\n%d registration(s) changed" % len(changed), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
