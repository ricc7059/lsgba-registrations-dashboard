"""Read, write, and diff the run state. Counts and dates only."""

import io
import json
import os
import re


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


def record_export(data, reg_id, name, count, export_filename):
    """Advance state for one registration. Only called after a successful export."""
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
