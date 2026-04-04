"""
Text preprocessing: normalize, remove noise, optional spelling correction.

Exports a single pure function: ``preprocess(text) -> str``.
No globals, no CLI entry point — imported by retrieval, intent classifier, and entity extractor.
"""

from __future__ import annotations

import json
import re
import string
from functools import lru_cache
from pathlib import Path
from typing import Any

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from spellchecker import SpellChecker

# ---------------------------------------------------------------------------
# Lazy NLTK data so first import does not fail offline if bundles exist
# ---------------------------------------------------------------------------
_NLTK_READY = False


def _ensure_nltk() -> None:
    global _NLTK_READY
    if _NLTK_READY:
        return
    for path, name in (
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
    ):
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(name, quiet=True)
    _NLTK_READY = True


_spell = SpellChecker(distance=1)


def _project_root() -> Path:
    # backend/modules/preprocessor.py → college-faq-chatbot
    return Path(__file__).resolve().parent.parent.parent


@lru_cache(maxsize=1)
def _domain_words() -> set[str]:
    """College-specific tokens to avoid 'correcting' valid abbreviations."""
    data_dir = _project_root() / "data"
    words: set[str] = set()
    for name in ("faq_data.json", "synonyms.json", "intents.json"):
        path = data_dir / name
        if not path.is_file():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(blob, list):
            for item in blob:
                if isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            words.update(w.lower() for w in re.findall(r"\w+", v))
        elif isinstance(blob, dict):
            for v in blob.values():
                if isinstance(v, list):
                    for phrase in v:
                        if isinstance(phrase, str):
                            words.update(w.lower() for w in re.findall(r"\w+", phrase))
    # common campus abbreviations
    words.update(
        [
            "btech", "mtech", "mba", "sem", "hod", "cs", "it", "me", "ce",
            "ec", "ee", "faq", "campus", "nst", "online", "pdf", "mca",
            "aiml", "aids", "eee", "fy", "sy", "ty", "bsc", "msc",
        ]
    )
    return words


def _correct_token(token: str) -> str:
    if len(token) <= 2 or token in _domain_words():
        return token
    if token in _spell:
        return token
    suggestion = _spell.correction(token)
    return suggestion if suggestion else token


def preprocess(text: str) -> str:
    """
    Normalize user or FAQ text for retrieval and intent models.

    Steps: lowercase → strip punctuation → tokenize → remove stopwords
    → light spelling correction → rejoin.
    """
    _ensure_nltk()
    if not text or not str(text).strip():
        return ""

    lowered = str(text).lower()
    # Keep alphanumeric chunks; turn other punctuation into space
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    tokens = word_tokenize(cleaned)
    stop = set(stopwords.words("english"))
    # Keep question-like tokens that may carry intent
    keep = {"what", "when", "where", "who", "how", "which", "why"}
    stop -= keep
    
    # Add domain-inspecific words as extra stopwords so they don't skew TF-IDF matching
    stop.update({"college", "university", "institute", "campus"})

    out: list[str] = []
    for raw in tokens:
        if raw in string.punctuation:
            continue
        if raw in stop:
            continue
        if not raw.strip():
            continue
        fixed = _correct_token(raw)
        if fixed:
            out.append(fixed)
    return " ".join(out)


def compare_before_after(samples: list[str] | None = None) -> list[dict[str, str]]:
    """
    Return a list of ``{original, preprocessed}`` dicts for documentation.

    If *samples* is ``None``, uses a default set of 10 representative queries.
    """
    if samples is None:
        samples = [
            "What are the college timings?",
            "How do I PAY my FEES online???",
            "when is the next semester exam!!",
            "hostel allotment process plz help",
            "tell me abt scholrship eligibilty",
            "CS301 exam date for SEM 5",
            "is there a bus from raipur?",
            "library timing on saturday",
            "who is the HOD of IT dept",
            "Can I get attendance exemption for medical leave?",
        ]
    return [{"original": s, "preprocessed": preprocess(s)} for s in samples]
