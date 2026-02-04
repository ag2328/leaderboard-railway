#!/usr/bin/env python3
"""Check Olivia Baker's aggregated stats"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from models import get_season_by_name
from stats_calculator import calculate_goalie_season_stats

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

season = get_season_by_name('Spring 2026')
olivia_id = 3

# Recalculate season stats
result = calculate_goalie_season_stats(olivia_id, season['id'])

print("Olivia Baker Season Stats (Aggregated across all games):")
print(f"  Shots against: {result['shots_against']} (23 from game 109 + 28 from game 110)")
print(f"  Goals allowed: {result['goals_allowed']} (3 from game 109 + 4 from game 110)")
print(f"  Saves: {result['saves']} (20 from game 109 + 24 from game 110)")
print(f"  Save %: {result['save_percentage']:.3f}")

# Show individual game stats
cursor.execute("""
    SELECT ggs.game_id, ggs.team_id, t.name as team_name,
           ggs.shots_against, ggs.goals_allowed, ggs.saves, ggs.save_percentage
    FROM goalie_game_stats ggs
    JOIN games g ON ggs.game_id = g.id
    JOIN teams t ON ggs.team_id = t.id
    WHERE ggs.goalie_id = %s AND g.season_id = %s
    ORDER BY ggs.game_id
""", (olivia_id, season['id']))

games = cursor.fetchall()
print("\nIndividual Game Stats:")
for game in games:
    print(f"  Game {game[0]} ({game[2]}): {game[3]} shots, {game[4]} goals, {game[5]} saves, {game[6]:.3f} SV%")

cursor.close()
conn.close()


