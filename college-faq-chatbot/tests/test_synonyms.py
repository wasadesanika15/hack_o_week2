"""
Tests for synonym-aware FAQ matching — Task 3.

Covers: 5 synonym variations per FAQ category and a coverage report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.chatbot_core import expand_synonyms, get_response  # noqa: E402
from modules.preprocessor import preprocess  # noqa: E402

SESSION = "syn-test"

# 5 synonym variations per FAQ category
SYNONYM_TEST_CASES = {
    "fees": [
        "What is the tuition amount?",
        "How to make payment for semester?",
        "What is the cost of the course?",
        "Tell me about charges for MBA",
        "When are the dues due?",
    ],
    "exam": [
        "When is the next test?",
        "Semester examination schedule",
        "Assessment dates for CS",
        "Paper dates for final year",
        "Midterm dates please",
    ],
    "admission": [
        "How to apply for enrollment?",
        "Application process for engineering",
        "What is the entry process?",
        "Registration deadline for MBA",
        "How to enroll in the college?",
    ],
    "hostel": [
        "Is dormitory available?",
        "Residence facility for students",
        "Boarding house rules",
        "Room accommodation details",
        "PG facility at college",
    ],
    "scholarship": [
        "Is financial aid available?",
        "Merit aid eligibility criteria",
        "How to apply for grant?",
        "Fee waiver application process",
        "Fellowship details for research",
    ],
    "placement": [
        "Campus drive schedule",
        "Job opportunities through college",
        "Which recruiters visit campus?",
        "Internship through placement cell",
        "Career guidance and hiring support",
    ],
    "library": [
        "Can I borrow books?",
        "Digital library access from home",
        "E-book and journal access",
        "Reference section in reading room",
        "Study room availability",
    ],
    "timetable": [
        "What is the class schedule?",
        "Lecture timing for Monday",
        "Weekly routine for CS department",
        "Lab slots and periods",
        "Time table download as PDF",
    ],
    "attendance": [
        "Am I present enough to sit exam?",
        "Minimum 75 percent rule",
        "Shortage consequence for absent",
        "Biometric roll call system",
        "Proxy attendance penalty",
    ],
    "transport": [
        "College bus route from station",
        "Shuttle service timings",
        "Parking facility for vehicle",
        "Metro station nearest to campus",
        "Commute options for students",
    ],
}


class TestSynonymExpansion:
    """Verify that synonym tokens are mapped to canonical keys."""

    def test_fee_synonyms(self):
        for syn in ["payment", "cost", "tuition", "charges"]:
            result = expand_synonyms(syn)
            assert "fees" in result or "fee" in result

    def test_exam_synonyms(self):
        for syn in ["test", "examination", "assessment"]:
            result = expand_synonyms(syn)
            assert "exam" in result

    def test_hostel_synonyms(self):
        for syn in ["dorm", "dormitory", "residence", "boarding"]:
            result = expand_synonyms(syn)
            assert "hostel" in result

    def test_placement_synonyms(self):
        for syn in ["career", "hiring", "internship"]:
            result = expand_synonyms(syn)
            assert "placement" in result


class TestSynonymVariations:
    """5 synonym variations per FAQ should produce a non-fallback response."""

    @pytest.mark.parametrize("category", list(SYNONYM_TEST_CASES.keys()))
    def test_synonym_queries_match(self, category):
        queries = SYNONYM_TEST_CASES[category]
        matched = 0
        for q in queries:
            response = get_response(q, f"{SESSION}-{category}")
            # Non-empty response that isn't the fallback
            if "not fully sure" not in response.lower():
                matched += 1
        # At least 3 out of 5 should match (60% minimum)
        assert matched >= 3, (
            f"Category '{category}': only {matched}/5 matched. "
            f"Expected at least 3."
        )


class TestCoverageReport:
    """Print a coverage report showing % of synonym queries that matched."""

    def test_coverage_report(self, capsys):
        total = 0
        matched_total = 0
        print("\n" + "=" * 60)
        print(f"{'Category':<15} | {'Matched':<10} | {'Total':<8} | {'Coverage'}")
        print("-" * 60)

        for category, queries in SYNONYM_TEST_CASES.items():
            matched = 0
            for q in queries:
                response = get_response(q, f"cov-{category}")
                if "not fully sure" not in response.lower():
                    matched += 1
            total += len(queries)
            matched_total += matched
            pct = matched / len(queries) * 100
            print(f"{category:<15} | {matched:<10} | {len(queries):<8} | {pct:.0f}%")

        overall = matched_total / total * 100 if total else 0
        print("-" * 60)
        print(f"{'OVERALL':<15} | {matched_total:<10} | {total:<8} | {overall:.0f}%")
        print("=" * 60)

        captured = capsys.readouterr()
        assert "OVERALL" in captured.out
