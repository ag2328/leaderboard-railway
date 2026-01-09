#!/usr/bin/env python3
"""
Complete Data Reset Script

Deletes ALL entered game data (fact tables) while preserving structural data (dimension tables).

DELETES (fact/transactional data):
- All events (goals, penalties, etc.)
- All game_summaries
- All goalie_game_stats
- All goalie_season_stats
- All player_season_stats
- All team_standings

PRESERVES (dimension/reference data):
- Teams
- Players
- Goalies
- Seasons
- Games (schedule) - but resets status to 'pending' and clears processed timestamps

This is a development tool for wiping the slate clean.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

# Get season
from models import get_season_by_name
season = get_season_by_name('Spring 2026')
if not season:
    print("ERROR: Season 'Spring 2026' not found")
    sys.exit(1)

season_id = season['id']

def main():
    print("=" * 60)
    print("COMPLETE DATA RESET - Delete All Entered Game Data")
    print("=" * 60)
    print()
    print("This will DELETE:")
    print("  - All events (goals, penalties, etc.)")
    print("  - All game_summaries")
    print("  - All goalie_game_stats")
    print("  - All goalie_season_stats")
    print("  - All player_season_stats")
    print("  - All team_standings")
    print()
    print("This will PRESERVE:")
    print("  - Teams")
    print("  - Players")
    print("  - Goalies")
    print("  - Seasons")
    print("  - Games (schedule) - but reset status to 'pending'")
    print()
    
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != 'yes':
        print("Reset cancelled.")
        return
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # 1. Delete all events for games in this season
        print("\n1. Deleting all events...")
        cursor.execute("""
            DELETE FROM events
            WHERE game_id IN (SELECT id FROM games WHERE season_id = %s)
        """, (season_id,))
        events_deleted = cursor.rowcount
        print(f"  [OK] Deleted {events_deleted} events")
        
        # 2. Delete all game_summaries for this season
        print("\n2. Deleting all game_summaries...")
        cursor.execute("""
            DELETE FROM game_summaries
            WHERE season_id = %s
        """, (season_id,))
        summaries_deleted = cursor.rowcount
        print(f"  [OK] Deleted {summaries_deleted} game_summaries")
        
        # 3. Delete all goalie_game_stats for games in this season
        print("\n3. Deleting all goalie_game_stats...")
        cursor.execute("""
            DELETE FROM goalie_game_stats
            WHERE game_id IN (SELECT id FROM games WHERE season_id = %s)
        """, (season_id,))
        goalie_game_stats_deleted = cursor.rowcount
        print(f"  [OK] Deleted {goalie_game_stats_deleted} goalie_game_stats")
        
        # 4. Delete all goalie_season_stats for this season
        print("\n4. Deleting all goalie_season_stats...")
        cursor.execute("""
            DELETE FROM goalie_season_stats
            WHERE season_id = %s
        """, (season_id,))
        goalie_season_stats_deleted = cursor.rowcount
        print(f"  [OK] Deleted {goalie_season_stats_deleted} goalie_season_stats")
        
        # 5. Delete all player_season_stats for this season
        print("\n5. Deleting all player_season_stats...")
        cursor.execute("""
            DELETE FROM player_season_stats
            WHERE season_id = %s
        """, (season_id,))
        player_season_stats_deleted = cursor.rowcount
        print(f"  [OK] Deleted {player_season_stats_deleted} player_season_stats")
        
        # 6. Delete all team_standings for this season
        print("\n6. Deleting all team_standings...")
        cursor.execute("""
            DELETE FROM team_standings
            WHERE season_id = %s
        """, (season_id,))
        team_standings_deleted = cursor.rowcount
        print(f"  [OK] Deleted {team_standings_deleted} team_standings")
        
        # 7. Reset games (unlock and clear processed timestamps)
        print("\n7. Resetting games (unlock and clear timestamps)...")
        cursor.execute("""
            UPDATE games
            SET status = 'pending',
                leaderboard_processed_at = NULL,
                game_outcome = NULL,
                went_to_overtime = false,
                went_to_shootout = false,
                winner_team_id = NULL,
                updated_at = NOW()
            WHERE season_id = %s
        """, (season_id,))
        games_reset = cursor.rowcount
        print(f"  [OK] Reset {games_reset} games to 'pending' status")
        
        # 8. Delete game_goalies entries for games in this season
        print("\n8. Deleting all game_goalies entries...")
        cursor.execute("""
            DELETE FROM game_goalies
            WHERE game_id IN (SELECT id FROM games WHERE season_id = %s)
        """, (season_id,))
        game_goalies_deleted = cursor.rowcount
        print(f"  [OK] Deleted {game_goalies_deleted} game_goalies entries")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("COMPLETE RESET SUCCESSFUL!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  Events deleted: {events_deleted}")
        print(f"  Game summaries deleted: {summaries_deleted}")
        print(f"  Goalie game stats deleted: {goalie_game_stats_deleted}")
        print(f"  Goalie season stats deleted: {goalie_season_stats_deleted}")
        print(f"  Player season stats deleted: {player_season_stats_deleted}")
        print(f"  Team standings deleted: {team_standings_deleted}")
        print(f"  Games reset: {games_reset}")
        print(f"  Game goalies deleted: {game_goalies_deleted}")
        print()
        print("All entered game data has been deleted.")
        print("Rosters, teams, goalies, and schedule remain intact.")
        print()
        
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()

