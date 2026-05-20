"""Normalize bot text for WhatsApp (no Markdown)."""

import re


def format_for_whatsapp(text: str) -> str:
    """
    Strip common Markdown so users never see raw ** or `code`.
    WhatsApp does not render Markdown like chat UIs.
    """
    if not text:
        return ""
    s = text

    # [label](url) -> label (url)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
    s = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", s)

    # Bold ** and __ (repeat for nested)
    for _ in range(8):
        next_s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        if next_s == s:
            break
        s = next_s
    for _ in range(8):
        next_s = re.sub(r"__([^_]+)__", r"\1", s)
        if next_s == s:
            break
        s = next_s

    # Strikethrough
    s = re.sub(r"~~(.+?)~~", r"\1", s)

    # Fenced code blocks
    s = re.sub(r"```[\w]*\s*\n?", "", s)
    s = s.replace("```", "")

    # Inline `code`
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # ATX headings at line start
    s = re.sub(r"^#{1,6}\s+", "", s, flags=re.MULTILINE)

    # Italic *word* (not list lines like "* item" with no closing *)
    s = re.sub(r"(?<![*])\*([^*\n]+?)\*(?![*])", r"\1", s)

    # Any leftover asterisk runs used as emphasis
    s = s.replace("**", "")

    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
