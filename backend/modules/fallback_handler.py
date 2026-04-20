"""
Fallback handler for the College FAQ Chatbot (Task 8).

Decides what to do when the retrieval score is too low to give a confident answer.

Three fallback modes:
  • ``escalate`` — score < 0.2 and no good matches → email + helpdesk link
  • ``clarify``  — score < 0.3 → ask a clarifying question
  • ``suggest``  — 0.3 ≤ score < 0.5 → show top-3 FAQ suggestions

Response formatting uses Jinja2 templates for clean separation of logic / presentation.
"""

from __future__ import annotations

import os
from typing import Any

from jinja2 import Environment, BaseLoader

# ──────────────────────────────────────────────────────────────────────
# Configuration (overridable via env vars)
# ──────────────────────────────────────────────────────────────────────
ADVISOR_EMAIL: str = os.getenv("ADVISOR_EMAIL", "advisor@college.edu")
HELPDESK_URL: str = os.getenv("HELPDESK_URL", "https://helpdesk.college.edu")

# ──────────────────────────────────────────────────────────────────────
# Jinja2 templates for each fallback mode
# ──────────────────────────────────────────────────────────────────────
_TEMPLATES: dict[str, str] = {
    "escalate": (
        "I wasn't able to find a reliable answer to your question.\n\n"
        "Please reach out for personal assistance:\n"
        "  • Email your advisor: mailto:{{ advisor_email }}\n"
        "  • Visit the helpdesk: {{ helpdesk_url }}\n\n"
        "A human advisor will be happy to help!"
    ),
    "clarify": (
        "I'm not quite sure what you're asking about.\n"
        "Could you rephrase your question or add more details?\n\n"
        "For example, try asking about:\n"
        "  • College timings\n"
        "  • Fee payment deadlines\n"
        "  • Exam schedules\n"
        "  • Hostel allotment"
    ),
    "suggest": (
        "I found some FAQs that might be related to your question:\n\n"
        "{% for item in suggestions %}"
        "  {{ loop.index }}. {{ item.text }} (relevance: {{ '%.0f' | format(item.score * 100) }}%)\n"
        "{% endfor %}\n"
        "Try clicking one of the above, or rephrase your question for a better match."
    ),
}

_jinja_env = Environment(loader=BaseLoader(), autoescape=False)


def _render(template_key: str, **context: Any) -> str:
    """Render a Jinja2 template string by key."""
    tmpl = _jinja_env.from_string(_TEMPLATES[template_key])
    return tmpl.render(**context).strip()


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────
def handle_fallback(
    query: str,
    score: float,
    top3_results: list[tuple[str, float]] | None = None,
) -> dict[str, Any]:
    """
    Determine the appropriate fallback action based on retrieval confidence.

    Parameters
    ----------
    query : str
        The user's original question.
    score : float
        Best-match TF-IDF cosine-similarity score (0.0 – 1.0).
    top3_results : list of (faq_text, score) tuples, optional
        Top-3 FAQ matches returned by ``retrieval.get_best_match(query, top_k=3)``.

    Returns
    -------
    dict
        Keys: ``mode`` (str), ``message`` (str), and mode-specific data.
    """
    if top3_results is None:
        top3_results = []

    # ── Mode 1: Escalate (very low confidence, nothing usable) ──
    if score < 0.2 and not _has_reasonable_match(top3_results):
        message = _render(
            "escalate",
            advisor_email=ADVISOR_EMAIL,
            helpdesk_url=HELPDESK_URL,
        )
        return {
            "mode": "escalate",
            "message": message,
            "advisor_email": f"mailto:{ADVISOR_EMAIL}",
            "helpdesk_url": HELPDESK_URL,
            "query": query,
            "score": score,
        }

    # ── Mode 2: Clarify (low confidence) ──
    if score < 0.3:
        message = _render("clarify")
        return {
            "mode": "clarify",
            "message": message,
            "query": query,
            "score": score,
        }

    # ── Mode 3: Suggest (moderate confidence — show top-3) ──
    suggestions = [
        {"text": text, "score": round(s, 4)}
        for text, s in top3_results[:3]
    ]
    message = _render("suggest", suggestions=suggestions)
    return {
        "mode": "suggest",
        "message": message,
        "suggestions": suggestions,
        "query": query,
        "score": score,
    }


def _has_reasonable_match(
    results: list[tuple[str, float]],
    threshold: float = 0.15,
) -> bool:
    """Return True if any result in the list exceeds ``threshold``."""
    return any(s >= threshold for _, s in results)


# ──────────────────────────────────────────────────────────────────────
# Stand-alone demo
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Escalate ===")
    print(handle_fallback("xyzzy gibberish", 0.05, [])["message"])
    print()
    print("=== Clarify ===")
    print(handle_fallback("something about fees?", 0.25, [("Fee details", 0.25)])["message"])
    print()
    print("=== Suggest ===")
    top3 = [("What are the college timings?", 0.42), ("Library hours?", 0.38), ("Hostel rules?", 0.35)]
    print(handle_fallback("when does it open", 0.42, top3)["message"])
