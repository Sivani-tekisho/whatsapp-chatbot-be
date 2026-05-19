"""Conversation memory / history loading."""

from uuid import UUID

from supabase import Client

from app.core.config import Settings


class MemoryService:
    def __init__(self, db: Client, settings: Settings) -> None:
        self._db = db
        self._limit = settings.conversation_history_limit

    def load_history(self, conversation_id: UUID) -> list[dict]:
        result = (
            self._db.table("messages")
            .select("role, message")
            .eq("conversation_id", str(conversation_id))
            .order("timestamp", desc=False)
            .limit(self._limit)
            .execute()
        )
        rows = result.data or []
        return [{"role": r["role"], "message": r["message"]} for r in rows if r["role"] != "system"]
