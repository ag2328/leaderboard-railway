#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def count_goals(cursor, game_id, home_team_id, away_team_id):
    cursor.execute("""
        SELECT e.player_id, e.details, p.team_id
        FROM events e
        LEFT JOIN players p ON e.player_id = p.id
        WHERE e.game_id = %s AND e.event_type = 'goal'
        ORDER BY e.id
    """, (game_id,))
    goals = cursor.fetchall()

    home_goals = 0
    away_goals = 0
    for goal in goals:
        details = goal['details'] or {}
        team_hint = details.get('team')
        if team_hint == 'home':
            home_goals += 1
            continue
        if team_hint == 'away':
            away_goals += 1
            continue

        player_team_id = goal['team_id']
        if player_team_id == home_team_id:
            home_goals += 1
        elif player_team_id == away_team_id:
            away_goals += 1

    return home_goals, away_goals


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        raise SystemExit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT g.id, g.game_date, g.home_team_id, g.away_team_id,
               ht.name as home_team, at.name as away_team,
               gs.home_team_score, gs.away_team_score
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        LEFT JOIN game_summaries gs ON gs.game_id = g.id
        WHERE g.status = 'locked'
        ORDER BY g.game_date, g.id
    """)
    games = cursor.fetchall()

    all_rows = []
    mismatches = []
    for game in games:
        home_goals, away_goals = count_goals(
            cursor,
            game['id'],
            game['home_team_id'],
            game['away_team_id']
        )
        row = (
            game['id'],
            game['game_date'],
            game['home_team'],
            game['away_team'],
            game['home_team_score'],
            game['away_team_score'],
            home_goals,
            away_goals
        )
        all_rows.append(row)
        if (game['home_team_score'] is None or game['away_team_score'] is None or
                game['home_team_score'] != home_goals or
                game['away_team_score'] != away_goals):
            mismatches.append(row)

    print("LOCKED GAMES (summary vs events):")
    for row in all_rows:
        print(row)

    print()
    print("MISMATCHES (need review):")
    for row in mismatches:
        print(row)

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
