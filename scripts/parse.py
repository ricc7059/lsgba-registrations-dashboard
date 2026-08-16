"""Read a SportsEngine Quick Report export, dropping PII at the door."""

import csv
import io

# Columns that must never be loaded into memory, matched case-insensitively.
# Order Status, Gross, Net and Service Fee are dropped as financial data,
# which this project deliberately does not report on.
PII_COLUMNS = {
    "first name",
    "last name",
    "date of birth",
    "order number",
    "account email",
    "order status",
    "attached",
    "gross",
    "net",
    "service fee",
}

# Layer 1 is only as good as the header names it anticipates, and exact matching
# is brittle against exactly the renames that matter: "Date of Birth" becoming
# "Birthdate", a new "Parent/Guardian Name" question, a "Cell Phone" field.
# Any column whose lowercased header contains one of these tokens is dropped as
# well. Over-dropping is the safe direction — the aggregate view loses nothing
# important if a stray column disappears, whereas under-dropping publishes a
# child's name. Verified against the live exports: "Athlete's current grade
# (entering Fall 2026)", "What sessions will your player be attending?",
# "Interested in coaching for the 2026-27 travel season?" and "Registration
# Date" all survive this list.
PII_TOKENS = (
    "name",
    "email",
    "e-mail",
    "phone",
    "mobile",
    "cell",
    "address",
    "street",
    "city",
    "zip",
    "postal",
    "birth",
    "dob",
    "parent",
    "guardian",
    "contact",
    "notes",
    "comment",
)


def is_pii_column(name):
    """True if this header must be dropped at read time."""
    lowered = (name or "").strip().lower()
    if lowered in PII_COLUMNS:
        return True
    return any(token in lowered for token in PII_TOKENS)

# Six literal characters: backslash, u, F, E, F, F. NOT a byte-order mark.
# SportsEngine emits the escape sequence itself rather than the character it
# denotes, so utf-8-sig decoding does not remove it.
BOM_LITERAL = "\\uFEFF"
REAL_BOM = u"﻿"


def strip_leading_bom_literal(text):
    """Remove SportsEngine's literal backslash-uFEFF prefix, or a real BOM."""
    if text.startswith(BOM_LITERAL):
        return text[len(BOM_LITERAL):]
    if text.startswith(REAL_BOM):
        return text[len(REAL_BOM):]
    return text


def parse_export(path):
    """Parse an export into {'columns': [...], 'rows': [{...}]} with PII removed."""
    with io.open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()

    reader = csv.reader(io.StringIO(strip_leading_bom_literal(raw)))
    all_rows = list(reader)
    if not all_rows:
        return {"columns": [], "rows": []}

    header = [strip_leading_bom_literal(name).strip() for name in all_rows[0]]
    keep = [i for i, name in enumerate(header) if not is_pii_column(name)]
    columns = [header[i] for i in keep]

    rows = []
    for raw_row in all_rows[1:]:
        if not any(cell.strip() for cell in raw_row):
            continue
        row = {}
        for i in keep:
            row[header[i]] = raw_row[i].strip() if i < len(raw_row) else ""
        rows.append(row)

    return {"columns": columns, "rows": rows}
