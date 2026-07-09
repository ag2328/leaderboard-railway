#!/usr/bin/env python3
"""
Enter game data for Game 109: Maple Leafs @ Canadiens
Week 1, 2026-01-11

Final: Canadiens 3, Maple Leafs 3 (Tie, Shootout - Canadiens win)
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from models import get_season_by_name, get_team_by_id

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
GAME_ID = 109

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)


def get_player_by_jersey(team_id, jersey_number):
    """Get player by jersey number and team."""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, name, jersey_number, team_id
        FROM players
        WHERE team_id = %s AND jersey_number = %s
    """, (team_id, jersey_number))
    player = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(player) if player else None


def main():
    print("=" * 60)
    print("Entering Game 109 Data: Maple Leafs @ Canadiens")
    print("=" * 60)
    print()
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get game info
    cursor.execute("""
        SELECT g.*, ht.name as home_team_name, at.name as away_team_name,
               ht.id as home_team_id, at.id as away_team_id
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.id = %s
    """, (GAME_ID,))
    game = cursor.fetchone()
    
    if not game:
        print(f"ERROR: Game {GAME_ID} not found")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    print(f"Game: {game['away_team_name']} @ {game['home_team_name']}")
    print(f"Date: {game['game_date']}")
    print(f"Status: {game['status']}")
    print()
    
    home_team_id = game['home_team_id']
    away_team_id = game['away_team_id']
    home_team_name = game['home_team_name']
    away_team_name = game['away_team_name']
    
    # Verify teams
    if home_team_name != 'Canadiens' or away_team_name != 'Maple Leafs':
        print(f"ERROR: Game teams don't match expected matchup")
        print(f"Expected: Maple Leafs @ Canadiens")
        print(f"Found: {away_team_name} @ {home_team_name}")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    # Clear any existing events for this game
    print("Clearing existing events...")
    cursor.execute("DELETE FROM events WHERE game_id = %s", (GAME_ID,))
    events_deleted = cursor.rowcount
    print(f"  [OK] Deleted {events_deleted} existing events")
    print()
    
    # CANADIENS GOALS
    print("Creating Canadiens goals...")
    
    # Goal 1: #15 Marley M, Assist: #22 Jake Fife
    scorer_15 = get_player_by_jersey(home_team_id, 15)
    assist_22 = get_player_by_jersey(home_team_id, 22)
    
    if not scorer_15:
        print(f"  [ERROR] Canadiens player #15 not found")
    elif not assist_22:
        print(f"  [ERROR] Canadiens player #22 not found")
    else:
        details = {'assists': [assist_22['id']]} if assist_22 else {}
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_15['id'], json.dumps(details)))
        print(f"  [OK] Goal 1 (P1): {scorer_15['name']} (#15) - Assist: {assist_22['name']} (#22)")
    
    # Goal 2: Unknown player, Assists: #37 Jack Wiseman, #22 Jake Fife
    assist_37 = get_player_by_jersey(home_team_id, 37)
    assist_22_2 = get_player_by_jersey(home_team_id, 22)
    
    if not assist_37:
        print(f"  [ERROR] Canadiens player #37 not found")
    elif not assist_22_2:
        print(f"  [ERROR] Canadiens player #22 not found")
    else:
        # Unknown scorer - create goal event without player_id, with team info in details
        assist_ids = [assist_37['id'], assist_22_2['id']]
        details = {
            'assists': assist_ids,
            'team': 'home',
            'unknown_scorer': True
        }
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', NULL, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, json.dumps(details)))
        print(f"  [OK] Goal 2 (P1): Unknown player - Assists: {assist_37['name']} (#37), {assist_22_2['name']} (#22)")
    
    # CANADIENS PENALTY
    print()
    print("Creating Canadiens penalty...")
    penalty_37 = get_player_by_jersey(home_team_id, 37)
    
    if not penalty_37:
        print(f"  [ERROR] Canadiens player #37 not found")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'penalty', %s, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, penalty_37['id'], json.dumps({'penalty_type': 'checking', 'minutes': 2})))
        print(f"  [OK] Penalty (P1): {penalty_37['name']} (#37) - Checking, 2 minutes")
    
    # MAPLE LEAFS GOALS
    print()
    print("Creating Maple Leafs goals...")
    
    # Goal 1: Unknown player, Assist: #72 Julian Dertavinian
    assist_72 = get_player_by_jersey(away_team_id, 72)
    
    if not assist_72:
        print(f"  [ERROR] Maple Leafs player #72 not found")
    else:
        details = {
            'assists': [assist_72['id']],
            'team': 'away',
            'unknown_scorer': True
        }
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', NULL, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, json.dumps(details)))
        print(f"  [OK] Goal 1 (P1): Unknown player - Assist: {assist_72['name']} (#72)")
    
    # Goal 2: Unknown player, Assist: #29 Jack Pollard
    assist_29 = get_player_by_jersey(away_team_id, 29)
    
    if not assist_29:
        print(f"  [ERROR] Maple Leafs player #29 not found")
    else:
        details = {
            'assists': [assist_29['id']],
            'team': 'away',
            'unknown_scorer': True
        }
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', NULL, 2, 0, %s, NOW(), NOW())
        """, (GAME_ID, json.dumps(details)))
        print(f"  [OK] Goal 2 (P2): Unknown player - Assist: {assist_29['name']} (#29)")
    
    # Goal 3: Unknown player (no assists)
    details = {
        'team': 'away',
        'unknown_scorer': True
    }
    cursor.execute("""
        INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
        VALUES (%s, 'goal', NULL, 3, 0, %s, NOW(), NOW())
    """, (GAME_ID, json.dumps(details)))
    print(f"  [OK] Goal 3 (P3): Unknown player - No assists")
    
    conn.commit()
    print()
    print("[OK] All events created")
    print()
    
    # Create game summary
    print("Creating game summary...")
    from stats_calculator import calculate_game_summary
    
    summary = calculate_game_summary(GAME_ID, force_update=True)
    if summary:
        # Update with shootout info
        cursor.execute("""
            UPDATE game_summaries
            SET went_to_shootout = true,
                updated_at = NOW()
            WHERE game_id = %s
        """, (GAME_ID,))
        conn.commit()
        print(f"  [OK] Game summary created")
        print(f"    Score: Maple Leafs 3 - 3 Canadiens")
        print(f"    Result: Tie, Shootout - Canadiens win")
    else:
        print("  [WARN] Could not create game summary")
    
    # Lock the game
    print()
    print("Locking game...")
    cursor.execute("""
        UPDATE games
        SET status = 'locked',
            updated_at = NOW()
        WHERE id = %s
    """, (GAME_ID,))
    conn.commit()
    print(f"  [OK] Game {GAME_ID} locked")
    
    cursor.close()
    conn.close()
    
    print()
    print("=" * 60)
    print("Game 109 Data Entry Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Process the game: python backend/sync_service.py (or use API endpoint)")
    print("2. Verify stats in the leaderboard")
    print()


if __name__ == '__main__':
    main()


