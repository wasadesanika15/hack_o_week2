"""
Tests for TF-IDF retrieval — Task 4.

Covers: matching, threshold fallback, model save/load, query logging.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.preprocessor import preprocess  # noqa: E402
from modules.retrieval import (  # noqa: E402
    FAQRetriever,
    _load_faq_items,
    get_best_match,
    log_query,
)


class TestTfidfRetrieval:
    """Core retrieval functionality."""

    def test_exact_match_high_confidence(self):
        query = preprocess("What are the college timings?")
        result = get_best_match(query)
        assert not result["fallback"]
        assert result["confidence"] > 0.3
        assert "9:00 AM" in result["answer"] or "timings" in result["answer"].lower()

    def test_fee_query_matches(self):
        query = preprocess("fee structure and payment")
        result = get_best_match(query)
        assert not result["fallback"]
        assert "fee" in result["answer"].lower() or "tuition" in result["answer"].lower()

    def test_hostel_query_matches(self):
        query = preprocess("hostel accommodation")
        result = get_best_match(query)
        assert not result["fallback"]
        assert "hostel" in result["answer"].lower()

    def test_gibberish_falls_back(self):
        query = preprocess("xyzzy foobar baz quantum")
        result = get_best_match(query)
        assert result["fallback"]
        assert result["confidence"] < 0.3

    def test_empty_query_falls_back(self):
        result = get_best_match("")
        assert result["fallback"]
        assert result["confidence"] == 0.0

    def test_intent_filtered_matching(self):
        query = preprocess("fee structure and payment online")
        result = get_best_match(query, intent_filter="fees")
        assert not result["fallback"]
        assert result.get("category") == "fees"

    def test_result_keys(self):
        result = get_best_match(preprocess("exam dates"))
        expected_keys = {"answer", "answer_template", "confidence", "matched_question",
                         "matched_id", "category", "fallback"}
        assert expected_keys.issubset(set(result.keys()))


class TestModelPersistence:
    """Save and load TF-IDF model."""

    def test_save_and_load(self, tmp_path):
        items = _load_faq_items()
        retriever = FAQRetriever(items)
        save_path = tmp_path / "test_tfidf.pkl"
        retriever.save(save_path)
        assert save_path.is_file()

        loaded = FAQRetriever.load(save_path)
        # Both should return same answer for same query
        query = preprocess("exam dates")
        r1 = retriever.get_best_match(query)
        r2 = loaded.get_best_match(query)
        assert r1["answer"] == r2["answer"]
        assert abs(r1["confidence"] - r2["confidence"]) < 0.01


class TestQueryLogging:
    """CSV query log."""

    def test_log_creates_csv(self, tmp_path, monkeypatch):
        log_path = tmp_path / "test_log.csv"
        import modules.retrieval as ret_mod
        monkeypatch.setattr(ret_mod, "_LOG_PATH", log_path)

        log_query("test query", "matched faq", 0.85)
        assert log_path.is_file()

        content = log_path.read_text()
        assert "timestamp" in content  # header
        assert "test query" in content
        assert "0.8500" in content

    def test_log_appends(self, tmp_path, monkeypatch):
        log_path = tmp_path / "test_log2.csv"
        import modules.retrieval as ret_mod
        monkeypatch.setattr(ret_mod, "_LOG_PATH", log_path)

        log_query("q1", "faq1", 0.5)
        log_query("q2", "faq2", 0.7)

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
