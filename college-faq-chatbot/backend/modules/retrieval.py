"""
TF-IDF + cosine similarity retrieval over FAQ questions.

Supports model persistence via joblib and query logging to CSV.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import joblib
except ImportError:
    import pickle as joblib  # type: ignore[no-redef]

from .preprocessor import preprocess

# Default aligns with legacy monolithic chatbot threshold but tightened for precision
DEFAULT_CONFIDENCE_THRESHOLD = 0.35

FALLBACK_MESSAGE = (
    "I'm not fully sure which topic you mean. Try asking about timings, fees, "
    "exam dates, admissions, scholarships, hostel, contacts, holidays, "
    "placement, or departments — or rephrase with a few clear keywords."
)


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


def _model_dir() -> Path:
    d = _data_dir().parent / "models"
    d.mkdir(exist_ok=True)
    return d


class FAQRetriever:
    """Fit-once TF-IDF index over preprocessed FAQ questions."""

    def __init__(
        self,
        faq_items: list[dict[str, Any]],
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self.threshold = threshold
        self._questions: list[str] = []
        self._answers: list[str] = []
        self._answer_templates: list[str] = []
        self._categories: list[str] = []
        self._raw_questions: list[str] = []
        self._ids: list[str] = []

        for row in faq_items:
            q = row.get("question", "")
            a = row.get("answer", "")
            tmpl = row.get("answer_template", a)
            cat = row.get("category", "general")
            faq_id = row.get("id", "")
            self._raw_questions.append(q)
            self._questions.append(q)
            self._answers.append(a)
            self._answer_templates.append(tmpl)
            self._categories.append(cat)
            self._ids.append(faq_id)

        processed = [preprocess(q) for q in self._questions]
        self._vectorizer = TfidfVectorizer()
        self._matrix = self._vectorizer.fit_transform(processed)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: Path | str | None = None) -> Path:
        """Persist vectorizer + matrix + metadata to a joblib file."""
        if path is None:
            path = _model_dir() / "tfidf_model.pkl"
        path = Path(path)
        data = {
            "vectorizer": self._vectorizer,
            "matrix": self._matrix,
            "questions": self._questions,
            "raw_questions": self._raw_questions,
            "answers": self._answers,
            "answer_templates": self._answer_templates,
            "categories": self._categories,
            "ids": self._ids,
            "threshold": self.threshold,
        }
        joblib.dump(data, path)
        return path

    @classmethod
    def load(cls, path: Path | str | None = None) -> "FAQRetriever":
        """Load a previously saved model (skips re-training)."""
        if path is None:
            path = _model_dir() / "tfidf_model.pkl"
        path = Path(path)
        data = joblib.load(path)
        obj = cls.__new__(cls)
        obj._vectorizer = data["vectorizer"]
        obj._matrix = data["matrix"]
        obj._questions = data["questions"]
        obj._raw_questions = data["raw_questions"]
        obj._answers = data["answers"]
        obj._answer_templates = data.get("answer_templates", data["answers"])
        obj._categories = data.get("categories", ["general"] * len(data["answers"]))
        obj._ids = data.get("ids", [""] * len(data["answers"]))
        obj.threshold = data.get("threshold", DEFAULT_CONFIDENCE_THRESHOLD)
        return obj

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def get_best_match(
        self,
        processed_query: str,
        intent_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Return best FAQ answer for a *preprocessed* query string.

        If *intent_filter* is given AND there are FAQs in that category, restrict
        candidates to that category. Falls back to full corpus if nothing matches.
        """
        pq = (processed_query or "").strip()
        if not pq:
            return {
                "answer": FALLBACK_MESSAGE,
                "answer_template": FALLBACK_MESSAGE,
                "confidence": 0.0,
                "matched_question": None,
                "matched_id": None,
                "category": None,
                "fallback": True,
            }

        vec = self._vectorizer.transform([pq])
        sims = cosine_similarity(vec, self._matrix)[0]

        # Intent-filtered ranking
        if intent_filter and intent_filter != "general":
            cat_indices = [
                i for i, c in enumerate(self._categories) if c == intent_filter
            ]
            if cat_indices:
                cat_best_idx = max(cat_indices, key=lambda i: sims[i])
                cat_best_score = float(sims[cat_best_idx])
                if cat_best_score >= self.threshold:
                    return self._build_result(cat_best_idx, cat_best_score)

        # Full corpus fallback
        idx = int(np.argmax(sims))
        score = float(sims[idx])

        if score < self.threshold:
            return {
                "answer": FALLBACK_MESSAGE,
                "answer_template": FALLBACK_MESSAGE,
                "confidence": score,
                "matched_question": None,
                "matched_id": None,
                "category": None,
                "fallback": True,
            }

        return self._build_result(idx, score)

    def _build_result(self, idx: int, score: float) -> dict[str, Any]:
        return {
            "answer": self._answers[idx],
            "answer_template": self._answer_templates[idx],
            "confidence": score,
            "matched_question": self._raw_questions[idx],
            "matched_id": self._ids[idx],
            "category": self._categories[idx],
            "fallback": False,
        }


# ======================================================================
# Module-level singleton
# ======================================================================
_retriever: FAQRetriever | None = None


def _load_faq_items() -> list[dict[str, Any]]:
    path = _data_dir() / "faq_data.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("faq_data.json must be a list of objects")
    return data


def get_retriever(threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> FAQRetriever:
    global _retriever
    if _retriever is None:
        model_path = _model_dir() / "tfidf_model.pkl"
        if model_path.is_file():
            _retriever = FAQRetriever.load(model_path)
        else:
            _retriever = FAQRetriever(_load_faq_items(), threshold=threshold)
            _retriever.save(model_path)
    return _retriever


def get_best_match(
    query: str,
    intent_filter: str | None = None,
) -> dict[str, Any]:
    """
    Public API: *query* must already be normalized (preprocess + synonym expansion).
    """
    return get_retriever().get_best_match(query, intent_filter=intent_filter)


# ======================================================================
# Query logging (CSV append — no database)
# ======================================================================
_LOG_PATH = _data_dir() / "query_log.csv"


def log_query(query: str, matched_faq: str | None, score: float) -> None:
    """Append a ``(timestamp, query, matched_faq, score)`` row to the CSV log."""
    write_header = not _LOG_PATH.is_file()
    with _LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "query", "matched_faq", "score"])
        writer.writerow([datetime.now().isoformat(), query, matched_faq or "", f"{score:.4f}"])


def train(threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> Path:
    """Force retrain from FAQ data and save the model."""
    global _retriever
    items = _load_faq_items()
    _retriever = FAQRetriever(items, threshold=threshold)
    return _retriever.save()
