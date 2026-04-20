"""
FastAPI entrypoint for the College FAQ Chatbot microservice.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Ensure ``PYTHONPATH`` includes the ``backend`` directory.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from app.models import ChatRequest, ChatResponse, HealthResponse

# ──────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("college_faq")

# ──────────────────────────────────────────────────────────────────────
# Attempt to import the real chatbot_core from Member A.
# If the module is not available, fall back to a stub so the API can
# still start and be tested independently.
# ──────────────────────────────────────────────────────────────────────
try:
    from modules.chatbot_core import get_chat_payload  # noqa: F401
    logger.info("Loaded real chatbot_core pipeline.")
    _USING_STUB = False
except ImportError:
    logger.warning("chatbot_core not found — running with STUB responses.")
    _USING_STUB = True

    def get_chat_payload(query: str, session_id: str) -> dict[str, Any]:
        """Stub: return a placeholder response when chatbot_core is absent."""
        return {
            "response": f"[STUB] Echo: {query}",
            "answer": f"[STUB] Echo: {query}",
            "intent": "general",
            "confidence": 0.0,
            "entities": {},
            "suggestions": ["College timings", "Fee details", "Exam dates"],
            "fallback": True,
        }

# ──────────────────────────────────────────────────────────────────────
# Optional analytics import (Task 10)
# ──────────────────────────────────────────────────────────────────────
try:
    from modules.analytics_logger import log_interaction, get_all_interactions
    _HAS_ANALYTICS = True
except ImportError:
    _HAS_ANALYTICS = False
    def get_all_interactions(): return []

# ──────────────────────────────────────────────────────────────────────
# Additional modules (Tasks 8 & 9)
# ──────────────────────────────────────────────────────────────────────
try:
    from modules.fallback_handler import handle_fallback
    from modules.channel_adapter import format_response
except ImportError:
    # Stubs
    def handle_fallback(query, score, top3=None):
        return {"mode": "suggest", "message": "Fallback", "suggestions": [], "query": query, "score": score}
    def format_response(answer, channel):
        return answer

# FastAPI application
# ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="College FAQ Chatbot",
    description="NLP-powered campus FAQ assistant (TF-IDF retrieval + intent classification + entity extraction).",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────
# Root & Favicon (suppress browser 404s)
# ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>College FAQ API</title></head>
<body style="font-family:system-ui,sans-serif;max-width:42rem;margin:2rem auto;line-height:1.5">
  <h1>College FAQ Chatbot API</h1>
  <p>Service is running. Visit <a href="/docs">/docs</a> for Swagger UI,
     or send requests to <code>POST /chat</code>.</p>
  <p><a href="/health">GET /health</a> — readiness check</p>
</body></html>"""
    return HTMLResponse(content=html)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        b'<rect fill="#0f1923" width="32" height="32" rx="6"/>'
        b'<text x="16" y="22" text-anchor="middle" fill="#d4a853" '
        b'font-family="Georgia,serif" font-size="16">C</text></svg>'
    )
    return Response(content=svg, media_type="image/svg+xml")


# ──────────────────────────────────────────────────────────────────────
# GET /health — readiness / liveness probe
# ──────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Return service health status with server timestamp."""
    return HealthResponse(status="ok", timestamp=datetime.utcnow())


# ──────────────────────────────────────────────────────────────────────
# POST /chat — main chat endpoint
# ──────────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(req: ChatRequest) -> ChatResponse:
    """
    Accept a user query and return the bot's answer with metadata.

    Uses the full NLP pipeline (preprocessing → synonym expansion → intent
    classification → TF-IDF retrieval → entity injection → fallback logic).
    """
    try:
        payload = get_chat_payload(req.query, req.session_id)
    except Exception as exc:
        logger.exception("Pipeline error for query=%r", req.query)
        raise HTTPException(status_code=500, detail=f"Internal pipeline error: {exc}") from exc

    score = float(payload.get("confidence", 0.0))
    intent = str(payload.get("intent", "general"))
    answer = str(payload.get("answer") or payload.get("response", ""))
    is_fallback = bool(payload.get("fallback", False))
    suggestions = list(payload.get("suggestions", []))

    # Task 8: Trigger fallback explicitly if confidence is low
    if score < 0.5:
        # We can extract top3 suggestions from payload if present, else empty
        top3_stub = [(s, score) for s in suggestions]
        fallback_data = handle_fallback(req.query, score, top3_stub)
        answer = fallback_data.get("message", answer)
        is_fallback = True

    # Task 9: Format response for web channel
    formatted_answer = format_response(answer, channel="web")

    # Task 10: Analytics logging (fire-and-forget)
    if _HAS_ANALYTICS:
        try:
            log_interaction(
                query=req.query,
                intent=intent,
                score=score,
                answer=answer,
                session_id=req.session_id,
            )
        except Exception:
            logger.warning("Analytics logging failed", exc_info=True)

    return ChatResponse(
        answer=formatted_answer,
        intent=intent,
        score=round(score, 4),
        session_id=req.session_id,
        fallback=is_fallback,
        suggestions=suggestions,
    )


# ──────────────────────────────────────────────────────────────────────
# GET /analytics — fetch logs for UI panel
# ──────────────────────────────────────────────────────────────────────
@app.get("/analytics", tags=["analytics"])
def get_analytics() -> list[dict[str, Any]]:
    """Return the last 100 interaction records from the database."""
    if not _HAS_ANALYTICS:
        return []
    records = get_all_interactions()
    return records[:100]
