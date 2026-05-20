-- Optional: store public contact info in Supabase (run in SQL Editor if you want Settings UI fields).
-- Safe to run multiple times.

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS website_url TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS support_email TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS sales_email TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS phone_number TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS whatsapp_number TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS office_address TEXT;
