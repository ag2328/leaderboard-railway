"""
Sync service for processing games and updating stats.

Handles:
- Processing pending games (locked but not processed)
- Calculating game summaries
- Updating aggregated stats (standings, player stats, goalie stats)
- Manual vs automatic sync modes
"""

import os
from datetime import datetime
from models import get_pending_games, get_active_season, get_all_teams
from stats_calculator import (
    calculate_game_summary,
    calculate_goalie_game_stats,
    calculate_team_standings,
    calculate_player_season_stats,
    calculate_goalie_season_stats
)
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
AUTO_SYNC_ENABLED = os.getenv('AUTO_SYNC_ENABLED', 'false').lower() == 'true'


def get_db_connection():
    """Get a database connection."""
    return psycopg2.connect(DATABASE_URL)


def process_pending_games(season_id=None):
    """
    Process all pending games (locked but not yet processed).
    
    For each pending game:
    1. Calculate game summary
    2. Calculate goalie game stats
    3. Mark as processed
    4. If auto-sync enabled, update aggregated stats immediately
    5. Otherwise, mark as awaiting manual update
    """
    if not season_id:
        season = get_active_season()
        if not season:
            return {'error': 'No active season found'}
        season_id = season['id']
    
    pending_games = get_pending_games(season_id)
    
    if not pending_games:
        return {
            'processed': 0,
            'message': 'No pending games to process'
        }
    
    processed_count = 0
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for game in pending_games:
        try:
            # Calculate game summary
            summary = calculate_game_summary(game['id'])
            if not summary:
                continue
            
            # Calculate goalie game stats (simplified for now)
            calculate_goalie_game_stats(game['id'])
            
            # Mark game as processed
            cursor.execute("""
                UPDATE games
                SET leaderboard_processed_at = %s
                WHERE id = %s
            """, (datetime.now(), game['id']))
            
            # If auto-sync enabled, update aggregated stats
            if AUTO_SYNC_ENABLED:
                update_aggregated_stats_for_game(game['id'], season_id)
            else:
                # Mark game_summary as awaiting manual update
                cursor.execute("""
                    UPDATE game_summaries
                    SET awaiting_manual_update = true
                    WHERE game_id = %s
                """, (game['id'],))
            
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing game {game['id']}: {e}")
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'processed': processed_count,
        'total_pending': len(pending_games),
        'message': f'Processed {processed_count} games'
    }


def process_single_game(game_id):
    """
    Process a single game by ID.
    
    Used when scorekeepr_lite locks a game and wants immediate processing.
    
    Returns:
        dict: Result with success status and message
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get game info
        cursor.execute("""
            SELECT id, status, season_id, home_team_id, away_team_id
            FROM games
            WHERE id = %s
        """, (game_id,))
        game = cursor.fetchone()
        
        if not game:
            return {'error': f'Game {game_id} not found'}
        
        if game[1] != 'locked':  # status
            return {'error': f'Game {game_id} is not locked (status: {game[1]})'}
        
        season_id = game[2]
        if not season_id:
            return {'error': f'Game {game_id} has no season_id'}
        
        # Calculate game summary
        summary = calculate_game_summary(game_id)
        if not summary:
            return {'error': f'Failed to calculate summary for game {game_id}'}
        
        # Calculate goalie game stats
        calculate_goalie_game_stats(game_id)
        
        # Mark game as processed
        cursor.execute("""
            UPDATE games
            SET leaderboard_processed_at = %s
            WHERE id = %s
        """, (datetime.now(), game_id))
        
        # Always update aggregated stats when processing a single game
        # (called from scorekeepr_lite - user expects immediate results)
        update_aggregated_stats_for_game(game_id, season_id)
        
        conn.commit()
        
        return {
            'success': True,
            'game_id': game_id,
            'message': f'Game {game_id} processed successfully'
        }
        
    except Exception as e:
        conn.rollback()
        return {'error': f'Error processing game {game_id}: {str(e)}'}
    finally:
        cursor.close()
        conn.close()


def update_aggregated_stats_for_game(game_id, season_id):
    """
    Update all aggregated stats for a specific game.
    
    Updates:
    - Team standings for both teams
    - Player season stats for all players in the game
    - Goalie season stats for goalies in the game
    """
    game = None
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get game info
    cursor.execute("""
        SELECT home_team_id, away_team_id FROM games WHERE id = %s
    """, (game_id,))
    game = cursor.fetchone()
    
    if not game:
        cursor.close()
        conn.close()
        return
    
    home_team_id = game[0]
    away_team_id = game[1]
    
    # Update team standings for both teams
    calculate_team_standings(home_team_id, season_id)
    calculate_team_standings(away_team_id, season_id)
    
    # Get all players who participated in this game
    cursor.execute("""
        SELECT DISTINCT player_id FROM events
        WHERE game_id = %s AND player_id IS NOT NULL
    """, (game_id,))
    player_ids = [row[0] for row in cursor.fetchall()]
    
    # Update player stats
    for player_id in player_ids:
        try:
            calculate_player_season_stats(player_id, season_id)
        except Exception as e:
            print(f"Error updating player {player_id} stats: {e}")
    
    # Get goalies for both teams from goalies table
    cursor.execute("""
        SELECT id FROM goalies
        WHERE team_id IN (%s, %s) AND status = 'active'
    """, (home_team_id, away_team_id))
    goalie_ids = [row[0] for row in cursor.fetchall()]
    
    # Update goalie stats
    for goalie_id in goalie_ids:
        try:
            calculate_goalie_season_stats(goalie_id, season_id)
        except Exception as e:
            print(f"Error updating goalie {goalie_id} stats: {e}")
    
    # Mark game_summary as no longer awaiting update
    cursor.execute("""
        UPDATE game_summaries
        SET awaiting_manual_update = false
        WHERE game_id = %s
    """, (game_id,))
    
    conn.commit()
    cursor.close()
    conn.close()


def manual_sync_trigger(season_id=None):
    """
    Manually trigger stats update for all processed games awaiting update.
    
    This is called when auto-sync is disabled and admin wants to update stats.
    """
    if not season_id:
        season = get_active_season()
        if not season:
            return {'error': 'No active season found'}
        season_id = season['id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get games awaiting manual update
    cursor.execute("""
        SELECT g.id FROM games g
        JOIN game_summaries gs ON g.id = gs.game_id
        WHERE g.season_id = %s
          AND g.status = 'locked'
          AND gs.awaiting_manual_update = true
    """, (season_id,))
    game_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    updated_count = 0
    for game_id in game_ids:
        try:
            update_aggregated_stats_for_game(game_id, season_id)
            updated_count += 1
        except Exception as e:
            print(f"Error updating stats for game {game_id}: {e}")
    
    return {
        'updated': updated_count,
        'total_awaiting': len(game_ids),
        'message': f'Updated stats for {updated_count} games'
    }


def recalculate_all_stats(season_id=None):
    """
    Recalculate all stats for a season.
    
    Useful for:
    - Initial setup
    - After data corrections
    - Debugging
    """
    if not season_id:
        season = get_active_season()
        if not season:
            return {'error': 'No active season found'}
        season_id = season['id']
    
    # Recalculate all team standings
    teams = get_all_teams()
    for team in teams:
        try:
            calculate_team_standings(team['id'], season_id)
        except Exception as e:
            print(f"Error recalculating standings for team {team['id']}: {e}")
    
    # Recalculate all player stats
    # (This would require getting all players - simplified for now)
    
    return {
        'message': 'Recalculation complete',
        'teams_updated': len(teams)
    }


def get_sync_status(season_id=None):
    """
    Get current sync status.
    
    Returns:
    - Pending games count
    - Games awaiting manual update count
    - Auto-sync status
    """
    if not season_id:
        season = get_active_season()
        if not season:
            return {'error': 'No active season found'}
        season_id = season['id']
    
    pending_games = get_pending_games(season_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) FROM game_summaries gs
        JOIN games g ON gs.game_id = g.id
        WHERE g.season_id = %s
          AND gs.awaiting_manual_update = true
    """, (season_id,))
    awaiting_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return {
        'pending_games': len(pending_games),
        'awaiting_manual_update': awaiting_count,
        'auto_sync_enabled': AUTO_SYNC_ENABLED,
        'season_id': season_id
    }

