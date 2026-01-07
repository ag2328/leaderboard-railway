-- ============================================================================
-- Migration: Add customer_id to players table
-- ============================================================================
-- Adds an optional, unique customer_id field to the players table to link
-- Scorekeepr registrations across seasons.
-- ============================================================================

ALTER TABLE players
    ADD COLUMN IF NOT EXISTS customer_id VARCHAR(64);

-- Unique index on non-null customer_id values
CREATE UNIQUE INDEX IF NOT EXISTS idx_players_customer_id
    ON players(customer_id)
    WHERE customer_id IS NOT NULL;


