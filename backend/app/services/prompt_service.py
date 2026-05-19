"""System prompt construction for the company agent."""

from app.core.config import Settings


class PromptService:
    DEFAULT_RULES = """
Rules:
- Answer only using the provided company context
- Never invent information
- If information is unavailable, say exactly: "{fallback}"
- Keep responses short for WhatsApp (under 500 characters when possible)
- Prefer bullet points for lists
- Maintain a professional, helpful company tone
"""

    def build_system_prompt(
        self,
        company_name: str,
        custom_prompt: str | None,
        fallback_message: str,
    ) -> str:
        base = custom_prompt or (
            f"You are an AI assistant for {company_name}."
        )
        rules = self.DEFAULT_RULES.format(fallback=fallback_message)
        return f"{base.strip()}\n{rules.strip()}"

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
            f"## Company Knowledge Base\n{context_block}"
        )

        messages: list[dict] = [{"role": "system", "content": system_with_context}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_message})
        return messages


def get_prompt_service(settings: Settings | None = None) -> PromptService:
    return PromptService()
