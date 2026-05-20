"""Conversation memory / history loading."""

from uuid import UUID

from supabase import Client

from app.core.config import Settings


class MemoryService:
    def __init__(self, db: Client, settings: Settings) -> None:
        self._db = db
        self._limit = settings.conversation_history_limit

    def load_history(self, conversation_id: UUID) -> list[dict]:
        """Conversation messages in chronological order (for LLM context)."""
        base = (
            self._db.table("messages")
            .select("role, message")
            .eq("conversation_id", str(conversation_id))
        )
        if self._limit > 0:
            rows = (
                base.order("timestamp", desc=True)
                .limit(self._limit)
                .execute()
                .data
                or []
            )
            rows = list(reversed(rows))
        else:
            rows = base.order("timestamp", desc=False).execute().data or []
        return [{"role": r["role"], "message": r["message"]} for r in rows if r["role"] != "system"]
