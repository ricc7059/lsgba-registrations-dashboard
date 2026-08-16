"""Read, write, and diff the run state. Counts and dates only."""

import datetime
import io
import json
import os
import re


def now_stamp():
    """Local time, ISO 8601 with a UTC offset: '2026-08-15T21:55:00-05:00'."""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def touch_last_run(data, stamp=None):
    """Stamp lastRun. Call it from anything that advances the dashboard."""
    data["lastRun"] = stamp or now_stamp()
    return data["lastRun"]


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower())
    return slug.strip("-")


def load(path):
    if not os.path.exists(path):
        return {"lastRun": None, "registrations": {}}
    with io.open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("lastRun", None)
    data.setdefault("registrations", {})
    return data


def save(path, data):
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
        handle.write("\n")


def diff(data, discovered):
    """Compare discovered counts against state. Movement in EITHER direction counts."""
    results = []
    for item in discovered:
        entry = data.get("registrations", {}).get(item["id"])
        previous = entry.get("lastCount") if entry else None
        is_new = previous is None
        delta = 0 if is_new else item["count"] - previous
        results.append({
            "id": item["id"],
            "name": item["name"],
            "count": item["count"],
            "previous": previous,
            "delta": delta,
            "is_new": is_new,
            "changed": is_new or delta != 0,
        })
    return results


def record_export(data, reg_id, name, count, export_filename, stamp=None):
    """Advance state for one registration. Only called after a successful export."""
    touch_last_run(data, stamp)
    registrations = data.setdefault("registrations", {})
    entry = registrations.setdefault(reg_id, {})
    previous = entry.get("lastCount")

    entry["name"] = name
    entry["slug"] = entry.get("slug") or slugify(name)
    entry["previousCount"] = previous
    entry["lastDelta"] = 0 if previous is None else count - previous
    entry["lastCount"] = count
    entry["lastExport"] = export_filename
    # 'event' is hand-maintained and must survive every automated write.
    entry.setdefault("event", None)
