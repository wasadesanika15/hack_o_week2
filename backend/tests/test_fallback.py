"""
Unit tests for fallback_handler.py (Task 8).

Tests all three fallback paths:
  • test_escalate  — score < 0.2, no reasonable matches
  • test_clarify   — score >= 0.2 but < 0.3
  • test_suggest   — score >= 0.3 but < 0.5, with top-3 results
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure modules are importable regardless of working directory
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.fallback_handler import handle_fallback


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────
@pytest.fixture
def top3_weak() -> list[tuple[str, float]]:
    """Top-3 results where none exceeds the reasonable-match threshold (0.15)."""
    return [
        ("Is the campus open on weekends?", 0.10),
        ("What is the dress code?", 0.08),
        ("Where is parking?", 0.05),
    ]


@pytest.fixture
def top3_moderate() -> list[tuple[str, float]]:
    """Top-3 results with moderate relevance scores."""
    return [
        ("What are the college timings?", 0.42),
        ("What are the library hours?", 0.38),
        ("When does the canteen open?", 0.35),
    ]


# ──────────────────────────────────────────────────────────────────────
# 1. ESCALATE — score < 0.2, no good matches
# ──────────────────────────────────────────────────────────────────────
class TestEscalate:
    def test_mode_is_escalate(self, top3_weak):
        result = handle_fallback("zzz random noise", 0.05, top3_weak)
        assert result["mode"] == "escalate"

    def test_contains_email_link(self, top3_weak):
        result = handle_fallback("gibberish", 0.05, top3_weak)
        assert "mailto:" in result["advisor_email"]
        assert "advisor" in result["advisor_email"]

    def test_contains_helpdesk_url(self, top3_weak):
        result = handle_fallback("gibberish", 0.05, top3_weak)
        assert result["helpdesk_url"].startswith("http")

    def test_message_mentions_advisor(self, top3_weak):
        result = handle_fallback("xyzzy", 0.05, top3_weak)
        assert "advisor" in result["message"].lower()

    def test_message_mentions_helpdesk(self, top3_weak):
        result = handle_fallback("abc123", 0.05, top3_weak)
        assert "helpdesk" in result["message"].lower()

    def test_escalate_empty_results(self):
        result = handle_fallback("nothing", 0.0, [])
        assert result["mode"] == "escalate"

    def test_score_preserved(self, top3_weak):
        result = handle_fallback("test", 0.12, top3_weak)
        assert result["score"] == 0.12


# ──────────────────────────────────────────────────────────────────────
# 2. CLARIFY — score < 0.3
# ──────────────────────────────────────────────────────────────────────
class TestClarify:
    def test_mode_is_clarify(self):
        result = handle_fallback("something about fees?", 0.25, [("Fee info", 0.25)])
        assert result["mode"] == "clarify"

    def test_message_asks_to_rephrase(self):
        result = handle_fallback("fees maybe", 0.22, [("Fee details", 0.22)])
        msg = result["message"].lower()
        assert "rephrase" in msg or "details" in msg

    def test_clarify_at_boundary(self):
        """Score exactly at 0.2 with a reasonable match should clarify, not escalate."""
        result = handle_fallback("hmm", 0.2, [("Some FAQ", 0.2)])
        assert result["mode"] == "clarify"

    def test_clarify_just_below_suggest(self):
        """Score at 0.29 is clarify, not suggest."""
        result = handle_fallback("test", 0.29, [("FAQ", 0.29)])
        assert result["mode"] == "clarify"

    def test_query_preserved(self):
        result = handle_fallback("my_query", 0.28, [])
        assert result["query"] == "my_query"


# ──────────────────────────────────────────────────────────────────────
# 3. SUGGEST — 0.3 ≤ score < 0.5
# ──────────────────────────────────────────────────────────────────────
class TestSuggest:
    def test_mode_is_suggest(self, top3_moderate):
        result = handle_fallback("when open", 0.42, top3_moderate)
        assert result["mode"] == "suggest"

    def test_has_suggestions_list(self, top3_moderate):
        result = handle_fallback("when open", 0.42, top3_moderate)
        assert "suggestions" in result
        assert len(result["suggestions"]) == 3

    def test_suggestions_have_text_and_score(self, top3_moderate):
        result = handle_fallback("when open", 0.42, top3_moderate)
        for s in result["suggestions"]:
            assert "text" in s
            assert "score" in s
            assert isinstance(s["score"], float)

    def test_message_contains_faq_text(self, top3_moderate):
        result = handle_fallback("when open", 0.42, top3_moderate)
        assert "college timings" in result["message"].lower()

    def test_suggest_at_lower_boundary(self, top3_moderate):
        """Score exactly at 0.3 = suggest."""
        result = handle_fallback("test", 0.30, top3_moderate)
        assert result["mode"] == "suggest"

    def test_suggest_at_upper_boundary(self, top3_moderate):
        """Score just below 0.5 = still suggest."""
        result = handle_fallback("test", 0.49, top3_moderate)
        assert result["mode"] == "suggest"

    def test_limits_to_three_suggestions(self):
        five = [(f"FAQ {i}", 0.3 + i * 0.01) for i in range(5)]
        result = handle_fallback("test", 0.35, five)
        assert len(result["suggestions"]) <= 3


# ──────────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_none_top3_defaults_to_empty(self):
        """Passing None for top3_results should not crash."""
        result = handle_fallback("test", 0.05, None)
        assert result["mode"] == "escalate"

    def test_high_score_above_suggest_range(self, top3_moderate):
        """Score >= 0.5 still returns 'suggest' (not a confident match handler)."""
        result = handle_fallback("test", 0.65, top3_moderate)
        # The handler is only called for low scores; above 0.5 still returns suggest mode
        assert result["mode"] == "suggest"

    def test_return_type(self, top3_moderate):
        result = handle_fallback("test", 0.4, top3_moderate)
        assert isinstance(result, dict)
        assert "mode" in result
        assert "message" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
