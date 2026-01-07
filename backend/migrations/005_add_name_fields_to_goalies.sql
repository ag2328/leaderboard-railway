-- ============================================================================
-- Migration: Add name and full_name fields to goalies table
-- ============================================================================
-- Adds public display name (name) and announcer name (full_name) to goalies
-- to match players table structure.
-- ============================================================================

ALTER TABLE goalies
    ADD COLUMN IF NOT EXISTS name VARCHAR(255);

ALTER TABLE goalies
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

-- Update existing goalies to populate name and full_name from first_name and last_name
UPDATE goalies
SET 
    name = first_name || ' ' || SUBSTRING(last_name, 1, 1) || '.',
    full_name = first_name || ' ' || last_name
WHERE name IS NULL OR full_name IS NULL;

-- Add index for name lookups
CREATE INDEX IF NOT EXISTS idx_goalies_name
    ON goalies(name)
    WHERE name IS NOT NULL;

