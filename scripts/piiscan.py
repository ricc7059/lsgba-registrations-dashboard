"""Fail-closed check that generated HTML carries no athlete PII."""

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# MM/DD/YYYY — the shape SportsEngine uses for Date of Birth. ISO dates
# (YYYY-MM-DD) are used by the timeline axis and are deliberately not matched.
US_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")


class PIIFound(Exception):
    """Raised when generated output contains something that must not be published."""


def scan(html):
    """Return a list of (kind, matched_text) for every suspected PII hit."""
    findings = []
    for match in EMAIL_RE.findall(html):
        findings.append(("email", match))
    for match in US_DATE_RE.findall(html):
        findings.append(("date", match))
    return findings


def assert_clean(html):
    """Raise PIIFound if the HTML contains anything resembling PII."""
    findings = scan(html)
    if findings:
        detail = ", ".join("%s:%s" % (kind, value) for kind, value in findings)
        raise PIIFound("refusing to publish, found %d item(s): %s" % (len(findings), detail))
