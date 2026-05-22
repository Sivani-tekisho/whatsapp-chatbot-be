-- Optional: persistent cache in Supabase (app uses in-memory cache by default).
-- Run this only if you want answers stored in the database across restarts.

CREATE TABLE IF NOT EXISTS cached_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    cache_key TEXT NOT NULL,
    normalized_question TEXT,
    response TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE (organization_id, cache_key)
);

CREATE INDEX IF NOT EXISTS idx_cached_responses_lookup
    ON cached_responses(organization_id, cache_key);
