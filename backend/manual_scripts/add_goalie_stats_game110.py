#!/usr/bin/env python3
"""Add goalie stats for game 110"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
GAME_ID = 110

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Get game teams
cursor.execute("SELECT home_team_id, away_team_id FROM games WHERE id = %s", (GAME_ID,))
game = cursor.fetchone()
home_team_id = game['home_team_id']
away_team_id = game['away_team_id']

# Find goalies
cursor.execute("SELECT id FROM goalies WHERE name LIKE %s AND team_id = %s", ('%Briar%', away_team_id))
briar = cursor.fetchone()

cursor.execute("SELECT id FROM goalies WHERE name LIKE %s AND team_id = %s", ('%Olivia%', home_team_id))
olivia = cursor.fetchone()

# If Olivia not found for Bruins, check if she's registered elsewhere or use first Bruins goalie
if not olivia:
    cursor.execute("SELECT id FROM goalies WHERE team_id = %s LIMIT 1", (home_team_id,))
    olivia = cursor.fetchone()
    if olivia:
        print(f"Note: Using first available Bruins goalie (ID: {olivia['id']}) instead of Olivia Baker")

if not briar:
    print("ERROR: Briar Peeples not found for Red Wings")
    cursor.close()
    conn.close()
    sys.exit(1)

if not olivia:
    print("ERROR: No Bruins goalie found")
    cursor.close()
    conn.close()
    sys.exit(1)

# Assign goalies to game
cursor.execute("DELETE FROM game_goalies WHERE game_id = %s", (GAME_ID,))
cursor.execute("""
    INSERT INTO game_goalies (game_id, team_id, goalie_id, is_home_team, created_at, updated_at)
    VALUES (%s, %s, %s, false, NOW(), NOW())
""", (GAME_ID, away_team_id, briar['id']))
cursor.execute("""
    INSERT INTO game_goalies (game_id, team_id, goalie_id, is_home_team, created_at, updated_at)
    VALUES (%s, %s, %s, true, NOW(), NOW())
""", (GAME_ID, home_team_id, olivia['id']))
print("Assigned goalies to game 110")

# Create goalie stats
cursor.execute("DELETE FROM goalie_game_stats WHERE game_id = %s", (GAME_ID,))

# Red Wings (Briar): 22 shots, 2 goals allowed, 20 saves
cursor.execute("""
    INSERT INTO goalie_game_stats (game_id, goalie_id, team_id, shots_against, goals_allowed, saves, save_percentage, created_at, updated_at)
    VALUES (%s, %s, %s, 22, 2, 20, 0.909, NOW(), NOW())
    ON CONFLICT (game_id, goalie_id) DO UPDATE SET
        shots_against = 22,
        goals_allowed = 2,
        saves = 20,
        save_percentage = 0.909,
        updated_at = NOW()
""", (GAME_ID, briar['id'], away_team_id))

# Bruins (Olivia/London): 28 shots, 4 goals allowed, 24 saves
cursor.execute("""
    INSERT INTO goalie_game_stats (game_id, goalie_id, team_id, shots_against, goals_allowed, saves, save_percentage, created_at, updated_at)
    VALUES (%s, %s, %s, 28, 4, 24, 0.857, NOW(), NOW())
    ON CONFLICT (game_id, goalie_id) DO UPDATE SET
        shots_against = 28,
        goals_allowed = 4,
        saves = 24,
        save_percentage = 0.857,
        updated_at = NOW()
""", (GAME_ID, olivia['id'], home_team_id))

conn.commit()
print("Created goalie game stats:")
print(f"  Red Wings (Briar P.): 22 shots against, 2 goals allowed, 20 saves, 0.909 SV%")
print(f"  Bruins (Goalie ID {olivia['id']}): 28 shots against, 4 goals allowed, 24 saves, 0.857 SV%")

cursor.close()
conn.close()


