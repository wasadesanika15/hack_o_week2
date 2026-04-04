"""
Intent classification with scikit-learn (LogisticRegression + TF-IDF).

Supports training, prediction, model persistence, and evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

try:
    import joblib
except ImportError:
    import pickle as joblib  # type: ignore[no-redef]

from .preprocessor import preprocess

_INTENT_ORDER = (
    "admissions",
    "fees",
    "exam",
    "timetable",
    "hostel",
    "scholarship",
    "placement",
    "library",
    "attendance",
    "transport",
    "general",
)


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


def _model_dir() -> Path:
    d = _data_dir().parent / "models"
    d.mkdir(exist_ok=True)
    return d


def _build_training(intents_blob: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []
    for label in _INTENT_ORDER:
        phrases = intents_blob.get(label, [])
        for p in phrases:
            processed = preprocess(str(p))
            if processed.strip():
                texts.append(processed)
                labels.append(label)
    # Also accept any extra intents not in _INTENT_ORDER
    for label, phrases in intents_blob.items():
        if label not in _INTENT_ORDER:
            for p in phrases:
                processed = preprocess(str(p))
                if processed.strip():
                    texts.append(processed)
                    labels.append(label)
    return texts, labels


class IntentClassifier:
    """Small TF-IDF + logistic model trained on ``data/intents.json``."""

    def __init__(self, pipeline: Pipeline | None = None) -> None:
        if pipeline is not None:
            self._pipeline = pipeline
            self._classes: list[str] = list(pipeline.classes_)
            return

        path = _data_dir() / "intents.json"
        blob = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(blob, dict):
            raise ValueError("intents.json must be an object mapping intent -> phrases")
        X, y = _build_training(blob)
        self._pipeline: Pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                (
                    "clf",
                    LogisticRegression(max_iter=1000, class_weight="balanced"),
                ),
            ]
        )
        self._pipeline.fit(X, y)
        self._classes = list(self._pipeline.classes_)

    def predict_intent(self, query: str) -> str:
        """Return intent label for the raw user query."""
        x = preprocess(query or "")
        if not x.strip():
            return "general"
        label = self._pipeline.predict([x])[0]
        return str(label)

    def predict_proba_dict(self, query: str) -> dict[str, float]:
        """Probability mass per intent (handy for analytics / future routing)."""
        x = preprocess(query or "")
        if not x.strip():
            return {c: 1.0 / len(self._classes) for c in self._classes}
        probs = self._pipeline.predict_proba([x])[0]
        return {str(c): float(p) for c, p in zip(self._classes, probs)}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: Path | str | None = None) -> Path:
        if path is None:
            path = _model_dir() / "intent_model.pkl"
        path = Path(path)
        joblib.dump(self._pipeline, path)
        return path

    @classmethod
    def load(cls, path: Path | str | None = None) -> "IntentClassifier":
        if path is None:
            path = _model_dir() / "intent_model.pkl"
        path = Path(path)
        pipeline = joblib.load(path)
        return cls(pipeline=pipeline)


# ======================================================================
# Evaluation
# ======================================================================

def evaluate(test_size: float = 0.2) -> dict[str, Any]:
    """
    Train/test split evaluation. Returns accuracy, report, and confusion matrix.

    Optionally saves confusion matrix to ``models/confusion_matrix.png``.
    """
    path = _data_dir() / "intents.json"
    blob = json.loads(path.read_text(encoding="utf-8"))
    X, y = _build_training(blob)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=sorted(set(y)))

    # Try to save confusion matrix image
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 8))
        labels_sorted = sorted(set(y))
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.set_xticks(range(len(labels_sorted)))
        ax.set_yticks(range(len(labels_sorted)))
        ax.set_xticklabels(labels_sorted, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(labels_sorted, fontsize=8)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title(f"Intent Confusion Matrix (accuracy={acc:.2%})")
        fig.colorbar(im, ax=ax)

        # Add text annotations
        for i in range(len(labels_sorted)):
            for j in range(len(labels_sorted)):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black",
                        fontsize=7)

        fig.tight_layout()
        out_path = _model_dir() / "confusion_matrix.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
    except ImportError:
        out_path = None

    return {
        "accuracy": acc,
        "report": report,
        "confusion_matrix": cm.tolist(),
        "image_path": str(out_path) if out_path else None,
    }


# ======================================================================
# Module-level singleton
# ======================================================================
_classifier: IntentClassifier | None = None


def get_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        model_path = _model_dir() / "intent_model.pkl"
        if model_path.is_file():
            _classifier = IntentClassifier.load(model_path)
        else:
            _classifier = IntentClassifier()
            _classifier.save(model_path)
    return _classifier


def predict_intent(query: str) -> str:
    return get_classifier().predict_intent(query)


def train() -> Path:
    """Force retrain from intents.json and save the model."""
    global _classifier
    _classifier = IntentClassifier()
    return _classifier.save()
