-- ============================================================================
-- Leaderboard Database Schema Migration
-- ============================================================================
-- 
-- This migration creates tables for the leaderboard application:
-- - seasons: Season records
-- - game_summaries: Per-game statistics
-- - goalie_game_stats: Per-game goalie statistics
-- - team_standings: Aggregated team standings per season
-- - player_season_stats: Aggregated player statistics per season
-- - goalie_season_stats: Aggregated goalie statistics per season
--
-- Also modifies existing games table to add outcome tracking
-- ============================================================================

-- Seasons table
CREATE TABLE IF NOT EXISTS seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Game summaries table
CREATE TABLE IF NOT EXISTS game_summaries (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    
    -- Team scores
    home_team_score INTEGER NOT NULL DEFAULT 0,
    away_team_score INTEGER NOT NULL DEFAULT 0,
    
    -- Shots on goal
    home_team_shots INTEGER NOT NULL DEFAULT 0,
    away_team_shots INTEGER NOT NULL DEFAULT 0,
    
    -- Game outcome
    game_outcome VARCHAR(50) NOT NULL,
    winner_team_id INTEGER REFERENCES teams(id),
    
    -- Overtime/Shootout info
    went_to_overtime BOOLEAN DEFAULT false,
    went_to_shootout BOOLEAN DEFAULT false,
    
    -- Processing status
    processed_at TIMESTAMP,
    awaiting_manual_update BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(game_id)
);

-- Goalie game stats table
CREATE TABLE IF NOT EXISTS goalie_game_stats (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    goalie_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    
    shots_against INTEGER NOT NULL DEFAULT 0,
    goals_allowed INTEGER NOT NULL DEFAULT 0,
    saves INTEGER NOT NULL DEFAULT 0,
    save_percentage DECIMAL(5,3),
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(game_id, goalie_id)
);

-- Team standings table
CREATE TABLE IF NOT EXISTS team_standings (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    
    games_played INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    ties INTEGER NOT NULL DEFAULT 0,
    tiebreaker_wins INTEGER NOT NULL DEFAULT 0,
    tiebreaker_losses INTEGER NOT NULL DEFAULT 0,
    
    goals_scored INTEGER NOT NULL DEFAULT 0,
    goals_against INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(team_id, season_id)
);

-- Player season stats table
CREATE TABLE IF NOT EXISTS player_season_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    
    goals INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    penalties INTEGER NOT NULL DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(player_id, season_id)
);

-- Goalie season stats table
CREATE TABLE IF NOT EXISTS goalie_season_stats (
    id SERIAL PRIMARY KEY,
    goalie_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    
    shots_against INTEGER NOT NULL DEFAULT 0,
    goals_allowed INTEGER NOT NULL DEFAULT 0,
    saves INTEGER NOT NULL DEFAULT 0,
    save_percentage DECIMAL(5,3),
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(goalie_id, season_id)
);

-- Modify games table to add outcome tracking
ALTER TABLE games ADD COLUMN IF NOT EXISTS season_id INTEGER REFERENCES seasons(id);
ALTER TABLE games ADD COLUMN IF NOT EXISTS game_outcome VARCHAR(50);
ALTER TABLE games ADD COLUMN IF NOT EXISTS went_to_overtime BOOLEAN DEFAULT false;
ALTER TABLE games ADD COLUMN IF NOT EXISTS went_to_shootout BOOLEAN DEFAULT false;
ALTER TABLE games ADD COLUMN IF NOT EXISTS winner_team_id INTEGER REFERENCES teams(id);
ALTER TABLE games ADD COLUMN IF NOT EXISTS leaderboard_processed_at TIMESTAMP;

-- Ensure events table has event_type (should already exist, but make sure)
-- ALTER TABLE events ADD COLUMN IF NOT EXISTS event_type VARCHAR(50);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_game_summaries_game_id ON game_summaries(game_id);
CREATE INDEX IF NOT EXISTS idx_game_summaries_season_id ON game_summaries(season_id);
CREATE INDEX IF NOT EXISTS idx_goalie_game_stats_game_id ON goalie_game_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_goalie_game_stats_goalie_id ON goalie_game_stats(goalie_id);
CREATE INDEX IF NOT EXISTS idx_team_standings_team_id ON team_standings(team_id);
CREATE INDEX IF NOT EXISTS idx_team_standings_season_id ON team_standings(season_id);
CREATE INDEX IF NOT EXISTS idx_player_season_stats_player_id ON player_season_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_player_season_stats_season_id ON player_season_stats(season_id);
CREATE INDEX IF NOT EXISTS idx_goalie_season_stats_goalie_id ON goalie_season_stats(goalie_id);
CREATE INDEX IF NOT EXISTS idx_goalie_season_stats_season_id ON goalie_season_stats(season_id);
CREATE INDEX IF NOT EXISTS idx_games_season_id ON games(season_id);
CREATE INDEX IF NOT EXISTS idx_games_leaderboard_processed_at ON games(leaderboard_processed_at);

-- Comments
COMMENT ON TABLE seasons IS 'Hockey seasons (e.g., Spring 2026)';
COMMENT ON TABLE game_summaries IS 'Per-game statistics for leaderboard display';
COMMENT ON TABLE goalie_game_stats IS 'Per-game goalie statistics';
COMMENT ON TABLE team_standings IS 'Aggregated team standings per season';
COMMENT ON TABLE player_season_stats IS 'Aggregated player statistics per season';
COMMENT ON TABLE goalie_season_stats IS 'Aggregated goalie statistics per season';

