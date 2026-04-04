"""
Smoke and contract tests for the FAQ chatbot service.

Updated to cover the enriched pipeline (Tasks 1-7).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from modules.chatbot_core import get_chat_payload, get_response  # noqa: E402
from modules.entity_extractor import extract_entities  # noqa: E402
from modules.preprocessor import preprocess  # noqa: E402

client = TestClient(app)


# ===========================================================================
# Health & root
# ===========================================================================

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_returns_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "College FAQ" in r.text


# ===========================================================================
# POST /chat
# ===========================================================================

def test_chat_accepts_query_key():
    r = client.post(
        "/chat",
        json={"query": "What are the college timings?", "session_id": "t1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "response" in body and "answer" in body
    assert body["response"] == body["answer"]
    assert body["intent"]
    assert "confidence" in body
    assert isinstance(body["entities"], dict)
    assert isinstance(body["suggestions"], list)
    assert isinstance(body["fallback"], bool)


def test_chat_accepts_message_key_legacy_frontend():
    r = client.post(
        "/chat",
        json={"message": "Tell me about hostel facilities", "session_id": "t2"},
    )
    assert r.status_code == 200
    assert "hostel" in r.json()["response"].lower()


def test_chat_requires_payload():
    r = client.post("/chat", json={"session_id": "only-session"})
    assert r.status_code == 422


# ===========================================================================
# get_response — the primary handoff function
# ===========================================================================

def test_get_response_string_api():
    text = get_response("What is the fee structure?", "sess-x")
    assert isinstance(text, str) and len(text) > 10


def test_get_response_signature():
    """Ensure the function signature matches the spec."""
    import inspect

    sig = inspect.signature(get_response)
    params = list(sig.parameters.keys())
    assert params == ["query", "session_id"]


# ===========================================================================
# Entity extraction
# ===========================================================================

def test_entities_sem_department():
    e = extract_entities("SEM 5 CS exam date")
    assert e.get("semester") == 5
    assert e.get("department") == "CS"


# ===========================================================================
# Preprocessor
# ===========================================================================

def test_preprocess_normalizes():
    out = preprocess("What are the FEES for 2026?")
    assert "fee" in out or "2026" in out


# ===========================================================================
# Session context
# ===========================================================================

def test_session_context_merges_entities():
    get_chat_payload("SEM 3 CS timetable", "merge-test")
    second = get_chat_payload("When is the exam?", "merge-test")
    assert (
        second["entities"].get("semester") == 3
        or second["entities"].get("department") == "CS"
    )


# ===========================================================================
# 10 sample questions (README requirement)
# ===========================================================================

SAMPLE_QUESTIONS = [
    "What are the college timings?",
    "How do I pay my fees online?",
    "When are the semester exams?",
    "How can I apply for admission?",
    "Are there any scholarships available?",
    "Does the college have a hostel?",
    "How do I contact the IT department?",
    "What is the minimum attendance requirement?",
    "Where can I find my class timetable?",
    "What are the placement opportunities?",
]


@pytest.mark.parametrize("question", SAMPLE_QUESTIONS)
def test_sample_question_gets_answer(question):
    response = get_response(question, "sample-test")
    assert isinstance(response, str)
    assert len(response) > 10
    assert "not fully sure" not in response.lower(), (
        f"Fallback triggered for: {question}"
    )
