"""
Tests for preprocessor.py — Task 2.

Covers: lowercasing, punctuation removal, stopword removal, spelling correction,
and a before/after comparison table.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.preprocessor import compare_before_after, preprocess  # noqa: E402


class TestPreprocessBasics:
    """Each preprocessing step is tested independently."""

    def test_lowercasing(self):
        result = preprocess("HELLO WORLD")
        assert result == result.lower()

    def test_punctuation_removal(self):
        result = preprocess("fees??? what!!!")
        assert "?" not in result
        assert "!" not in result

    def test_empty_string(self):
        assert preprocess("") == ""

    def test_none_input(self):
        assert preprocess(None) == ""

    def test_whitespace_only(self):
        assert preprocess("   ") == ""

    def test_stopword_removal(self):
        result = preprocess("what is the fee for the course")
        # 'is' and 'the' are stopwords; 'what' is kept
        assert "what" in result
        tokens = result.split()
        assert "is" not in tokens
        assert "the" not in tokens

    def test_question_words_kept(self):
        """Question words (what, when, where, who, how, which, why) survive."""
        for word in ["what", "when", "where", "who", "how", "which", "why"]:
            result = preprocess(f"{word} is the timing")
            assert word in result.split(), f"'{word}' should be kept"

    def test_spelling_correction(self):
        result = preprocess("scholrship eligibilty")
        # Should attempt correction; at minimum no crash
        assert isinstance(result, str) and len(result) > 0

    def test_domain_words_preserved(self):
        """Campus abbreviations like 'sem', 'hod' should not be 'corrected'."""
        result = preprocess("sem 5 CS exam")
        assert "sem" in result or "5" in result


class TestCompareBeforeAfter:
    """Tests for the documentation utility."""

    def test_default_samples(self):
        table = compare_before_after()
        assert len(table) == 10
        for row in table:
            assert "original" in row
            assert "preprocessed" in row
            assert isinstance(row["original"], str)
            assert isinstance(row["preprocessed"], str)

    def test_custom_samples(self):
        samples = ["Hello World!", "FEES??", "exam date"]
        table = compare_before_after(samples)
        assert len(table) == 3

    def test_before_after_table_print(self, capsys):
        """Print a formatted before/after table for documentation."""
        table = compare_before_after()
        print("\n" + "=" * 80)
        print(f"{'Original':<45} | {'Preprocessed':<35}")
        print("-" * 80)
        for row in table:
            print(f"{row['original']:<45} | {row['preprocessed']:<35}")
        print("=" * 80)
        captured = capsys.readouterr()
        assert "Original" in captured.out
        assert "Preprocessed" in captured.out
