#!/usr/bin/env python3
"""
CLI test runner for the College FAQ Chatbot.

Usage:
    python chat.py

Uses ``get_response(query, session_id)`` from the backend modules.
All NLP/ML logic is handled by the modular pipeline.
"""

import sys
from pathlib import Path

# Ensure backend modules are importable
_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.chatbot_core import get_response  # noqa: E402

SESSION_ID = "cli-session"


def main() -> None:
    print("=" * 60)
    print("  College FAQ Chatbot — CLI Mode")
    print("  Type your question, or 'exit' / 'quit' to stop.")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Goodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            print("Bot: Goodbye! 👋")
            break

        response = get_response(user_input, SESSION_ID)
        print(f"Bot: {response}")
        print()


if __name__ == "__main__":
    main()
