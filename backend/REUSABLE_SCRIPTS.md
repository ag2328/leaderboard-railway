# Reusable Scripts for Future Seasons

This document lists all reusable scripts that should be kept for future seasons.

## Core Application Files (Keep)
- `app.py` - Flask backend API
- `models.py` - Database models and queries
- `stats_calculator.py` - Stats calculation engine (updated to match Fall 2025 formula)
- `sync_service.py` - Sync service for processing games and updating stats

## Reusable Utility Scripts (Keep)

### Season Management
- `setup_season.py` - Create new season records
- `check_seasons.py` - Check seasons and standings in database

### Data Loading
- `load_schedule.py` - Load schedule data from JSON file
- `load_players.py` - Load player roster data
- `load_goalies.py` - Load goalie roster data

### Stats Management
- `zero_all_stats.py` - Reset all stats to zero (useful between seasons)
- `reset_all_stats.py` - Alternative reset by recalculating (slower but more thorough)
- `recalculate_all_player_stats.py` - Recalculate all player season stats

### Testing & Debugging
- `simulate_test_game.py` - Simulate test games for troubleshooting
  - Use: `python backend/simulate_test_game.py create` - Create test games
  - Use: `python backend/simulate_test_game.py reset` - Reset test games
  - Use: `python backend/simulate_test_game.py status` - Check test game status

### Data Export
- `export_roster.py` - Export all players and goalies to text file for review

## Migration Files (Keep All)
- `migrations/001_leaderboard_schema.sql` - Initial schema
- `migrations/002_add_customer_id_to_players.sql` - Add customer_id field
- `migrations/003_add_full_name_to_players.sql` - Add full_name field
- `migrations/004_fix_goalie_foreign_keys.sql` - Fix goalie foreign keys
- `migrations/005_add_name_fields_to_goalies.sql` - Add name fields to goalies
- `migrations/run_migrations.py` - Run migrations script

## Configuration Files
- `requirements.txt` - Python dependencies
- `__init__.py` - Python package marker






