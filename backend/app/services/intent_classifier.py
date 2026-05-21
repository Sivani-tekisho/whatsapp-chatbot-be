"""Intent classifier for WhatsApp messages — pure regex, zero I/O.

Returns one of three intent labels:
  "social"    → greetings, acks, farewells, simple reactions
  "faq"       → common business questions (pricing, contact, hours, location…)
  "knowledge" → everything else (default — hits RAG + LLM)
"""

import re

# ── Pre-compiled patterns (compiled once at import time) ─────────────────────

# Full-message social match (trailing punctuation / emoji allowed)
_SOCIAL_RE = re.compile(
    r"^("
    r"hi+|hey+|hlo|hello|"
    r"good\s+(morning|evening|afternoon|night)|"
    r"thanks?(\s+you)?|thank\s*you|ty|"
    r"ok+|okay|sure|yep|nope|"
    r"got\s+it|noted|great|awesome|cool|"
    r"bye|goodbye|see\s+ya?|"
    r"no\s*problem|np|"
    r"👍|🙏|✅|yes|no|"
    # compound social phrases: "ok thanks", "hey there", "sure thanks", etc.
    r"(hey|ok|sure|great|awesome|cool)\s+(there|thanks?|ok)|"
    r"ok\s+thanks?|sure\s+thanks?"
    r")[!?.,\s😊🙏👋✅]*$",
    re.IGNORECASE,
)

# FAQ keyword presence (substring search).
# Intentionally narrow: only pure business logistics (pricing/contact/hours/location).
# Product/service questions and "about tekisho" are KNOWLEDGE intent so they hit RAG.
_FAQ_RE = re.compile(
    r"price|pricing|cost|charge|fee|how much|"
    r"contact|reach you|call you|email you|phone number|"
    r"office hours|working hours|open|closed|timing|"
    r"location|address|where are you|where is your office",
    re.IGNORECASE,
)

# Fast frozenset for single-token social words
_SOCIAL_TOKENS: frozenset[str] = frozenset(
    {
        "hi", "hii", "hiii", "hey", "heyy", "heyyy", "hello", "hlo",
        "thanks", "thank", "ty", "thankyou",
        "ok", "okay", "okk", "k",
        "sure", "yep", "nope", "yes", "no",
        "noted", "got it", "great", "awesome", "cool", "np",
        "bye", "goodbye",
        "👍", "🙏", "✅",
    }
)


def classify_intent(message: str) -> str:
    """Classify a WhatsApp message as 'social', 'faq', or 'knowledge'."""
    stripped = message.strip()
    normalised = stripped.lower().rstrip("!?., ")

    # 1. Very short messages are social
    if len(normalised) <= 3:
        return "social"

    # 2. Exact token match (fastest path)
    if normalised in _SOCIAL_TOKENS:
        return "social"

    # 3. Full-message social regex
    if _SOCIAL_RE.match(stripped):
        return "social"

    # 4. FAQ keyword presence
    if _FAQ_RE.search(stripped):
        return "faq"

    # 5. Default — knowledge / RAG required
    return "knowledge"


def get_social_reply(message: str) -> str:
    """Return a hardcoded friendly reply for social messages (no LLM call needed)."""
    normalised = message.strip().lower()

    if any(w in normalised for w in ("morning", "evening", "afternoon", "night")):
        return "Good day! 😊 How can I help you today?"

    if any(w in normalised for w in ("hi", "hey", "hello", "hlo")):
        return "Hey! 👋 How can I help you today?"

    if any(w in normalised for w in ("thanks", "thank", "ty", "thankyou")):
        return "Happy to help! Let me know if you need anything else. 😊"

    if any(w in normalised for w in ("bye", "goodbye", "see ya", "see you")):
        return "Goodbye! Feel free to message anytime. 👋"

    if any(w in normalised for w in ("ok", "okay", "noted", "sure", "got it",
                                      "great", "awesome", "cool", "np",
                                      "no problem", "yep", "yes")):
        return "Got it! Anything else I can help with?"

    return "Got it! What can I help you with?"
