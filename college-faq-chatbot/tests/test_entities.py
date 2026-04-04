"""
Tests for entity extraction — Task 6.

10 queries with expected entity output per the spec.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.entity_extractor import extract_entities  # noqa: E402

# 10 queries with expected entities
ENTITY_TEST_CASES = [
    {
        "query": "SEM 5 CS exam date",
        "expected": {"semester": 5, "department": "CS"},
    },
    {
        "query": "What is the fee for semester 3 IT",
        "expected": {"semester": 3, "department": "IT"},
    },
    {
        "query": "CS301 course timetable",
        "expected": {"course_code": "CS301", "department": "CS"},
    },
    {
        "query": "ME-501 practical exam on 15/11/2024",
        "expected": {"course_code": "ME501", "department": "ME", "dates": ["2024-11-15"]},
    },
    {
        "query": "third year EC placement",
        "expected": {"year": 3, "department": "EC"},
    },
    {
        "query": "FY hostel allotment",
        "expected": {"year": 1},
    },
    {
        "query": "2nd semester MBA fee structure",
        "expected": {"semester": 2, "department": "MBA"},
    },
    {
        "query": "exam on 2024-05-20 for EE",
        "expected": {"department": "EE", "dates": ["2024-05-20"]},
    },
    {
        "query": "4th year final exam schedule",
        "expected": {"year": 4},
    },
    {
        "query": "15 Nov 2024 IT402 exam",
        "expected": {"course_code": "IT402", "department": "IT", "dates": ["2024-11-15"]},
    },
]


class TestEntityExtraction:
    """Each of the 10 spec queries produces correct entities."""

    @pytest.mark.parametrize(
        "case",
        ENTITY_TEST_CASES,
        ids=[c["query"][:30] for c in ENTITY_TEST_CASES],
    )
    def test_entity_case(self, case):
        result = extract_entities(case["query"])
        for key, expected_value in case["expected"].items():
            assert key in result, (
                f"Missing entity '{key}' in result {result} for query: {case['query']}"
            )
            assert result[key] == expected_value, (
                f"Entity '{key}': expected {expected_value}, got {result[key]} "
                f"for query: {case['query']}"
            )


class TestEntityEdgeCases:
    """Edge cases and empty inputs."""

    def test_empty_string(self):
        assert extract_entities("") == {}

    def test_no_entities(self):
        result = extract_entities("hello how are you")
        # Might have empty or only general keys
        assert "semester" not in result
        assert "department" not in result
        assert "course_code" not in result

    def test_multiple_date_formats(self):
        result = extract_entities("exam on 20/05/2024")
        assert "dates" in result
        assert "2024-05-20" in result["dates"]

    def test_iso_date_format(self):
        result = extract_entities("deadline is 2024-12-31")
        assert "dates" in result
        assert "2024-12-31" in result["dates"]

    def test_named_month_date(self):
        result = extract_entities("exam on 25 December 2024")
        assert "dates" in result
        assert "2024-12-25" in result["dates"]

    def test_department_case_insensitive(self):
        result = extract_entities("cs department")
        assert result.get("department") == "CS"

    def test_semester_variations(self):
        assert extract_entities("semester 7")["semester"] == 7
        assert extract_entities("sem 3")["semester"] == 3
        assert extract_entities("5th semester")["semester"] == 5

    def test_year_word_variations(self):
        assert extract_entities("first year")["year"] == 1
        assert extract_entities("second year")["year"] == 2
        assert extract_entities("SY student")["year"] == 2


class TestEntityOutputTable:
    """Print a formatted table of entity extraction results."""

    def test_print_entity_table(self, capsys):
        print("\n" + "=" * 80)
        print(f"{'Query':<40} | {'Extracted Entities'}")
        print("-" * 80)
        for case in ENTITY_TEST_CASES:
            result = extract_entities(case["query"])
            print(f"{case['query']:<40} | {result}")
        print("=" * 80)
        captured = capsys.readouterr()
        assert "Extracted Entities" in captured.out
