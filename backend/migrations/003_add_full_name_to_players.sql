-- ============================================================================
-- Migration: Add full_name to players table
-- ============================================================================
-- Adds a full_name column for announcer use (Scorekeepr) while keeping
-- name column for public display (Leaderboard)
-- ============================================================================

ALTER TABLE players
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

-- Add index for full_name lookups
CREATE INDEX IF NOT EXISTS idx_players_full_name
    ON players(full_name)
    WHERE full_name IS NOT NULL;






