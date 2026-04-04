#!/usr/bin/env python3
"""
Train and save all ML models for the College FAQ Chatbot.

Produces:
    models/tfidf_model.pkl   — TF-IDF vectorizer + FAQ matrix
    models/intent_model.pkl  — Intent classifier (LogisticRegression pipeline)
    models/confusion_matrix.png — Visual evaluation of intent classifier

Usage:
    python train_models.py
"""

import sys
from pathlib import Path

# Ensure backend modules are importable
_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def main() -> None:
    print("=" * 60)
    print("  College FAQ Chatbot — Model Training")
    print("=" * 60)
    print()

    # --- TF-IDF Retrieval Model ---
    print("[1/3] Training TF-IDF retrieval model...")
    from modules.retrieval import train as train_retrieval

    tfidf_path = train_retrieval()
    print(f"      ✅ Saved to: {tfidf_path}")
    print()

    # --- Intent Classifier ---
    print("[2/3] Training intent classifier...")
    from modules.intent_classifier import train as train_intent

    intent_path = train_intent()
    print(f"      ✅ Saved to: {intent_path}")
    print()

    # --- Evaluation ---
    print("[3/3] Evaluating intent classifier...")
    from modules.intent_classifier import evaluate

    results = evaluate(test_size=0.2)
    print(f"      Accuracy: {results['accuracy']:.2%}")
    print()
    print("      Classification Report:")
    for line in results["report"].strip().split("\n"):
        print(f"      {line}")
    print()
    if results.get("image_path"):
        print(f"      📊 Confusion matrix saved: {results['image_path']}")
    else:
        print("      ⚠️  matplotlib not installed — confusion matrix image skipped")

    print()
    print("=" * 60)
    print("  All models trained and saved successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
