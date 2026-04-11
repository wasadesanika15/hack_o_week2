#!/usr/bin/env python3
"""
CLI simulator — Mobile channel.

Usage:
    python simulate_mobile.py --query "Library hours are 8 AM to 9 PM. Carry your student ID."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure modules are importable
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.channel_adapter import format_response


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate Mobile channel formatting for the College FAQ Chatbot."
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="The answer text to format (simulates the bot's raw answer).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Mobile Channel Simulator")
    print("=" * 60)
    print()

    formatted = format_response(args.query, "mobile")
    print(formatted)
    print()


if __name__ == "__main__":
    main()
