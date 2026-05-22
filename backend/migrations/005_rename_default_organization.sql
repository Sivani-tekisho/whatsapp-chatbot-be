-- Run once in Supabase SQL Editor if the bot still says "Default Organization"
UPDATE organizations
SET name = 'Tekisho Infotech'
WHERE lower(trim(name)) IN ('default organization', 'default org');
