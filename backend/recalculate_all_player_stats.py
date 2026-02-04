#!/usr/bin/env python3
"""Recalculate all player stats with fixed assist counting."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from stats_calculator import calculate_player_season_stats
from models import get_season_by_name

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor(cursor_factory=RealDictCursor)

season = get_season_by_name('Spring 2026')

# Get all players
cursor.execute("SELECT DISTINCT id FROM players")
players = cursor.fetchall()

print("Recalculating player stats...")
updated = 0
for player in players:
    try:
        calculate_player_season_stats(player['id'], season['id'])
        updated += 1
    except Exception as e:
        print(f"Error updating player {player['id']}: {e}")

print(f"Updated {updated} players")

cursor.close()
conn.close()






