"""
Multi-channel response formatter for the College FAQ Chatbot (Task 9).

Pure formatter: string in → formatted string out.
No network calls, no state, no side effects.

Supported channels:
  • ``web``      — Full Markdown/HTML allowed.
  • ``mobile``   — Compact card blocks, max 160 chars per block.
  • ``whatsapp`` — Plain text only, no emojis, max 1 000 chars.
"""

from __future__ import annotations

import re
import textwrap
from html import escape as html_escape


# ──────────────────────────────────────────────────────────────────────
# Emoji / special-character regex (covers most common emoji ranges)
# ──────────────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols, extended-A
    "\U0001FA70-\U0001FAFF"  # extended-B
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000200D"             # zero-width joiner
    "\U0000203C"             # double exclamation
    "\U00002049"             # exclamation question mark
    "]+",
    flags=re.UNICODE,
)

# Markdown link pattern: [text](url)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Markdown bold / italic
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"\*(.+?)\*")

# HTML tag stripper
_HTML_TAG_RE = re.compile(r"<[^>]+>")


# ──────────────────────────────────────────────────────────────────────
# Channel formatters
# ──────────────────────────────────────────────────────────────────────
def _format_web(answer: str) -> str:
    """
    Web channel: wrap answer in a styled HTML card.

    Markdown bold/italic is converted to HTML.  Raw HTML is kept as-is.
    """
    html = answer

    # Convert markdown links → HTML anchors
    html = _MD_LINK_RE.sub(r'<a href="\2" target="_blank">\1</a>', html)

    # Convert markdown bold/italic → HTML
    html = _MD_BOLD_RE.sub(r"<strong>\1</strong>", html)
    html = _MD_ITALIC_RE.sub(r"<em>\1</em>", html)

    # Wrap newlines for HTML rendering
    html = html.replace("\n", "<br>\n")

    return (
        '<div class="chat-answer" style="'
        "font-family:system-ui,sans-serif;"
        "padding:12px 16px;"
        "border-left:4px solid #4f46e5;"
        "background:#f8f9fa;"
        "border-radius:6px;"
        "line-height:1.6;"
        '">\n'
        f"  {html}\n"
        "</div>"
    )


def _format_mobile(answer: str, max_block: int = 160) -> str:
    """
    Mobile channel: compact card with truncated blocks.

    Each paragraph is treated as a separate block, capped at ``max_block`` chars.
    """
    # Strip HTML and markdown
    plain = _strip_markup(answer)

    blocks = [b.strip() for b in plain.split("\n\n") if b.strip()]
    if not blocks:
        blocks = [b.strip() for b in plain.split("\n") if b.strip()]

    cards: list[str] = []
    for block in blocks:
        # Wrap to max_block chars
        if len(block) > max_block:
            block = block[: max_block - 3].rstrip() + "..."
        cards.append(f"┌─ {block}")

    return "\n".join(cards) if cards else "┌─ No answer available."


def _format_whatsapp(answer: str, max_chars: int = 1000) -> str:
    """
    WhatsApp channel: plain text only, no emojis, hard length cap.
    """
    plain = _strip_markup(answer)

    # Remove emojis
    plain = _EMOJI_RE.sub("", plain)

    # Collapse multiple whitespace / blank lines
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    plain = re.sub(r"[ \t]+", " ", plain)
    plain = plain.strip()

    if len(plain) > max_chars:
        plain = plain[: max_chars - 3].rstrip() + "..."

    return plain


def _strip_markup(text: str) -> str:
    """Remove both HTML tags and Markdown formatting from *text*."""
    out = _HTML_TAG_RE.sub("", text)
    out = _MD_LINK_RE.sub(r"\1 (\2)", out)
    out = _MD_BOLD_RE.sub(r"\1", out)
    out = _MD_ITALIC_RE.sub(r"\1", out)
    return out


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────
_FORMATTERS = {
    "web": _format_web,
    "mobile": _format_mobile,
    "whatsapp": _format_whatsapp,
}

SUPPORTED_CHANNELS = tuple(_FORMATTERS.keys())


def format_response(answer: str, channel: str) -> str:
    """
    Format *answer* for the given *channel*.

    Parameters
    ----------
    answer : str
        The raw bot answer (may contain Markdown or HTML).
    channel : str
        One of ``"web"``, ``"mobile"``, ``"whatsapp"``.

    Returns
    -------
    str
        Channel-appropriate formatted string.

    Raises
    ------
    ValueError
        If *channel* is not a recognised channel name.
    """
    key = (channel or "").strip().lower()
    formatter = _FORMATTERS.get(key)
    if formatter is None:
        raise ValueError(
            f"Unknown channel '{channel}'. "
            f"Supported channels: {', '.join(SUPPORTED_CHANNELS)}"
        )
    return formatter(answer)


# ──────────────────────────────────────────────────────────────────────
# Stand-alone demo
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = (
        "**College Library** opens at 8:00 AM 📚 and closes at 9:00 PM.\n\n"
        "Visit [Library Portal](https://library.college.edu) for more info.\n\n"
        "Remember to carry your **student ID card** 🪪!"
    )
    for ch in SUPPORTED_CHANNELS:
        print(f"\n{'='*60}")
        print(f"  Channel: {ch.upper()}")
        print(f"{'='*60}")
        print(format_response(sample, ch))
