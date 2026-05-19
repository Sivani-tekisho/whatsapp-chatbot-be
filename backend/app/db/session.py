"""Dependency injection helpers for database access."""

from typing import Annotated

from fastapi import Depends
from supabase import Client

from app.db.database import get_supabase_client


def get_db() -> Client:
    return get_supabase_client()


DbDep = Annotated[Client, Depends(get_db)]
