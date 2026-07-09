#!/usr/bin/env python3
"""
Enter game data for Game 110: Red Wings @ Bruins
Week 1, 2026-01-11

Final: Bruins 2, Red Wings 4
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from models import get_season_by_name

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
GAME_ID = 110

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
    print("Entering Game 110 Data: Red Wings @ Bruins")
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
    if home_team_name != 'Bruins' or away_team_name != 'Red Wings':
        print(f"ERROR: Game teams don't match expected matchup")
        print(f"Expected: Red Wings @ Bruins")
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
    
    # BRUINS GOALS
    print("Creating Bruins goals...")
    
    # Goal 1: #61 Kaiden Sanchez (no assists)
    scorer_61 = get_player_by_jersey(home_team_id, 61)
    
    if not scorer_61:
        print(f"  [WARN] Bruins player #61 not found - creating as unknown player")
        details = {'team': 'home', 'unknown_scorer': True, 'jersey_number': 61}
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', NULL, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, json.dumps(details)))
        print(f"  [OK] Goal 1 (P1): Unknown player #61 - No assists")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_61['id'], json.dumps({})))
        print(f"  [OK] Goal 1 (P1): {scorer_61['name']} (#61) - No assists")
    
    # Goal 2: #61 Kaiden Sanchez (no assists)
    if not scorer_61:
        details = {'team': 'home', 'unknown_scorer': True, 'jersey_number': 61}
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', NULL, 2, 0, %s, NOW(), NOW())
        """, (GAME_ID, json.dumps(details)))
        print(f"  [OK] Goal 2 (P2): Unknown player #61 - No assists")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 2, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_61['id'], json.dumps({})))
        print(f"  [OK] Goal 2 (P2): {scorer_61['name']} (#61) - No assists")
    
    # BRUINS PENALTY
    print()
    print("Creating Bruins penalty...")
    penalty_7 = get_player_by_jersey(home_team_id, 7)
    
    if not penalty_7:
        print(f"  [ERROR] Bruins player #7 not found")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'penalty', %s, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, penalty_7['id'], json.dumps({})))
        print(f"  [OK] Penalty (P1): {penalty_7['name']} (#7)")
    
    # RED WINGS GOALS
    print()
    print("Creating Red Wings goals...")
    
    # Goal 1: #12 Jason Groller
    scorer_12 = get_player_by_jersey(away_team_id, 12)
    
    if not scorer_12:
        print(f"  [ERROR] Red Wings player #12 not found")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_12['id'], json.dumps({})))
        print(f"  [OK] Goal 1 (P1): {scorer_12['name']} (#12) - No assists")
    
    # Goal 2: #12 Jason Groller
    if scorer_12:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 2, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_12['id'], json.dumps({})))
        print(f"  [OK] Goal 2 (P2): {scorer_12['name']} (#12) - No assists")
    
    # Goal 3: #19 Josiah Ramirez
    scorer_19 = get_player_by_jersey(away_team_id, 19)
    
    if not scorer_19:
        print(f"  [ERROR] Red Wings player #19 not found")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 3, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_19['id'], json.dumps({})))
        print(f"  [OK] Goal 3 (P3): {scorer_19['name']} (#19) - No assists")
    
    # Goal 4: #19 Josiah Ramirez
    if scorer_19:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', %s, 3, 0, %s, NOW(), NOW())
        """, (GAME_ID, scorer_19['id'], json.dumps({})))
        print(f"  [OK] Goal 4 (P3): {scorer_19['name']} (#19) - No assists")
    
    # RED WINGS PENALTY
    print()
    print("Creating Red Wings penalty...")
    penalty_27 = get_player_by_jersey(away_team_id, 27)
    
    if not penalty_27:
        print(f"  [ERROR] Red Wings player #27 not found")
    else:
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'penalty', %s, 1, 0, %s, NOW(), NOW())
        """, (GAME_ID, penalty_27['id'], json.dumps({'penalty_type': 'roughing'})))
        print(f"  [OK] Penalty (P1): {penalty_27['name']} (#27) - Roughing")
    
    conn.commit()
    print()
    print("[OK] All events created")
    print()
    
    # Create game summary
    print("Creating game summary...")
    from stats_calculator import calculate_game_summary
    
    summary = calculate_game_summary(GAME_ID, force_update=True)
    if summary:
        # Update with correct scores
        cursor.execute("""
            UPDATE game_summaries
            SET home_team_score = 2,
                away_team_score = 4,
                updated_at = NOW()
            WHERE game_id = %s
        """, (GAME_ID,))
        conn.commit()
        print(f"  [OK] Game summary created")
        print(f"    Score: Red Wings 4 - 2 Bruins")
    else:
        # Create manually if calculate_game_summary failed
        cursor.execute("""
            INSERT INTO game_summaries (
                game_id, season_id, home_team_score, away_team_score,
                home_team_shots, away_team_shots, game_outcome, winner_team_id,
                went_to_overtime, went_to_shootout, processed_at, created_at, updated_at
            )
            SELECT 
                %s, season_id, 2, 4, 2, 4, 'regulation_loss', %s,
                false, false, NOW(), NOW(), NOW()
            FROM games WHERE id = %s
            ON CONFLICT (game_id) DO UPDATE SET
                home_team_score = 2,
                away_team_score = 4,
                game_outcome = 'regulation_loss',
                winner_team_id = %s,
                updated_at = NOW()
        """, (GAME_ID, away_team_id, GAME_ID, away_team_id))
        conn.commit()
        print(f"  [OK] Game summary created manually")
        print(f"    Score: Red Wings 4 - 2 Bruins")
    
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
    print("Game 110 Data Entry Complete!")
    print("=" * 60)
    print()
    print("Note: If Kaiden Sanchez (#61) was a sub in game 109, you may need")
    print("      to update game 109 events to attribute his 2 goals there.")
    print()


if __name__ == '__main__':
    main()


