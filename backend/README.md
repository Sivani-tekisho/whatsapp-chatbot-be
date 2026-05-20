# WhatsApp AI Chatbot Platform

Production-ready WhatsApp chatbot with RAG knowledge base, Meta Cloud API integration, and admin dashboard. Built for a single organization today, with `organization_id` on all tables for future multi-tenancy.

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Python 3.13, Supabase (PostgreSQL + pgvector), OpenAI, LangChain |
| Frontend | React, Vite, Tailwind, Axios |
| Messaging | Meta WhatsApp Cloud API |

## Architecture

```
WhatsApp User → Meta API → POST /webhook → MessageProcessor
  → RAG (Pinecone or Supabase) → LLM → Save messages (Supabase) → WhatsApp reply
```

| Store | Purpose |
|-------|---------|
| **Pinecone** | Your existing document embeddings (RAG) |
| **Supabase** | Conversations, messages, bot settings only |

Admin UI talks to `/api/v1/*` for conversations and settings.

## Quick Start (existing Pinecone RAG)

### 1. Supabase — chat tables only

Run **`supabase/migrations/002_chat_only_pinecone.sql`** in SQL Editor.

Do **not** need `documents` / `document_chunks` tables if RAG stays in Pinecone.

### 2. `.env` — connect Pinecone

```env
RAG_PROVIDER=pinecone
PINECONE_API_KEY=your_key
PINECONE_HOST=https://your-index-xxxx.svc.pinecone.io
PINECONE_NAMESPACE=
PINECONE_TEXT_METADATA_KEY=text
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

Use the same **embedding model + dimensions** as when you built the Pinecone index.

Find **Host** in Pinecone console → Indexes → your index.

If chunk text is stored under a different metadata key (e.g. `content`, `page_content`), set `PINECONE_TEXT_METADATA_KEY`.

### 3. Run backend + frontend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

## Quick Start (upload docs to Supabase instead)

### 1. Supabase setup

1. Create a [Supabase](https://supabase.com) project.
2. Open **SQL Editor** and run `supabase/migrations/001_initial_schema.sql`.
3. Set `RAG_PROVIDER=supabase` in `.env`.
4. Copy your project URL, anon key, and **service role** key.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Create backend/.env — set variables listed under "Environment Variables" below
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Ingest documents (Supabase RAG only)

Skip this if using Pinecone. Place PDF/DOCX in a folder:

```bash
cd backend
python scripts/ingest_existing_docs.py --path "C:\path\to\your\docs"
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 5. WhatsApp webhook (ngrok)

```bash
ngrok http 8000
```

In [Meta Developer Console](https://developers.facebook.com/):

| Field | Value |
|-------|-------|
| Callback URL | `https://YOUR-NGROK-URL/webhook` |
| Verify token | Same as `VERIFY_TOKEN` in `.env` |
| Subscribe | `messages` |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `WHATSAPP_ACCESS_TOKEN` | Meta permanent token |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone number ID from Meta |
| `VERIFY_TOKEN` | Webhook verification string |
| `APP_SECRET` | Meta app secret (signature verification) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend DB access |
| `DEFAULT_ORGANIZATION_ID` | Optional org UUID |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhook` | Meta verification |
| POST | `/webhook` | Incoming messages |
| GET | `/api/v1/conversations/metrics` | Dashboard stats |
| GET | `/api/v1/conversations` | List conversations |
| POST | `/api/v1/conversations/outbound` | Send first message to a phone (admin UI) |
| GET | `/api/v1/documents` | List documents |
| POST | `/api/v1/documents/upload` | Upload PDF/DOC |
| POST | `/api/v1/documents/url` | Ingest website |
| GET/PATCH | `/api/v1/settings` | Bot configuration |

## Testing Checklist

- [ ] Company FAQs from your documents
- [ ] Pricing / product questions
- [ ] Conversation memory (follow-up questions)
- [ ] Unknown question → fallback message
- [ ] Greeting on "hi" / "hello"

## Project Structure

```
backend/app/
  api/          # FastAPI routes
  services/     # Business logic (DI via dependencies.py)
  agents/       # Company RAG agent
  rag/          # Embeddings, chunking, retrieval
  db/           # Supabase client
  core/         # Config, security

frontend/src/
  pages/        # Dashboard, Conversations, Knowledge, Settings
  components/   # Sidebar, ChatWindow, Upload, Metrics
  services/     # Axios API client
```

## Future (not implemented)

- V2: Tool calling, scheduling, tickets, leads
- V3: LangGraph multi-agent
- V4: Multi-tenant onboarding, workflow builder
