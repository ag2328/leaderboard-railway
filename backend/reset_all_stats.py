#!/usr/bin/env python3
"""Reset all stats to zero by recalculating everything."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from models import get_season_by_name, get_all_teams
from stats_calculator import (
    calculate_team_standings,
    calculate_player_season_stats,
    calculate_goalie_season_stats
)
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

season = get_season_by_name('Spring 2026')
if not season:
    print("ERROR: Season 'Spring 2026' not found")
    sys.exit(1)

print("=" * 60)
print("Resetting All Stats to Zero")
print("=" * 60)
print()

# Recalculate team standings
print("1. Recalculating team standings...")
teams = get_all_teams()
for team in teams:
    try:
        calculate_team_standings(team['id'], season['id'])
    except Exception as e:
        print(f"  [ERROR] Team {team['name']}: {e}")

print(f"  [OK] Updated {len(teams)} teams")
print()

# Recalculate player stats
print("2. Recalculating player stats...")
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor(cursor_factory=RealDictCursor)

cursor.execute("SELECT DISTINCT id FROM players")
players = cursor.fetchall()

updated_players = 0
for player in players:
    try:
        calculate_player_season_stats(player['id'], season['id'])
        updated_players += 1
    except Exception as e:
        print(f"  [ERROR] Player {player['id']}: {e}")

print(f"  [OK] Updated {updated_players} players")
print()

# Recalculate goalie stats
print("3. Recalculating goalie stats...")
cursor.execute("SELECT DISTINCT id FROM goalies WHERE status = 'active'")
goalies = cursor.fetchall()

updated_goalies = 0
for goalie in goalies:
    try:
        calculate_goalie_season_stats(goalie['id'], season['id'])
        updated_goalies += 1
    except Exception as e:
        print(f"  [ERROR] Goalie {goalie['id']}: {e}")

print(f"  [OK] Updated {updated_goalies} goalies")
print()

cursor.close()
conn.close()

print("=" * 60)
print("All Stats Reset Complete!")
print("=" * 60)
print()
print("All team standings, player stats, and goalie stats have been")
print("recalculated and should now show zeros (no games played).")
print()






