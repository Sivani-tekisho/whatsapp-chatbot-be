"""System prompt construction for the company agent."""

from functools import lru_cache
from pathlib import Path

from app import company_branding as branding
from app.core.config import Settings, get_settings

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_WHATSAPP_TEMPLATE_PATH = _PROMPTS_DIR / "whatsapp_system_prompt.txt"


@lru_cache(maxsize=1)
def _load_whatsapp_system_template() -> str:
    if not _WHATSAPP_TEMPLATE_PATH.is_file():
        return ""
    return _WHATSAPP_TEMPLATE_PATH.read_text(encoding="utf-8")


def _branding(attr: str) -> str:
    """Read from company_branding.py; missing optional fields default to empty."""
    return str(getattr(branding, attr, "") or "").strip()


def _org_settings_or_branding(
    org: dict | None, org_key: str, settings_value: str, branding_attr: str
) -> str:
    """DB org column → .env → company_branding.py."""
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
) -> str:
    """Fill {{PLACEHOLDERS}} in whatsapp_system_prompt.txt from DB → .env → company_branding.py."""
    s = settings or get_settings()
    org = org_settings or {}

    display_name = (
        (company_name or "").strip()
        or (s.company_name or "").strip()
        or _branding("COMPANY_NAME")
        or "Our Company"
    )

    mapping = {
        "COMPANY_NAME": display_name,
        "FALLBACK_MESSAGE": fallback_message,
        "WEBSITE_URL": _org_settings_or_branding(org, "website_url", s.website_url, "WEBSITE_URL"),
        "SUPPORT_EMAIL": _org_settings_or_branding(
            org, "support_email", s.support_email, "SUPPORT_EMAIL"
        ),
        "SALES_EMAIL": _org_settings_or_branding(org, "sales_email", s.sales_email, "SALES_EMAIL"),
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

    raw = _load_whatsapp_system_template()
    if not raw.strip():
        return ""

    out = raw
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    # Leave any unreplaced {{KEY}} as-is if we add new placeholders later
    return out.strip()


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
    ) -> str:
        settings = get_settings()
        whatsapp_core = render_whatsapp_system_prompt(
            company_name=company_name,
            fallback_message=fallback_message,
            org_settings=org_settings,
            settings=settings,
        )

        if whatsapp_core:
            parts = [whatsapp_core]
            if custom_prompt and str(custom_prompt).strip():
                parts.append(
                    "\n---\n## Additional organization instructions (from database)\n"
                    + str(custom_prompt).strip()
                )
            return "\n".join(parts).strip()

        base = custom_prompt or (f"You are an AI assistant for {company_name}.")
        rules = self.DEFAULT_RULES.format(fallback=fallback_message)
        return f"{base.strip()}\n{rules.strip()}"

    def build_no_rag_prompt(
        self,
        company_name: str,
        fallback_message: str,
        user_message: str,
        history: list[dict],
        org_settings: dict | None = None,
    ) -> list[dict]:
        """When retrieval finds nothing — use WhatsApp policy + safe general knowledge."""
        settings = get_settings()
        base = render_whatsapp_system_prompt(
            company_name=company_name,
            fallback_message=fallback_message,
            org_settings=org_settings,
            settings=settings,
        )

        if base:
            system = (
                base
                + "\n\n==================================================\n"
                + "## Current retrieval state\n"
                + "No knowledge base chunks were retrieved for this user message. "
                "Apply **WHEN INFORMATION IS NOT VERIFIED**, **GENERAL AI KNOWLEDGE USAGE**, "
                "and **CONTACT & BUSINESS INTEREST HANDLING** strictly. "
                "Do not invent company-specific facts."
            )
        else:
            system = (
                f"You are a helpful WhatsApp assistant for {company_name}.\n"
                "No company knowledge base context is available for this question.\n"
                "Rules:\n"
                f"- For questions about services, pricing, products, or company details, "
                f'say exactly: "{fallback_message}"\n'
                "- You may answer simple greetings and clarify what the user needs.\n"
                "- Never invent services, prices, or policies.\n"
                "- Keep replies under 500 characters."
            )

        messages: list[dict] = [{"role": "system", "content": system}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_message})
        return messages

    def build_rag_prompt(
        self,
        system_prompt: str,
        context_chunks: list[str],
        user_message: str,
        history: list[dict],
    ) -> list[dict]:
        context_block = "\n\n---\n\n".join(context_chunks) if context_chunks else "(No relevant documents found)"
        system_with_context = (
            f"{system_prompt}\n\n"
            f"## Company Knowledge Base (retrieved context — treat as primary for facts)\n{context_block}"
        )

        messages: list[dict] = [{"role": "system", "content": system_with_context}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_message})
        return messages


def get_prompt_service(settings: Settings | None = None) -> PromptService:
    return PromptService()
