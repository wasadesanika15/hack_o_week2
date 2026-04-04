"""
Per-session conversational context for multi-turn FAQ assistance.

Features:
- Tracks last intent, merged entities, previous bot reply, and user message.
- Auto-resets after ``MAX_IDLE_TURNS`` unanswered turns.
- Detects topic change when intent shifts on a substantial new query.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# Configurable constants
MAX_IDLE_TURNS = 5          # Reset session after this many turns
TOPIC_CHANGE_MIN_WORDS = 3  # Minimum query words to trigger topic-change detection


@dataclass
class SessionState:
    session_id: str
    last_intent: str | None = None
    last_entities: dict[str, Any] = field(default_factory=dict)
    previous_response: str | None = None
    last_user_message: str | None = None
    turn_count: int = 0
    last_active: float = field(default_factory=time.time)


class ContextManager:
    """
    In-memory session store (swap for Redis in a scaled deployment).

    Tracks last intent, merged entities, and previous bot reply so follow-ups
    like "what about hostel fees?" can reuse partial slots.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        sid = session_id or "anonymous"
        if sid not in self._sessions:
            self._sessions[sid] = SessionState(session_id=sid)
        return self._sessions[sid]

    def update(
        self,
        session_id: str,
        *,
        intent: str | None = None,
        entities: dict[str, Any] | None = None,
        response: str | None = None,
        user_message: str | None = None,
    ) -> SessionState:
        state = self.get(session_id)

        # --- Auto-reset after MAX_IDLE_TURNS with no topic ---
        state.turn_count += 1
        if state.turn_count > MAX_IDLE_TURNS:
            self.reset(session_id)
            state = self.get(session_id)
            state.turn_count = 1

        state.last_active = time.time()

        if user_message is not None:
            state.last_user_message = user_message

        # --- Topic-change detection ---
        if intent is not None and state.last_intent is not None:
            is_topic_change = (
                intent != state.last_intent
                and intent != "general"
                and state.last_intent != "general"
                and user_message is not None
                and len((user_message or "").split()) >= TOPIC_CHANGE_MIN_WORDS
            )
            if is_topic_change:
                # Clear stale entities from previous topic
                state.last_entities = {}

        if intent is not None:
            state.last_intent = intent

        if entities is not None:
            merged = {**state.last_entities}
            for k, v in entities.items():
                if v is not None and v != "" and v != []:
                    merged[k] = v
            state.last_entities = merged

        if response is not None:
            state.previous_response = response

        return state

    def reset(self, session_id: str) -> None:
        """Clear all state for a session."""
        sid = session_id or "anonymous"
        if sid in self._sessions:
            del self._sessions[sid]

    def active_sessions(self) -> list[str]:
        """Return list of active session IDs."""
        return list(self._sessions.keys())


_manager = ContextManager()


def get_context_manager() -> ContextManager:
    return _manager
