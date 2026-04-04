"""
FastAPI entrypoint for the College FAQ chatbot microservice.

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Ensure ``PYTHONPATH`` includes this ``backend`` directory (or run from inside ``backend``).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, model_validator

from modules.chatbot_core import get_chat_payload

app = FastAPI(
    title="College FAQ Chatbot",
    description="NLP-powered campus FAQ assistant (TF-IDF retrieval + intent + entities).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Browsers always request / and /favicon.ico; without routes those show as 404 in DevTools.
@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>College FAQ API</title></head>
<body style="font-family:system-ui,sans-serif;max-width:42rem;margin:2rem auto;line-height:1.5">
  <h1>College FAQ Chatbot API</h1>
  <p>Service is running. Use <a href="/docs">/docs</a> for interactive API (Swagger), or point the CampusBot UI at <code>POST /chat</code>.</p>
  <p><a href="/health">GET /health</a> — readiness check</p>
</body></html>"""
    return HTMLResponse(content=html)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    # Simple SVG tab icon (avoids noisy 404 on automatic favicon fetch)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect fill="#0f1923" width="32" height="32" rx="6"/><text x="16" y="22" text-anchor="middle" fill="#d4a853" font-family="Georgia,serif" font-size="16">S</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


class ChatRequest(BaseModel):
    """Accepts ``query`` (spec) and ``message`` (legacy CampusBot frontend)."""

    model_config = ConfigDict(str_strip_whitespace=False)

    query: str | None = None
    message: str | None = None
    session_id: str = "anonymous"

    @model_validator(mode="after")
    def require_text(self) -> ChatRequest:
        if not (self.query or "").strip() and not (self.message or "").strip():
            raise ValueError("Provide either 'query' or 'message'.")
        if not (self.session_id or "").strip():
            raise ValueError("session_id must be a non-empty string.")
        return self

    def effective_query(self) -> str:
        if (self.query or "").strip():
            return str(self.query).strip()
        return str(self.message).strip()


class ChatResponse(BaseModel):
    """Response mirrors the static SPA contract and adds ``response`` for the brief."""

    response: str
    answer: str
    intent: str
    confidence: float
    entities: dict[str, object]
    suggestions: list[str]
    fallback: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        text = req.effective_query()
        sid = str(req.session_id).strip()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    payload = get_chat_payload(text, sid)
    return ChatResponse(**payload)
