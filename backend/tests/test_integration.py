"""
Integration tests for the overall College FAQ Chatbot backend.

Verifies:
 - The app starts and `/health` works
 - `/chat` works with normal queries
 - `/chat` triggers fallback appropriately
 - `/analytics` endpoint works
"""

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# Ensure backend directory is in path
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.main import app

client = TestClient(app)

def test_health_check():
    """Verify that the health check endpoint returns 200 OK and status 'ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data

def test_chat_valid_query():
    """Verify that a standard query returns an answer, intent, and score."""
    response = client.post(
        "/chat",
        json={"query": "What are the college timings?", "session_id": "test-session-123"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Depending on if it's the stub or real module, the score and intent
    # might be different. Let's just check the structure.
    assert "answer" in data
    assert "intent" in data
    assert "score" in data
    assert "fallback" in data

def test_chat_fallback_trigger():
    """Verify that an ambiguous query triggers fallback mode and sets fallback true."""
    # We can pass an empty string or random gibberish to trigger it
    response = client.post(
        "/chat",
        json={"query": "asdfjkl random noise", "session_id": "test-session-124"}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["fallback"] is True
    assert "answer" in data
    # Fallback should be modifying the answer to have links or helpdesk text, or clarification

def test_analytics_endpoint():
    """Verify that analytics endpoint returns a list of interactions."""
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "timestamp" in data[0]
        assert "query" in data[0]
        assert "score" in data[0]
