-- Use this migration when RAG lives in Pinecone (not Supabase).
-- Supabase = chat history + bot settings only.

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    bot_name TEXT DEFAULT 'Company Assistant',
    system_prompt TEXT,
    greeting_message TEXT DEFAULT 'Hello! How can I help you today?',
    fallback_message TEXT DEFAULT 'I couldn''t find that information.',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    phone TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'resolved')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (organization_id, phone)
);

CREATE INDEX IF NOT EXISTS idx_conversations_org ON conversations(organization_id);
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

INSERT INTO organizations (name, bot_name, system_prompt)
SELECT
    'Default Organization',
    'Company Assistant',
    'You are an AI assistant for the company. Answer only using company information. Never invent information. Keep responses short for WhatsApp. Prefer bullet points.'
WHERE NOT EXISTS (SELECT 1 FROM organizations LIMIT 1);