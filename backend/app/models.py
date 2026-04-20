"""
Pydantic v2 request / response schemas for the College FAQ Chatbot API.

These models enforce input validation and provide automatic OpenAPI docs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ──────────────────────────────────────────────────────────────────────
# Request
# ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """
    Incoming chat payload.

    - ``query`` is the primary text field.
    - ``session_id`` identifies the user's conversation session.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's natural-language question.",
        examples=["What are the college timings?"],
    )
    session_id: str = Field(
        default="anonymous",
        min_length=1,
        max_length=128,
        description="Unique session identifier for context tracking.",
        examples=["sess-abc123"],
    )

    @model_validator(mode="after")
    def validate_non_empty(self) -> ChatRequest:
        """Ensure query is not blank after stripping whitespace."""
        if not self.query.strip():
            raise ValueError("query must contain at least one non-whitespace character.")
        return self


# ──────────────────────────────────────────────────────────────────────
# Response
# ──────────────────────────────────────────────────────────────────────
class ChatResponse(BaseModel):
    """
    Structured bot response returned by ``POST /chat``.

    Includes the answer text, detected intent, TF-IDF confidence score,
    and metadata useful for frontend rendering.
    """

    answer: str = Field(
        ...,
        description="Bot's natural-language answer.",
        examples=["The college opens at 8:00 AM and closes at 5:00 PM."],
    )
    intent: str = Field(
        ...,
        description="Detected intent label.",
        examples=["timings"],
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="TF-IDF cosine-similarity confidence score.",
        examples=[0.8742],
    )
    session_id: str = Field(
        ...,
        description="Echo of the session ID from the request.",
        examples=["sess-abc123"],
    )
    fallback: bool = Field(
        default=False,
        description="True when the bot could not find a confident match.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Quick-reply chip suggestions for the user.",
    )


class HealthResponse(BaseModel):
    """Response from ``GET /health``."""

    status: str = Field(
        default="ok",
        description="Service health indicator.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Server UTC timestamp at the time of the health check.",
    )
