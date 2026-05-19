#!/usr/bin/env python3
"""Bulk-ingest local documents into Supabase knowledge base.

Usage:
    python -m scripts.ingest_existing_docs --path ./data/docs
"""

import argparse
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.database import get_supabase_client
from app.dependencies import get_document_ingestor
from app.api.documents import _extract_docx, _extract_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest local docs into RAG")
    parser.add_argument("--path", required=True, help="Folder with PDF/DOCX files")
    args = parser.parse_args()

    folder = Path(args.path)
    if not folder.is_dir():
        print(f"Not a directory: {folder}")
        sys.exit(1)

    settings = get_settings()
    db = get_supabase_client()
    org_id = settings.default_organization_id
    if not org_id:
        org = db.table("organizations").select("id").limit(1).execute()
        org_id = org.data[0]["id"]

    ingestor = get_document_ingestor()
    total_chunks = 0

    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue
        lower = file_path.name.lower()
        try:
            if lower.endswith(".pdf"):
                text = _extract_pdf(file_path.read_bytes())
                source_type = "pdf"
            elif lower.endswith((".doc", ".docx")):
                text = _extract_docx(file_path.read_bytes())
                source_type = "doc"
            else:
                continue

            if not text.strip():
                print(f"Skip (empty): {file_path}")
                continue

            doc_id, chunks = ingestor.ingest(
                organization_id=UUID(org_id),
                title=file_path.name,
                content=text,
                source_type=source_type,
            )
            total_chunks += chunks
            print(f"OK {file_path.name} -> {doc_id} ({chunks} chunks)")
        except Exception as exc:
            print(f"FAIL {file_path}: {exc}")

    print(f"Done. Total chunks: {total_chunks}")


if __name__ == "__main__":
    main()
