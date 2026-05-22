"""
Public company details for the WhatsApp bot (fill this file in).

Priority when the model sees contact info:
  1. Supabase `organizations` row (if those columns exist and are set)
  2. Environment variables in backend/.env (see app.core.config.Settings)
  3. The values below — used when 1 and 2 are empty

The prompt template is prompts/whatsapp_system_prompt.txt; it only has {{PLACEHOLDERS}},
not your real phone or email. Those are injected from the sources above.
"""

# Company / product name (also used if DB `name` and env COMPANY_NAME are empty)
COMPANY_NAME = "Tekisho Infotech"

# Customer-facing site
WEBSITE_URL = "https://www.tekisho.ai/"

# Emails shown to users in replies (not SMTP credentials)
SUPPORT_EMAIL = "contact@tekisho.ai"
SALES_EMAIL = ""  # optional; leave empty to use support only

# Human-readable numbers for the prompt (not Meta WHATSAPP_PHONE_NUMBER_ID)
PHONE_NUMBER = "+91 9059443516"
WHATSAPP_NUMBER = ""  # optional display number for users (e.g. +91 9059443516)

OFFICE_ADDRESS = (
    "Tekisho Infotech Pvt. Ltd., 505 A, 5th Floor, Techno 1, "
    "Gachibowli Road, Raidurg, Hyderabad, Telangana - 500032"
)

# DB migration seed names — treat as unset so COMPANY_NAME below is used
_DB_NAME_PLACEHOLDERS = frozenset(
    {
        "default organization",
        "default org",
        "company assistant",
    }
)


def resolve_company_name(db_name: str | None = None, env_name: str | None = None) -> str:
    """Display name: real DB name → company_branding.py → env → fallback."""
    n = (db_name or "").strip()
    if n and n.lower() not in _DB_NAME_PLACEHOLDERS:
        return n
    if (COMPANY_NAME or "").strip():
        return COMPANY_NAME.strip()
    if (env_name or "").strip():
        return env_name.strip()
    return "Tekisho Infotech"
