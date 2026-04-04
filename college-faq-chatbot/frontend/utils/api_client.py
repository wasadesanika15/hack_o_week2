"""Tiny HTTP helper for calling the FastAPI ``/chat`` endpoint (Streamlit or scripts)."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE = os.environ.get("CHATBOT_API_BASE", "http://127.0.0.1:8000")


def send_chat(
    message: str,
    session_id: str,
    *,
    base_url: str = DEFAULT_BASE,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """POST JSON body using ``message`` key (CampusBot-compatible)."""
    url = f"{base_url.rstrip('/')}/chat"
    payload = {"message": message, "session_id": session_id}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()
