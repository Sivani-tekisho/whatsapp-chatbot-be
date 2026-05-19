"""Conversation and message persistence."""

from datetime import datetime, timezone
from uuid import UUID

from supabase import Client

from app.core.config import Settings


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


class ConversationService:
    def __init__(self, db: Client, settings: Settings) -> None:
        self._db = db
        org_id = settings.default_organization_id
        self._org_id = org_id if org_id and _is_valid_uuid(org_id) else ""

    def _org_id_str(self) -> str:
        if not self._org_id:
            org = self._db.table("organizations").select("id").limit(1).execute()
            if not org.data:
                raise RuntimeError(
                    "No organization found. Run supabase/migrations/002_chat_only_pinecone.sql"
                )
            self._org_id = org.data[0]["id"]
        return self._org_id

    def get_or_create(self, phone: str) -> dict:
        org_id = self._org_id_str()
        existing = (
            self._db.table("conversations")
            .select("*")
            .eq("organization_id", org_id)
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]

        created = (
            self._db.table("conversations")
            .insert({"organization_id": org_id, "phone": phone})
            .execute()
        )
        return created.data[0]

    def save_message(self, conversation_id: UUID, role: str, message: str) -> dict:
        row = (
            self._db.table("messages")
            .insert(
                {
                    "conversation_id": str(conversation_id),
                    "role": role,
                    "message": message,
                }
            )
            .execute()
        )
        self._db.table("conversations").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(conversation_id)).execute()
        return row.data[0]

    def list_conversations(
        self,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        org_id = self._org_id_str()
        query = (
            self._db.table("conversations")
            .select("*", count="exact")
            .eq("organization_id", org_id)
            .order("updated_at", desc=True)
        )
        if status:
            query = query.eq("status", status)
        if search:
            query = query.ilike("phone", f"%{search}%")

        result = query.range(offset, offset + limit - 1).execute()
        conversations = result.data or []
        total = result.count or len(conversations)

        for conv in conversations:
            msgs = (
                self._db.table("messages")
                .select("message, timestamp")
                .eq("conversation_id", conv["id"])
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            count_result = (
                self._db.table("messages")
                .select("id", count="exact")
                .eq("conversation_id", conv["id"])
                .execute()
            )
            conv["message_count"] = count_result.count or 0
            conv["last_message"] = msgs.data[0]["message"] if msgs.data else None

        return conversations, total

    def get_conversation_with_messages(self, conversation_id: UUID) -> dict | None:
        conv = (
            self._db.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .limit(1)
            .execute()
        )
        if not conv.data:
            return None

        messages = (
            self._db.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("timestamp", desc=False)
            .execute()
        )
        data = conv.data[0]
        data["messages"] = messages.data or []
        return data

    def update_status(self, conversation_id: UUID, status: str) -> dict:
        result = (
            self._db.table("conversations")
            .update({"status": status})
            .eq("id", str(conversation_id))
            .execute()
        )
        return result.data[0]

    def get_dashboard_metrics(self) -> dict:
        org_id = self._org_id_str()
        convs = (
            self._db.table("conversations")
            .select("id, status", count="exact")
            .eq("organization_id", org_id)
            .execute()
        )
        total = convs.count or 0
        resolved = sum(1 for c in (convs.data or []) if c.get("status") == "resolved")

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        msgs_today = (
            self._db.table("messages")
            .select("id", count="exact")
            .gte("timestamp", today_start)
            .execute()
        )

        return {
            "total_conversations": total,
            "messages_today": msgs_today.count or 0,
            "resolved_conversations": resolved,
            "average_response_time_seconds": 2.5,
        }
