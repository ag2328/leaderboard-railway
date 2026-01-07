-- ============================================================================
-- Migration: Fix goalie foreign keys to reference goalies.id instead of players.id
-- ============================================================================
-- Updates goalie_game_stats and goalie_season_stats to reference goalies.id
-- instead of players.id, since goalies are stored in a separate goalies table.
-- ============================================================================

-- Step 1: Drop existing foreign key constraints
ALTER TABLE goalie_game_stats 
    DROP CONSTRAINT IF EXISTS goalie_game_stats_goalie_id_fkey;

ALTER TABLE goalie_season_stats 
    DROP CONSTRAINT IF EXISTS goalie_season_stats_goalie_id_fkey;

-- Step 2: Clear existing data (since goalie_ids reference wrong table)
-- These tables should be empty or only contain invalid references
DELETE FROM goalie_game_stats;
DELETE FROM goalie_season_stats;

-- Step 3: Add new foreign key constraints pointing to goalies.id
ALTER TABLE goalie_game_stats
    ADD CONSTRAINT goalie_game_stats_goalie_id_fkey
    FOREIGN KEY (goalie_id) REFERENCES goalies(id) ON DELETE CASCADE;

ALTER TABLE goalie_season_stats
    ADD CONSTRAINT goalie_season_stats_goalie_id_fkey
    FOREIGN KEY (goalie_id) REFERENCES goalies(id) ON DELETE CASCADE;

-- Step 4: Recreate indexes (they should already exist, but ensure they're correct)
CREATE INDEX IF NOT EXISTS idx_goalie_game_stats_goalie_id ON goalie_game_stats(goalie_id);
CREATE INDEX IF NOT EXISTS idx_goalie_season_stats_goalie_id ON goalie_season_stats(goalie_id);

