#!/usr/bin/env python3
"""
Rebuild summaries for all locked games from events.

This forces recalculation even if summaries exist.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from stats_calculator import calculate_game_summary, calculate_goalie_game_stats
from sync_service import update_aggregated_stats_for_game

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        raise SystemExit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT id, season_id
        FROM games
        WHERE status = 'locked'
        ORDER BY game_date, id
    """)
    games = cursor.fetchall()
    cursor.close()
    conn.close()

    updated = 0
    skipped = 0
    for game in games:
        summary = calculate_game_summary(game['id'], force_update=True)
        if not summary:
            skipped += 1
            continue
        calculate_goalie_game_stats(game['id'])
        update_aggregated_stats_for_game(game['id'], game['season_id'])
        updated += 1

    print(f"Rebuilt summaries: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == '__main__':
    main()
