#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("""
    SELECT g.id
    FROM games g
    JOIN teams ht ON g.home_team_id = ht.id
    JOIN teams at ON g.away_team_id = at.id
    WHERE g.game_date = %s AND ht.name = %s AND at.name = %s
""", ("2026-01-11", "Canadiens", "Maple Leafs"))
print("Game id (Canadiens vs Maple Leafs, 2026-01-11):", cur.fetchone())

cur.execute("""
    SELECT gs.home_team_score, gs.away_team_score,
           gs.home_team_shots, gs.away_team_shots,
           gs.game_outcome, gs.went_to_shootout, gs.went_to_overtime
    FROM game_summaries gs
    WHERE gs.game_id = %s
""", (109,))
print("Game 109 summary:", cur.fetchone())

cur.execute("""
    SELECT event_type, player_id, period, details
    FROM events
    WHERE game_id = %s
    ORDER BY id
""", (109,))
rows = cur.fetchall()
print("Game 109 events:", len(rows))
for row in rows:
    print(row)

cur.close()
conn.close()
