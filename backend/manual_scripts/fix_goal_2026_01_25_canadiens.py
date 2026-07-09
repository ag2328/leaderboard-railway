#!/usr/bin/env python3
"""
Fix Canadiens goal attribution for 2026-01-25 (Bruins vs Canadiens).

Replaces unknown scorer (jersey 62) with #52 Gio Kainz.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from sync_service import update_aggregated_stats_for_game

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
GAME_DATE = '2026-01-25'
HOME_TEAM = 'Bruins'
AWAY_TEAM = 'Canadiens'
TARGET_JERSEY = 52


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        raise SystemExit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT g.id, g.season_id, ht.id as home_team_id, at.id as away_team_id
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.game_date = %s AND ht.name = %s AND at.name = %s
    """, (GAME_DATE, HOME_TEAM, AWAY_TEAM))
    game = cursor.fetchone()
    if not game:
        print("ERROR: Game not found for 2026-01-25 Bruins vs Canadiens")
        raise SystemExit(1)

    game_id = game['id']
    season_id = game['season_id']
    away_team_id = game['away_team_id']

    cursor.execute("""
        SELECT id, name FROM players WHERE team_id = %s AND jersey_number = %s
    """, (away_team_id, TARGET_JERSEY))
    player = cursor.fetchone()
    if not player:
        print(f"ERROR: Canadiens player #{TARGET_JERSEY} not found")
        raise SystemExit(1)

    cursor.execute("""
        SELECT id, details
        FROM events
        WHERE game_id = %s
          AND event_type = 'goal'
          AND details ? 'unknown_scorer'
          AND details->>'team' = 'away'
          AND details->>'jersey_number' = '62'
    """, (game_id,))
    event = cursor.fetchone()
    if not event:
        print("ERROR: Unknown scorer goal for jersey 62 not found")
        raise SystemExit(1)

    assists = event['details'].get('assists') if event['details'] else None
    new_details = {'assists': assists} if assists else {}

    cursor.execute("""
        UPDATE events
        SET player_id = %s,
            details = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (player['id'], json.dumps(new_details), event['id']))

    conn.commit()
    cursor.close()
    conn.close()

    update_aggregated_stats_for_game(game_id, season_id)
    print(f"[OK] Updated goal to {player['name']} (#{TARGET_JERSEY}) for game {game_id}")


if __name__ == '__main__':
    main()
