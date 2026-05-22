"""System prompt construction for the company agent."""

from functools import lru_cache
from pathlib import Path

from app import company_branding as branding
from app.core.config import Settings, get_settings

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_WHATSAPP_TEMPLATE_PATH = _PROMPTS_DIR / "whatsapp_system_prompt.txt"
_WHATSAPP_COMPACT_PATH = _PROMPTS_DIR / "whatsapp_system_prompt_compact.txt"
_INTENT_POLICY_PATH = _PROMPTS_DIR / "whatsapp_intent_policy.txt"


@lru_cache(maxsize=2)
def _load_whatsapp_system_template(compact: bool = False) -> str:
    path = _WHATSAPP_COMPACT_PATH if compact else _WHATSAPP_TEMPLATE_PATH
    if not path.is_file():
        path = _WHATSAPP_TEMPLATE_PATH
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_intent_policy_template() -> str:
    if not _INTENT_POLICY_PATH.is_file():
        return ""
    return _INTENT_POLICY_PATH.read_text(encoding="utf-8")


def _branding(attr: str) -> str:
    return str(getattr(branding, attr, "") or "").strip()


def _org_settings_or_branding(
    org: dict | None, org_key: str, settings_value: str, branding_attr: str
) -> str:
    if org and org.get(org_key):
        return str(org[org_key]).strip()
    if (settings_value or "").strip():
        return settings_value.strip()
    return _branding(branding_attr)


def render_whatsapp_system_prompt(
    company_name: str,
    fallback_message: str,
    org_settings: dict | None = None,
    settings: Settings | None = None,
    detected_intent: str | None = None,
) -> str:
    """Fill placeholders from DB / .env / company_branding.py and prompt files only."""
    s = settings or get_settings()
    org = org_settings or {}
    display_name = branding.resolve_company_name(company_name, s.company_name)
    intent_label = (detected_intent or "general").strip().lower()
    website = _org_settings_or_branding(org, "website_url", s.website_url, "WEBSITE_URL")
    support = _org_settings_or_branding(org, "support_email", s.support_email, "SUPPORT_EMAIL")
    sales = _org_settings_or_branding(org, "sales_email", s.sales_email, "SALES_EMAIL")
    contact_email = sales or support

    policy_raw = _load_intent_policy_template()
    policy_block = ""
    if policy_raw.strip():
        policy_block = policy_raw
        for key, value in {
            "COMPANY_NAME": display_name,
            "FALLBACK_MESSAGE": fallback_message,
            "DETECTED_INTENT": intent_label,
            "WEBSITE_URL": website,
            "CONTACT_EMAIL": contact_email,
            "PHONE_NUMBER": _org_settings_or_branding(
                org, "phone_number", s.company_phone, "PHONE_NUMBER"
            ),
        }.items():
            policy_block = policy_block.replace("{{" + key + "}}", value)

    mapping = {
        "COMPANY_NAME": display_name,
        "FALLBACK_MESSAGE": fallback_message,
        "DETECTED_INTENT": intent_label,
        "INTENT_POLICY": policy_block.strip(),
        "WEBSITE_URL": website,
        "CONTACT_EMAIL": contact_email,
        "SUPPORT_EMAIL": support,
        "SALES_EMAIL": sales or support,
        "PHONE_NUMBER": _org_settings_or_branding(
            org, "phone_number", s.company_phone, "PHONE_NUMBER"
        ),
        "WHATSAPP_NUMBER": _org_settings_or_branding(
            org, "whatsapp_number", s.company_whatsapp_display, "WHATSAPP_NUMBER"
        ),
        "OFFICE_ADDRESS": _org_settings_or_branding(
            org, "office_address", s.office_address, "OFFICE_ADDRESS"
        ),
    }

    use_compact = s.whatsapp_use_compact_prompt
    raw = _load_whatsapp_system_template(use_compact)
    if not raw.strip():
        return policy_block.strip()

    out = raw
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out.strip()


_MAX_CUSTOM_PROMPT_CHARS = 0


def _history_for_llm(history: list[dict], user_message: str) -> list[dict]:
    if not history:
        return []
    last = history[-1]
    if (
        last.get("role") == "user"
        and (last.get("message") or "").strip() == user_message.strip()
    ):
        return history[:-1]
    return history


class PromptService:
    DEFAULT_RULES = """
Rules:
- Answer only using the provided company context
- Never invent information
- If information is unavailable, say exactly: "{fallback}"
- Keep responses short for WhatsApp (under 500 characters when possible)
- Prefer bullet points for lists (use "- " lines; never ** or Markdown)
- Output plain text only — no **bold**, # headings, or `code` fences
- Maintain a professional, helpful company tone
"""

    def build_system_prompt(
        self,
        company_name: str,
        custom_prompt: str | None,
        fallback_message: str,
        org_settings: dict | None = None,
        detected_intent: str | None = None,
    ) -> str:
        settings = get_settings()
        whatsapp_core = render_whatsapp_system_prompt(
            company_name=company_name,
            fallback_message=fallback_message,
            org_settings=org_settings,
            settings=settings,
            detected_intent=detected_intent,
        )

        if whatsapp_core:
            parts = [whatsapp_core]
            if custom_prompt and str(custom_prompt).strip():
                extra = str(custom_prompt).strip()
                if _MAX_CUSTOM_PROMPT_CHARS > 0 and len(extra) > _MAX_CUSTOM_PROMPT_CHARS:
                    extra = extra[: _MAX_CUSTOM_PROMPT_CHARS - 3].rstrip() + "..."
                parts.append(
                    "\n---\n## Additional organization instructions (from database)\n"
                    + extra
                )
            return "\n".join(parts).strip()

        base = custom_prompt or (f"You are an AI assistant for {company_name}.")
        rules = self.DEFAULT_RULES.format(fallback=fallback_message)
        return f"{base.strip()}\n{rules.strip()}"

    def build_rag_system_prompt(
        self,
        company_name: str,
        fallback_message: str,
        org_settings: dict | None = None,
        custom_prompt: str | None = None,
        detected_intent: str | None = None,
    ) -> str:
        settings = get_settings()
        if settings.whatsapp_rag_minimal_system:
            return render_whatsapp_system_prompt(
                company_name=company_name,
                fallback_message=fallback_message,
                org_settings=org_settings,
                settings=settings,
                detected_intent=detected_intent,
            )
        return self.build_system_prompt(
            company_name=company_name,
            custom_prompt=custom_prompt,
            fallback_message=fallback_message,
            org_settings=org_settings,
            detected_intent=detected_intent,
        )

    def build_no_rag_prompt(
        self,
        company_name: str,
        fallback_message: str,
        user_message: str,
        history: list[dict],
        org_settings: dict | None = None,
        intent: str | None = None,
    ) -> list[dict]:
        system = self.build_system_prompt(
            company_name=company_name,
            custom_prompt=org_settings.get("system_prompt") if org_settings else None,
            fallback_message=fallback_message,
            org_settings=org_settings,
            detected_intent=intent,
        )
        if system:
            system += (
                "\n\n## Retrieval\n"
                "No knowledge base passages matched this message. "
                "Apply the intent policy above and answer from what you know is appropriate."
            )

        history = _history_for_llm(history, user_message)
        messages: list[dict] = [{"role": "system", "content": system}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    def _trim_chunks(chunks: list[str], max_chars: int) -> list[str]:
        if max_chars <= 0:
            return chunks
        trimmed = []
        for c in chunks:
            c = (c or "").strip()
            if len(c) > max_chars:
                c = c[: max_chars - 3].rstrip() + "..."
            trimmed.append(c)
        return trimmed

    def build_rag_prompt(
        self,
        system_prompt: str,
        context_chunks: list[str],
        user_message: str,
        history: list[dict],
        max_chunk_chars: int | None = None,
        company_name: str = "Tekisho",
        intent: str | None = None,
        org_settings: dict | None = None,
    ) -> list[dict]:
        limit = max_chunk_chars if max_chunk_chars is not None else get_settings().rag_chunk_max_chars
        history = _history_for_llm(history, user_message)
        chunks = self._trim_chunks(context_chunks, limit)
        context_block = "\n\n---\n\n".join(chunks) if chunks else "(No relevant documents found)"
        system_with_context = (
            f"{system_prompt}\n\n"
            f"## Knowledge base\n{context_block}"
        )

        messages: list[dict] = [{"role": "system", "content": system_with_context}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_message})
        return messages


def get_prompt_service(settings: Settings | None = None) -> PromptService:
    return PromptService()
