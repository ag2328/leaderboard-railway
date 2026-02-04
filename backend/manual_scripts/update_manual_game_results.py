#!/usr/bin/env python3
"""
Manually set game results for known scores without updating stats.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

GAME_RESULTS = [
    # Week 1 (2026-01-11)
    {
        "date": "2026-01-11",
        "home": "Canadiens",
        "away": "Maple Leafs",
        "home_score": 4,
        "away_score": 3,
        "went_to_shootout": True,
        "went_to_overtime": False,
    },
    {
        "date": "2026-01-11",
        "home": "Bruins",
        "away": "Red Wings",
        "home_score": 2,
        "away_score": 4,
        "went_to_shootout": False,
        "went_to_overtime": False,
    },
    # Week 2 (2026-01-18)
    {
        "date": "2026-01-18",
        "home": "Maple Leafs",
        "away": "Bruins",
        "home_score": 5,
        "away_score": 1,
        "went_to_shootout": False,
        "went_to_overtime": False,
    },
    {
        "date": "2026-01-18",
        "home": "Red Wings",
        "away": "Canadiens",
        "home_score": 3,
        "away_score": 6,
        "went_to_shootout": False,
        "went_to_overtime": False,
    },
    # Week 3 (2026-01-25)
    {
        "date": "2026-01-25",
        "home": "Maple Leafs",
        "away": "Red Wings",
        "home_score": 3,
        "away_score": 1,
        "went_to_shootout": False,
        "went_to_overtime": False,
    },
    {
        "date": "2026-01-25",
        "home": "Bruins",
        "away": "Canadiens",
        "home_score": 2,
        "away_score": 3,
        "went_to_shootout": False,
        "went_to_overtime": False,
    },
]


def get_outcome(home_score, away_score, went_to_overtime, went_to_shootout):
    if home_score > away_score:
        if went_to_shootout:
            return "so_win"
        if went_to_overtime:
            return "ot_win"
        return "regulation_win"
    if away_score > home_score:
        if went_to_shootout:
            return "so_loss"
        if went_to_overtime:
            return "ot_loss"
        return "regulation_loss"
    return "tie"


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        raise SystemExit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    for result in GAME_RESULTS:
        cursor.execute("""
            SELECT g.id, g.season_id, g.home_team_id, g.away_team_id,
                   ht.name as home_team, at.name as away_team
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE g.game_date = %s AND ht.name = %s AND at.name = %s
        """, (result["date"], result["home"], result["away"]))
        game = cursor.fetchone()
        if not game:
            print(f"[ERROR] Game not found: {result['date']} {result['away']} @ {result['home']}")
            continue

        outcome = get_outcome(
            result["home_score"],
            result["away_score"],
            result["went_to_overtime"],
            result["went_to_shootout"],
        )
        winner_id = None
        if result["home_score"] > result["away_score"]:
            winner_id = game["home_team_id"]
        elif result["away_score"] > result["home_score"]:
            winner_id = game["away_team_id"]

        cursor.execute("""
            SELECT home_team_shots, away_team_shots
            FROM game_summaries
            WHERE game_id = %s
        """, (game["id"],))
        shots = cursor.fetchone()
        home_shots = shots["home_team_shots"] if shots else 0
        away_shots = shots["away_team_shots"] if shots else 0

        cursor.execute("""
            INSERT INTO game_summaries (
                game_id, season_id,
                home_team_score, away_team_score,
                home_team_shots, away_team_shots,
                game_outcome, winner_team_id,
                went_to_overtime, went_to_shootout,
                processed_at, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
            ON CONFLICT (game_id) DO UPDATE SET
                home_team_score = EXCLUDED.home_team_score,
                away_team_score = EXCLUDED.away_team_score,
                game_outcome = EXCLUDED.game_outcome,
                winner_team_id = EXCLUDED.winner_team_id,
                went_to_overtime = EXCLUDED.went_to_overtime,
                went_to_shootout = EXCLUDED.went_to_shootout,
                updated_at = NOW()
        """, (
            game["id"],
            game["season_id"],
            result["home_score"],
            result["away_score"],
            home_shots,
            away_shots,
            outcome,
            winner_id,
            result["went_to_overtime"],
            result["went_to_shootout"],
        ))

        cursor.execute("""
            UPDATE games
            SET status = 'locked',
                game_outcome = %s,
                winner_team_id = %s,
                went_to_overtime = %s,
                went_to_shootout = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            outcome,
            winner_id,
            result["went_to_overtime"],
            result["went_to_shootout"],
            game["id"],
        ))

        print(
            f"[OK] {result['date']} {result['away']} @ {result['home']} "
            f"-> {result['away_score']}-{result['home_score']} ({outcome})"
        )

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
