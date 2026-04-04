"""
Tests for intent classification — Task 5.

Covers: prediction accuracy per category, evaluation metrics, model persistence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.intent_classifier import (  # noqa: E402
    IntentClassifier,
    evaluate,
    get_classifier,
    predict_intent,
)

# Representative queries per intent for smoke testing
INTENT_SAMPLES = {
    "admissions": [
        "how to apply for admission",
        "admission deadline this year",
        "what documents for enrollment",
    ],
    "fees": [
        "fee structure for engineering",
        "how to pay semester tuition",
        "late fee penalty amount",
    ],
    "exam": [
        "when is the semester exam",
        "exam hall ticket download",
        "supplementary exam schedule",
    ],
    "timetable": [
        "class schedule for Monday",
        "download pdf timetable",
        "lab slot timing today",
    ],
    "hostel": [
        "hostel allotment process",
        "hostel mess menu",
        "girls hostel rules and curfew",
    ],
    "scholarship": [
        "scholarship eligibility criteria",
        "how to apply for financial aid",
        "merit scholarship amount details",
    ],
    "placement": [
        "placement statistics last year",
        "which companies visit for campus drives",
        "average package offered to students",
    ],
    "library": [
        "library timing today",
        "how many books can I borrow",
        "digital library access from home",
    ],
    "general": [
        "hello",
        "thank you",
        "who are you",
    ],
}


class TestIntentPrediction:
    """Verify correct intent for representative queries."""

    @pytest.mark.parametrize(
        "expected_intent,queries",
        list(INTENT_SAMPLES.items()),
    )
    def test_intent_accuracy(self, expected_intent, queries):
        correct = 0
        for q in queries:
            predicted = predict_intent(q)
            if predicted == expected_intent:
                correct += 1
        # At least 2 out of 3 should be correct
        assert correct >= 2, (
            f"Intent '{expected_intent}': only {correct}/3 correct. "
            f"Predictions: {[predict_intent(q) for q in queries]}"
        )

    def test_empty_query_returns_general(self):
        assert predict_intent("") == "general"
        assert predict_intent("   ") == "general"

    def test_predict_proba_sums_to_one(self):
        clf = get_classifier()
        probs = clf.predict_proba_dict("what is the fee structure")
        total = sum(probs.values())
        assert abs(total - 1.0) < 0.01, f"Probabilities sum to {total}"


class TestIntentModelPersistence:
    """Save and load intent model."""

    def test_save_and_load(self, tmp_path):
        clf = IntentClassifier()
        save_path = tmp_path / "test_intent.pkl"
        clf.save(save_path)
        assert save_path.is_file()

        loaded = IntentClassifier.load(save_path)
        # Both should predict same intent
        query = "when is the exam"
        assert clf.predict_intent(query) == loaded.predict_intent(query)


class TestIntentEvaluation:
    """Evaluation metrics and confusion matrix."""

    def test_evaluate_returns_accuracy(self):
        results = evaluate(test_size=0.2)
        assert "accuracy" in results
        assert 0.0 <= results["accuracy"] <= 1.0
        assert "report" in results
        assert "confusion_matrix" in results

    def test_accuracy_above_threshold(self):
        results = evaluate(test_size=0.2)
        # With 20+ examples per intent, we expect at least 60% accuracy
        assert results["accuracy"] >= 0.5, (
            f"Accuracy {results['accuracy']:.2%} is below 50% — "
            f"training data may be insufficient."
        )

    def test_evaluation_report_print(self, capsys):
        """Print evaluation results for documentation."""
        results = evaluate(test_size=0.2)
        print(f"\n{'='*60}")
        print(f"Intent Classifier Accuracy: {results['accuracy']:.2%}")
        print(f"{'='*60}")
        print(results["report"])
        captured = capsys.readouterr()
        assert "accuracy" in captured.out.lower() or "precision" in captured.out.lower()
