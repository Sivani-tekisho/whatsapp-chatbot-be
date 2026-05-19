"""Document ingestion pipeline."""

from uuid import UUID

from supabase import Client

from app.rag.chunking import split_text
from app.rag.embeddings import EmbeddingService


class DocumentIngestor:
    def __init__(self, db: Client, embedding_service: EmbeddingService) -> None:
        self._db = db
        self._embeddings = embedding_service

    def ingest(
        self,
        organization_id: UUID,
        title: str,
        content: str,
        source_type: str = "upload",
        source_url: str | None = None,
    ) -> tuple[UUID, int]:
        doc_result = (
            self._db.table("documents")
            .insert(
                {
                    "organization_id": str(organization_id),
                    "title": title,
                    "content": content[:50000] if content else None,
                    "source_type": source_type,
                    "source_url": source_url,
                }
            )
            .execute()
        )
        document = doc_result.data[0]
        document_id = UUID(document["id"])

        chunks = split_text(content)
        if not chunks:
            return document_id, 0

        embeddings = self._embeddings.embed_texts(chunks)
        rows = [
            {
                "document_id": str(document_id),
                "chunk_text": chunk,
                "embedding": embedding,
                "chunk_index": idx,
            }
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        batch_size = 50
        for i in range(0, len(rows), batch_size):
            self._db.table("document_chunks").insert(rows[i : i + batch_size]).execute()

        return document_id, len(chunks)
