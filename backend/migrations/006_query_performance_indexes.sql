-- Run in Supabase SQL Editor: speeds up chat history, conversation list, lookups.
-- Safe to run multiple times (IF NOT EXISTS).

-- Last N messages per conversation (memory / polling)
CREATE INDEX IF NOT EXISTS idx_messages_conversation_timestamp_desc
    ON messages (conversation_id, timestamp DESC);

-- Dashboard conversation list sorted by recent activity
CREATE INDEX IF NOT EXISTS idx_conversations_org_updated_desc
    ON conversations (organization_id, updated_at DESC);

-- Webhook: find conversation by org + phone
CREATE INDEX IF NOT EXISTS idx_conversations_org_phone
    ON conversations (organization_id, phone);

-- Optional after 004_cached_responses.sql:
-- CREATE INDEX IF NOT EXISTS idx_cached_responses_lookup
--     ON cached_responses (organization_id, cache_key);

-- Refresh planner statistics
ANALYZE messages;
ANALYZE conversations;
