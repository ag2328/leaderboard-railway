#!/usr/bin/env python3
"""
Enter game data for 2026-01-25: Red Wings @ Maple Leafs (Week 3)

Final: Maple Leafs 3, Red Wings 1
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from stats_calculator import calculate_game_summary

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
GAME_DATE = '2026-01-25'
HOME_TEAM = 'Maple Leafs'
AWAY_TEAM = 'Red Wings'


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


def get_game(cursor):
    """Get game by date and team names."""
    cursor.execute("""
        SELECT g.*, ht.name as home_team_name, at.name as away_team_name,
               ht.id as home_team_id, at.id as away_team_id
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.game_date = %s AND ht.name = %s AND at.name = %s
    """, (GAME_DATE, HOME_TEAM, AWAY_TEAM))
    return cursor.fetchone()


def create_goal_event(cursor, game_id, team_id, team_side, jersey_number, period=1, assists=None):
    """Create goal event, falling back to unknown scorer if needed."""
    assists = assists or []
    scorer = get_player_by_jersey(team_id, jersey_number)
    assist_ids = []

    for assist_jersey in assists:
        assister = get_player_by_jersey(team_id, assist_jersey)
        if assister:
            assist_ids.append(assister['id'])
        else:
            print(f"  [WARN] Assist player #{assist_jersey} not found for {team_side} team")

    details = {}
    if assist_ids:
        details['assists'] = assist_ids

    if not scorer:
        print(f"  [WARN] {team_side.title()} player #{jersey_number} not found - creating unknown scorer")
        details.update({
            'team': team_side,
            'unknown_scorer': True,
            'jersey_number': jersey_number
        })
        cursor.execute("""
            INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
            VALUES (%s, 'goal', NULL, %s, 0, %s, NOW(), NOW())
        """, (game_id, period, json.dumps(details)))
        return

    cursor.execute("""
        INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
        VALUES (%s, 'goal', %s, %s, 0, %s, NOW(), NOW())
    """, (game_id, scorer['id'], period, json.dumps(details)))
    assist_text = ', '.join([f'#{a}' for a in assists]) if assists else 'None'
    print(f"  [OK] Goal (P{period}): {scorer['name']} (#{jersey_number}) - Assists: {assist_text}")


def create_penalty_event(cursor, game_id, team_id, team_label, jersey_number, penalty_type, minutes, period=1):
    """Create penalty event for a player."""
    player = get_player_by_jersey(team_id, jersey_number)
    if not player:
        print(f"  [WARN] {team_label} player #{jersey_number} not found for penalty")
        return

    details = {'penalty_type': penalty_type, 'minutes': minutes}
    cursor.execute("""
        INSERT INTO events (game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at)
        VALUES (%s, 'penalty', %s, %s, 0, %s, NOW(), NOW())
    """, (game_id, player['id'], period, json.dumps(details)))
    print(f"  [OK] Penalty (P{period}): {player['name']} (#{jersey_number}) - {penalty_type}, {minutes} minutes")


def main():
    print("=" * 60)
    print("Entering Game Data: Red Wings @ Maple Leafs (2026-01-25)")
    print("=" * 60)
    print()

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    game = get_game(cursor)
    if not game:
        print(f"ERROR: Game not found for {GAME_DATE}: {AWAY_TEAM} @ {HOME_TEAM}")
        cursor.close()
        conn.close()
        sys.exit(1)

    game_id = game['id']
    home_team_id = game['home_team_id']
    away_team_id = game['away_team_id']

    print(f"Game ID: {game_id}")
    print(f"Date: {game['game_date']}")
    print(f"Status: {game['status']}")
    print()

    print("Clearing existing events...")
    cursor.execute("DELETE FROM events WHERE game_id = %s", (game_id,))
    print(f"  [OK] Deleted {cursor.rowcount} existing events")
    print()

    print("Creating Maple Leafs goals...")
    create_goal_event(cursor, game_id, home_team_id, 'home', 72, period=1)
    create_goal_event(cursor, game_id, home_team_id, 'home', 28, period=2)
    create_goal_event(cursor, game_id, home_team_id, 'home', 28, period=3)

    print()
    print("Creating Red Wings goals...")
    create_goal_event(cursor, game_id, away_team_id, 'away', 25, period=1)

    print()
    print("Creating penalties...")
    create_penalty_event(cursor, game_id, home_team_id, HOME_TEAM, 34, 'roughing', 2, period=1)
    create_penalty_event(cursor, game_id, home_team_id, HOME_TEAM, 27, 'tripping', 2, period=1)
    create_penalty_event(cursor, game_id, away_team_id, AWAY_TEAM, 23, 'roughing', 2, period=1)

    conn.commit()
    print()
    print("[OK] All events created")
    print()

    print("Creating game summary...")
    summary = calculate_game_summary(game_id, force_update=True)
    if summary:
        cursor.execute("""
            UPDATE game_summaries
            SET home_team_score = 3,
                away_team_score = 1,
                home_team_shots = 25,
                away_team_shots = 14,
                updated_at = NOW()
            WHERE game_id = %s
        """, (game_id,))
        conn.commit()
        print("  [OK] Game summary created")
        print("    Score: Maple Leafs 3 - 1 Red Wings")
        print("    Shots: Maple Leafs 25 - 14 Red Wings")
    else:
        print("  [WARN] Could not create game summary")

    print()
    print("Locking game...")
    cursor.execute("""
        UPDATE games
        SET status = 'locked',
            updated_at = NOW()
        WHERE id = %s
    """, (game_id,))
    conn.commit()
    print(f"  [OK] Game {game_id} locked")

    cursor.close()
    conn.close()

    print()
    print("=" * 60)
    print("Game Data Entry Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Add goalie stats")
    print("2. Process the game: python backend/sync_service.py (or use API endpoint)")
    print()


if __name__ == '__main__':
    main()
