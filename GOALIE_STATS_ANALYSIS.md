# Goalie Stats Tracking Analysis

## Current State

### Original Repo (temp_original_repo)
- **Data Source**: Google Sheets CSV files parsed per week
- **Goalie Stats Format**: 
  - Columns: `Shot Attempts`, `Goals Allowed`, `Saves`, `Save %`
  - Parsed from CSV section labeled "Goalie Stats"
- **Display**:
  - **Season Stats**: Shown in player stats section with table:
    - # | Name | SA | GA | SV | SV%
  - **Per-Game Stats**: Not explicitly shown in game cards, but data was available

### Current System (Leaderboard)
- **Database Tables**:
  1. `goalie_game_stats` - Per-game goalie statistics (NOT POPULATED)
     - Fields: `shots_against`, `goals_allowed`, `saves`, `save_percentage`
     - Foreign key: `goalie_id` → `goalies.id` (fixed in migration 004)
  2. `goalie_season_stats` - Season aggregates (POPULATED)
     - Fields: `shots_against`, `goals_allowed`, `saves`, `save_percentage`
     - Calculated from `game_summaries` table

- **Data Source**: ScorekeeprDB → `game_summaries` table
  - `home_team_shots` / `away_team_shots` (shots on goal)
  - `home_team_score` / `away_team_score` (goals)

- **Current Implementation**:
  - ✅ `calculate_goalie_season_stats()` - Works, aggregates from game_summaries
  - ❌ `calculate_goalie_game_stats()` - Returns `None` (stub function)
  - ✅ Frontend displays season goalie stats in player stats section
  - ❌ Game cards do NOT show goalie stats per game

## What Needs to Be Done

### 1. Implement `calculate_goalie_game_stats()`

**Location**: `backend/stats_calculator.py` (line 173)

**Logic**:
```python
For each game:
  - Get game_summary (home_team_shots, away_team_shots, home_team_score, away_team_score)
  - Get active goalies for both teams from goalies table
  - For home team goalie:
    * shots_against = away_team_shots
    * goals_allowed = away_team_score
  - For away team goalie:
    * shots_against = home_team_shots
    * goals_allowed = home_team_score
  - Calculate:
    * saves = shots_against - goals_allowed
    * save_percentage = (saves / shots_against * 100) if shots_against > 0 else 0
  - Insert/update goalie_game_stats table
```

**Note**: Assumes one goalie per team per game. If multiple goalies play, we'd need to track which goalie was in net (not currently supported).

### 2. Add API Endpoint for Goalie Game Stats

**Location**: `backend/app.py`

**Endpoint**: `GET /api/games/<game_id>/goalies`

**Returns**: Array of goalie stats for the game:
```json
{
  "goalies": [
    {
      "goalie_id": 1,
      "name": "London C.",
      "full_name": "London Claxton",
      "team_id": 1,
      "team_name": "Bruins",
      "shots_against": 25,
      "goals_allowed": 2,
      "saves": 23,
      "save_percentage": 0.920
    }
  ]
}
```

### 3. Update Game Cards to Display Goalie Stats

**Location**: `frontend/js/game-cards.js`

**Current**: Game cards show:
- Date, Outcome (W/L/T)
- Teams with logos
- Score
- Team shots

**Enhancement**: Add goalie stats section:
```
Goalie Stats:
[Bruins Logo] London C. - 23/25 (0.920)
[Opponent Logo] Goalie Name - X/Y (Z.ZZZ)
```

**Note**: Only show for completed games (when summary exists).

### 4. Update Sync Service

**Location**: `backend/sync_service.py`

**Current**: Line 72 calls `calculate_goalie_game_stats()` but it does nothing.

**Action**: Ensure the function is properly implemented and called during game processing.

## Data Flow

```
ScorekeeprDB
    ↓
game_summaries table
    ↓
calculate_goalie_game_stats(game_id)
    ↓
goalie_game_stats table (per-game)
    ↓
calculate_goalie_season_stats(goalie_id, season_id)
    ↓
goalie_season_stats table (season aggregates)
    ↓
Frontend API
    ↓
Display in UI
```

## Implementation Priority

1. **High**: Implement `calculate_goalie_game_stats()` - Core functionality
2. **High**: Add API endpoint for game goalie stats - Needed for frontend
3. **Medium**: Update game cards to show goalie stats - User-facing feature
4. **Low**: Handle multiple goalies per game - Edge case (if needed)

## Questions to Consider

1. **Multiple Goalies**: What if a team uses multiple goalies in one game? Currently assumes one goalie per team.
2. **Game Card Display**: Should goalie stats be:
   - Always visible on game cards?
   - Expandable/collapsible?
   - Only on team page, not standings page?
3. **Data Accuracy**: Are `game_summaries` shots accurate? Or do we need to track shots differently?

