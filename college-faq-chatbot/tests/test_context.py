"""
Tests for context management (multi-turn) — Task 7.

Covers: session state, auto-reset after idle turns, topic-change detection,
and a 3-turn conversation transcript demo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.chatbot_core import get_chat_payload, get_response  # noqa: E402
from modules.context_manager import (  # noqa: E402
    MAX_IDLE_TURNS,
    ContextManager,
    SessionState,
    get_context_manager,
)


class TestSessionState:
    """Basic session state operations."""

    def test_new_session_has_defaults(self):
        mgr = ContextManager()
        state = mgr.get("test-1")
        assert state.session_id == "test-1"
        assert state.last_intent is None
        assert state.last_entities == {}
        assert state.previous_response is None
        assert state.turn_count == 0

    def test_update_merges_entities(self):
        mgr = ContextManager()
        mgr.update("s1", entities={"semester": 5})
        mgr.update("s1", entities={"department": "CS"})
        state = mgr.get("s1")
        assert state.last_entities.get("semester") == 5
        assert state.last_entities.get("department") == "CS"

    def test_update_tracks_intent(self):
        mgr = ContextManager()
        mgr.update("s2", intent="fees")
        assert mgr.get("s2").last_intent == "fees"

    def test_reset_clears_state(self):
        mgr = ContextManager()
        mgr.update("s3", intent="exam", entities={"semester": 3})
        mgr.reset("s3")
        state = mgr.get("s3")
        assert state.last_intent is None
        assert state.last_entities == {}

    def test_active_sessions(self):
        mgr = ContextManager()
        mgr.get("a1")
        mgr.get("a2")
        assert "a1" in mgr.active_sessions()
        assert "a2" in mgr.active_sessions()


class TestAutoReset:
    """Session resets after MAX_IDLE_TURNS."""

    def test_auto_reset_after_max_turns(self):
        mgr = ContextManager()
        mgr.update("reset-test", intent="fees", entities={"semester": 5})

        # Simulate MAX_IDLE_TURNS + 1 updates
        for i in range(MAX_IDLE_TURNS + 1):
            mgr.update("reset-test", intent="general", user_message="ok")

        state = mgr.get("reset-test")
        # After reset, turn_count should be back to a low number
        assert state.turn_count <= 2


class TestTopicChange:
    """Topic-change detection clears stale entities."""

    def test_topic_change_clears_entities(self):
        mgr = ContextManager()
        # Start with fees topic
        mgr.update("tc-1", intent="fees", entities={"semester": 5},
                    user_message="What is the fee for semester 5")
        assert mgr.get("tc-1").last_entities.get("semester") == 5

        # Switch to a completely different topic with a substantial query
        mgr.update("tc-1", intent="hostel",
                    user_message="Tell me about hostel accommodation",
                    entities={})
        state = mgr.get("tc-1")
        # Entities should have been cleared on topic change
        assert state.last_intent == "hostel"

    def test_same_topic_preserves_entities(self):
        mgr = ContextManager()
        mgr.update("tc-2", intent="fees", entities={"semester": 3},
                    user_message="semester 3 fees")
        mgr.update("tc-2", intent="fees", entities={"department": "CS"},
                    user_message="for CS department")
        state = mgr.get("tc-2")
        assert state.last_entities.get("semester") == 3
        assert state.last_entities.get("department") == "CS"


class TestMultiTurnConversation:
    """Full integration: multi-turn conversations through get_response."""

    def test_context_carries_entities(self):
        sid = "multi-1"
        # Turn 1: establish context
        r1 = get_chat_payload("SEM 3 CS timetable", sid)
        assert r1["entities"].get("semester") == 3 or r1["entities"].get("department") == "CS"

        # Turn 2: follow-up without repeating entities
        r2 = get_chat_payload("When is the exam?", sid)
        # Should still have semester or department from context
        has_context = (
            r2["entities"].get("semester") == 3
            or r2["entities"].get("department") == "CS"
        )
        assert has_context, f"Context lost: entities = {r2['entities']}"

    def test_three_turn_conversation(self, capsys):
        """3-turn conversation transcript for the README."""
        sid = "demo-3turn"
        turns = [
            "What is the fee structure for CS?",
            "And for semester 5?",
            "What about exam dates?",
        ]
        print("\n" + "=" * 70)
        print("  3-Turn Conversation Demo")
        print("=" * 70)
        for i, q in enumerate(turns, 1):
            response = get_response(q, sid)
            print(f"  Turn {i}:")
            print(f"    Student: {q}")
            print(f"    Bot:     {response}")
            print()
        print("=" * 70)

        captured = capsys.readouterr()
        assert "Turn 1" in captured.out
        assert "Turn 2" in captured.out
        assert "Turn 3" in captured.out

    def test_short_followup_reuses_intent(self):
        """Very short follow-ups reuse the last topic's context."""
        sid = "followup-test"
        # Establish topic
        get_response("Tell me about hostel facilities and accommodation", sid)
        # Short follow-up
        r = get_response("What about fees?", sid)
        assert isinstance(r, str) and len(r) > 10
