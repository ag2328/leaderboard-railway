-- ============================================================================
-- Add Points Column to Player Season Stats
-- ============================================================================
-- 
-- Adds a points column to player_season_stats table.
-- Points = Goals + Assists
-- 
-- Penalties column remains in the table for future reporting.
-- ============================================================================

-- Add points column to player_season_stats table
ALTER TABLE player_season_stats 
ADD COLUMN IF NOT EXISTS points INTEGER NOT NULL DEFAULT 0;

-- Update existing records to calculate points (goals + assists)
UPDATE player_season_stats 
SET points = goals + assists;

-- Add comment
COMMENT ON COLUMN player_season_stats.points IS 'Player points (goals + assists)';



