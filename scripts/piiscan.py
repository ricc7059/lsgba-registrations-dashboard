"""Fail-closed check that generated HTML carries no athlete PII.

This layer is a pattern scan and nothing more. It matches shapes — email
addresses, dates, phone numbers — and it CANNOT detect names. "Ada Fake" is
indistinguishable from "Head Coach" to a regular expression, so a leaked
athlete, parent, or guardian name will pass this scan silently. Keeping names
off the page is the job of layer 1 (the parser's column denylist in
scripts/parse.py) and layer 2 (the dimension gate in scripts/aggregate.py).
This layer is the last net, not the first, and it has a hole in it by design.
False assurance would be worse than a documented gap.
"""

import collections
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# MM/DD/YYYY — the shape SportsEngine uses for Date of Birth.
US_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")
# YYYY-MM-DD — the shape a renamed date-of-birth column arrives in. The
# renderer emits only MM/DD on the timeline axis and never a full ISO date, so
# this rule costs the legitimate page nothing.
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# 10 digits, optionally grouped 3-3-4 by a dash, dot, or space.
PHONE_RE = re.compile(r"\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b")

RULES = (
    ("email", EMAIL_RE),
    ("date", US_DATE_RE),
    ("iso-date", ISO_DATE_RE),
    ("phone", PHONE_RE),
)


class PIIFound(Exception):
    """Raised when generated output contains something that must not be published."""


def scan(html):
    """Return a list of (kind, matched_text) for every suspected PII hit."""
    findings = []
    for kind, pattern in RULES:
        for match in pattern.findall(html):
            findings.append((kind, match))
    return findings


def summarize(findings):
    """'2 email, 1 phone' — kinds and counts, never the matched values."""
    counts = collections.Counter(kind for kind, _ in findings)
    return ", ".join("%d %s" % (counts[kind], kind) for kind in sorted(counts))


def assert_clean(html):
    """Raise PIIFound if the HTML contains anything resembling PII.

    The message deliberately carries only kinds and counts. Echoing the matched
    text would copy the very PII this layer caught into the agent transcript and
    from there into its report to the user.
    """
    findings = scan(html)
    if findings:
        raise PIIFound("refusing to publish, found %d item(s): %s"
                       % (len(findings), summarize(findings)))
