"""Organization settings API."""

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.db.database import get_supabase_client
from app.models.organization import Organization, OrganizationUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _org_id() -> str:
    settings = get_settings()
    if settings.default_organization_id:
        return settings.default_organization_id
    db = get_supabase_client()
    org = db.table("organizations").select("id").limit(1).execute()
    if not org.data:
        raise HTTPException(status_code=500, detail="No organization configured")
    return org.data[0]["id"]


@router.get("", response_model=Organization)
async def get_settings_endpoint():
    db = get_supabase_client()
    result = db.table("organizations").select("*").eq("id", _org_id()).single().execute()
    return Organization(**result.data)


@router.patch("", response_model=Organization)
async def update_settings(body: OrganizationUpdate):
    db = get_supabase_client()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        db.table("organizations")
        .update(updates)
        .eq("id", _org_id())
        .execute()
    )
    return Organization(**result.data[0])
