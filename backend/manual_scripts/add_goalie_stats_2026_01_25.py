#!/usr/bin/env python3
"""
Add goalie assignments and goalie game stats for 2026-01-25 (Week 3).

Games:
- Red Wings @ Maple Leafs
- Canadiens @ Bruins
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

GAME_DATE = '2026-01-25'

GAME_1_HOME = 'Maple Leafs'
GAME_1_AWAY = 'Red Wings'
GAME_1_HOME_SCORE = 3
GAME_1_AWAY_SCORE = 1
GAME_1_HOME_SHOTS = 25
GAME_1_AWAY_SHOTS = 14

GAME_2_HOME = 'Bruins'
GAME_2_AWAY = 'Canadiens'
GAME_2_HOME_SCORE = 2
GAME_2_AWAY_SCORE = 3
GAME_2_HOME_SHOTS = 11
GAME_2_AWAY_SHOTS = 32


def get_game(cursor, home_team, away_team):
    cursor.execute("""
        SELECT g.id, ht.id as home_team_id, at.id as away_team_id
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.game_date = %s AND ht.name = %s AND at.name = %s
    """, (GAME_DATE, home_team, away_team))
    return cursor.fetchone()


def get_goalie_by_name(cursor, team_id, name_fragment):
    cursor.execute("""
        SELECT id, name, full_name
        FROM goalies
        WHERE team_id = %s
          AND (full_name ILIKE %s OR name ILIKE %s)
        LIMIT 1
    """, (team_id, f"%{name_fragment}%", f"%{name_fragment}%"))
    return cursor.fetchone()


def create_goalie(cursor, team_id, first_name, last_name, status='departed'):
    display_name = f"{first_name} {last_name[0].upper()}." if last_name else first_name
    full_name = f"{first_name} {last_name}".strip()
    cursor.execute("""
        INSERT INTO goalies (
            team_id, first_name, last_name, name, full_name,
            jersey_number, status, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, NULL, %s, NOW(), NOW())
        RETURNING id, name, full_name
    """, (team_id, first_name, last_name, display_name, full_name, status))
    return cursor.fetchone()


def upsert_goalie_stats(cursor, game_id, goalie_id, team_id, shots_against, goals_allowed):
    saves = shots_against - goals_allowed
    save_percentage = round((saves / shots_against), 3) if shots_against > 0 else 0.0
    cursor.execute("""
        INSERT INTO goalie_game_stats (
            game_id, goalie_id, team_id,
            shots_against, goals_allowed, saves, save_percentage,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (game_id, goalie_id) DO UPDATE SET
            team_id = EXCLUDED.team_id,
            shots_against = EXCLUDED.shots_against,
            goals_allowed = EXCLUDED.goals_allowed,
            saves = EXCLUDED.saves,
            save_percentage = EXCLUDED.save_percentage,
            updated_at = NOW()
    """, (game_id, goalie_id, team_id, shots_against, goals_allowed, saves, save_percentage))


def update_game_shots(cursor, game_id, home_shots, away_shots):
    cursor.execute("""
        UPDATE game_summaries
        SET home_team_shots = %s,
            away_team_shots = %s,
            updated_at = NOW()
        WHERE game_id = %s
    """, (home_shots, away_shots, game_id))


def assign_goalie(cursor, game_id, team_id, goalie_id, is_home_team):
    cursor.execute("""
        INSERT INTO game_goalies (
            game_id, team_id, goalie_id, is_home_team,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, NOW(), NOW())
    """, (game_id, team_id, goalie_id, is_home_team))


def main():
    print("=" * 60)
    print("Adding goalie stats for 2026-01-25 games")
    print("=" * 60)
    print()

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    if GAME_2_AWAY_SHOTS is None:
        print("ERROR: Canadiens shots on goal are not set for Bruins vs Canadiens")
        print("Update GAME_2_AWAY_SHOTS before running this script.")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Game 1: Red Wings @ Maple Leafs
    game_1 = get_game(cursor, GAME_1_HOME, GAME_1_AWAY)
    if not game_1:
        print(f"ERROR: Game not found for {GAME_DATE}: {GAME_1_AWAY} @ {GAME_1_HOME}")
        cursor.close()
        conn.close()
        sys.exit(1)

    game_1_id = game_1['id']
    game_1_home_id = game_1['home_team_id']
    game_1_away_id = game_1['away_team_id']

    phillip = get_goalie_by_name(cursor, game_1_home_id, 'Wiggins')
    if not phillip:
        print("ERROR: Phillip Wiggins not found for Maple Leafs")
        cursor.close()
        conn.close()
        sys.exit(1)

    briar = get_goalie_by_name(cursor, game_1_away_id, 'Briar')
    if not briar:
        print("ERROR: Briar Peeples not found for Red Wings")
        cursor.close()
        conn.close()
        sys.exit(1)

    cursor.execute("DELETE FROM game_goalies WHERE game_id = %s", (game_1_id,))
    assign_goalie(cursor, game_1_id, game_1_home_id, phillip['id'], True)
    assign_goalie(cursor, game_1_id, game_1_away_id, briar['id'], False)

    update_game_shots(cursor, game_1_id, GAME_1_HOME_SHOTS, GAME_1_AWAY_SHOTS)

    # Phillip (home) faces away shots
    upsert_goalie_stats(cursor, game_1_id, phillip['id'], game_1_home_id, GAME_1_AWAY_SHOTS, GAME_1_AWAY_SCORE)
    # Briar (away) faces home shots
    upsert_goalie_stats(cursor, game_1_id, briar['id'], game_1_away_id, GAME_1_HOME_SHOTS, GAME_1_HOME_SCORE)

    print(f"[OK] Game {game_1_id}: goalies assigned and stats stored")

    # Game 2: Canadiens @ Bruins
    game_2 = get_game(cursor, GAME_2_HOME, GAME_2_AWAY)
    if not game_2:
        print(f"ERROR: Game not found for {GAME_DATE}: {GAME_2_AWAY} @ {GAME_2_HOME}")
        cursor.close()
        conn.close()
        sys.exit(1)

    game_2_id = game_2['id']
    game_2_home_id = game_2['home_team_id']
    game_2_away_id = game_2['away_team_id']

    cove = get_goalie_by_name(cursor, game_2_home_id, 'Cove')
    if not cove:
        cove = create_goalie(cursor, game_2_home_id, 'Cove', 'Marlatt', status='departed')
        print(f"[NOTE] Added goalie: {cove['full_name']} (departed)")

    olivia = get_goalie_by_name(cursor, game_2_away_id, 'Olivia')
    if not olivia:
        print("ERROR: Olivia Baker not found for Canadiens")
        cursor.close()
        conn.close()
        sys.exit(1)

    cursor.execute("DELETE FROM game_goalies WHERE game_id = %s", (game_2_id,))
    assign_goalie(cursor, game_2_id, game_2_home_id, cove['id'], True)
    assign_goalie(cursor, game_2_id, game_2_away_id, olivia['id'], False)

    update_game_shots(cursor, game_2_id, GAME_2_HOME_SHOTS, GAME_2_AWAY_SHOTS)

    # Cove (home) faces away shots
    upsert_goalie_stats(cursor, game_2_id, cove['id'], game_2_home_id, GAME_2_AWAY_SHOTS, GAME_2_AWAY_SCORE)
    # Olivia (away) faces home shots
    upsert_goalie_stats(cursor, game_2_id, olivia['id'], game_2_away_id, GAME_2_HOME_SHOTS, GAME_2_HOME_SCORE)

    print(f"[OK] Game {game_2_id}: goalies assigned and stats stored")

    conn.commit()
    cursor.close()
    conn.close()

    print()
    print("=" * 60)
    print("Goalie stats update complete")
    print("=" * 60)


if __name__ == '__main__':
    main()
