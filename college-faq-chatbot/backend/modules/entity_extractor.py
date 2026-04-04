"""
Lightweight rule-based entity extraction for campus queries.

Returns a clean dict: ``{semester: 5, department: 'CS', course_code: 'CS301', dates: ['2024-11-15']}``
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Department codes / names commonly used on Indian campuses
# ---------------------------------------------------------------------------
_DEPT_PATTERN = re.compile(
    r"\b(CS|IT|ME|CE|EC|EE|EEE|AIML|AIDS|MBA|MCA|CHE|PE|BT)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Semester patterns
# ---------------------------------------------------------------------------
_SEM_PATTERNS = [
    re.compile(r"\bsem(?:ester)?\s*(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*sem(?:ester)?\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Year patterns  (e.g. "third year", "3rd year", "FY", "SY", "TY")
# ---------------------------------------------------------------------------
_YEAR_WORD_MAP = {
    "first": 1, "1st": 1, "fy": 1,
    "second": 2, "2nd": 2, "sy": 2,
    "third": 3, "3rd": 3, "ty": 3,
    "fourth": 4, "4th": 4,
    "final": 4,
}
_YEAR_PATTERNS = [
    re.compile(r"\b(first|second|third|fourth|final)\s*year\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s*year\b", re.IGNORECASE),
    re.compile(r"\b(FY|SY|TY)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Course codes like CS301, IT 402, ME-501
# ---------------------------------------------------------------------------
_COURSE_PATTERN = re.compile(
    r"\b(?!(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)\b)([A-Z]{2,5})[\s-]?(\d{3,4})\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Dates: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, 15 May 2026
# ---------------------------------------------------------------------------
_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b"),
    re.compile(r"\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b"),
    re.compile(
        r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})\b",
        re.IGNORECASE,
    ),
]

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _normalize_year(y: str) -> int:
    y = y.strip()
    if len(y) == 2:
        return 2000 + int(y)
    return int(y)


def extract_entities(text: str) -> dict[str, Any]:
    """
    Extract semester, department, course code, year, and dates from free text.

    Example::

        >>> extract_entities("SEM 5 CS exam date")
        {'semester': 5, 'department': 'CS'}
        >>> extract_entities("third year IT timetable")
        {'year': 3, 'department': 'IT'}
    """
    out: dict[str, Any] = {}
    if not text:
        return out

    # --- Semester ---
    for pat in _SEM_PATTERNS:
        m = pat.search(text)
        if m:
            out["semester"] = int(m.group(1))
            break

    # --- Year ---
    if "semester" not in out:
        for pat in _YEAR_PATTERNS:
            m = pat.search(text)
            if m:
                token = m.group(1).lower()
                if token in _YEAR_WORD_MAP:
                    out["year"] = _YEAR_WORD_MAP[token]
                elif token.isdigit():
                    out["year"] = int(token)
                break

    # --- Department ---
    dm = _DEPT_PATTERN.search(text)
    if dm:
        out["department"] = dm.group(1).upper()

    # --- Course code ---
    cm = _COURSE_PATTERN.search(text)
    if cm:
        dept_part = cm.group(1).upper()
        num = cm.group(2)
        out["course_code"] = f"{dept_part}{num}"
        if "department" not in out and dept_part in {
            "CS", "IT", "ME", "CE", "EC", "EE", "EEE", "MBA", "MCA",
            "CHE", "PE", "BT", "AIML", "AIDS",
        }:
            out["department"] = dept_part

    # --- Dates ---
    dates_found: list[str] = []
    for idx, pat in enumerate(_DATE_PATTERNS):
        for m in pat.finditer(text):
            try:
                if idx == 0:
                    d, mo, y = m.group(1), m.group(2), m.group(3)
                    dt = datetime(_normalize_year(y), int(mo), int(d))
                elif idx == 1:
                    y, mo, d = m.group(1), m.group(2), m.group(3)
                    dt = datetime(int(y), int(mo), int(d))
                else:
                    d, mon, y = m.group(1), m.group(2), m.group(3)
                    mon_key = mon[:3].lower()
                    month_num = _MONTH_MAP.get(mon_key)
                    if month_num is None:
                        continue
                    dt = datetime(_normalize_year(y), month_num, int(d))
                dates_found.append(dt.date().isoformat())
            except (ValueError, IndexError, TypeError):
                continue

    if dates_found:
        out["dates"] = dates_found

    return out
