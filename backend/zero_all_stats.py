#!/usr/bin/env python3
"""Explicitly set all stats to zero."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

print("=" * 60)
print("Setting All Stats to Zero")
print("=" * 60)
print()

# Get season
from models import get_season_by_name
season = get_season_by_name('Spring 2026')
if not season:
    print("ERROR: Season 'Spring 2026' not found")
    sys.exit(1)

season_id = season['id']

# Zero out team standings
print("1. Zeroing team standings...")
cursor.execute("""
    UPDATE team_standings
    SET games_played = 0,
        wins = 0,
        losses = 0,
        ties = 0,
        tiebreaker_wins = 0,
        tiebreaker_losses = 0,
        goals_scored = 0,
        goals_against = 0,
        points = 0,
        updated_at = NOW()
    WHERE season_id = %s
""", (season_id,))
team_updated = cursor.rowcount
print(f"  [OK] Updated {team_updated} team standings")
print()

# Zero out player stats
print("2. Zeroing player stats...")
cursor.execute("""
    UPDATE player_season_stats
    SET goals = 0,
        assists = 0,
        penalties = 0,
        updated_at = NOW()
    WHERE season_id = %s
""", (season_id,))
player_updated = cursor.rowcount
print(f"  [OK] Updated {player_updated} player stats")
print()

# Zero out goalie stats
print("3. Zeroing goalie stats...")
cursor.execute("""
    UPDATE goalie_season_stats
    SET shots_against = 0,
        goals_allowed = 0,
        saves = 0,
        save_percentage = 0.0,
        updated_at = NOW()
    WHERE season_id = %s
""", (season_id,))
goalie_updated = cursor.rowcount
print(f"  [OK] Updated {goalie_updated} goalie stats")
print()

conn.commit()
cursor.close()
conn.close()

print("=" * 60)
print("All Stats Set to Zero!")
print("=" * 60)
print()

