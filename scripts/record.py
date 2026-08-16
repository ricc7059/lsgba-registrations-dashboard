"""Record one successful export into state.json.

Usage:
  python3 scripts/record.py --id 1126331 --name "2026 LSGBA Travel Tryout Registration" \
      --count 23 --export lsgba-travel-tryout-2026-08-16-0930.csv
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import state  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--export", required=True)
    parser.add_argument("--state", default=os.path.join(REPO, "state.json"))
    args = parser.parse_args()

    data = state.load(args.state)
    state.record_export(data, args.id, args.name, args.count, args.export)
    state.save(args.state, data)
    print("recorded %s -> %d entries, %s" % (args.id, args.count, args.export))


if __name__ == "__main__":
    main()
