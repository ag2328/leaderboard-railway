#!/usr/bin/env python3
"""Update game 109 to attribute 2 unknown player goals to Kaiden Sanchez (#61)"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
GAME_ID = 109

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Get Kaiden Sanchez ID (he's on Bruins roster but was a sub for Maple Leafs in game 109)
cursor.execute("""
    SELECT id FROM players 
    WHERE jersey_number = 61
""", ())
kaiden = cursor.fetchone()

if not kaiden:
    print("ERROR: Kaiden Sanchez (#61) not found")
    cursor.close()
    conn.close()
    sys.exit(1)

kaiden_id = kaiden['id']
print(f"Found Kaiden Sanchez: ID {kaiden_id}")

# Find 2 unknown player goals for Maple Leafs (away team)
cursor.execute("""
    SELECT id FROM events 
    WHERE game_id = %s 
    AND event_type = 'goal' 
    AND player_id IS NULL 
    AND details->>'team' = 'away'
    ORDER BY id 
    LIMIT 2
""", (GAME_ID,))
unknown_goals = cursor.fetchall()

if len(unknown_goals) < 2:
    print(f"ERROR: Found only {len(unknown_goals)} unknown Maple Leafs goals, need 2")
    cursor.close()
    conn.close()
    sys.exit(1)

# Update the 2 goals to attribute to Kaiden
for goal in unknown_goals:
    cursor.execute("""
        UPDATE events 
        SET player_id = %s 
        WHERE id = %s
    """, (kaiden_id, goal['id']))
    print(f"Updated goal ID {goal['id']} to Kaiden Sanchez")

conn.commit()
print(f"\n[OK] Updated 2 goals in game 109 to Kaiden Sanchez (#61)")

cursor.close()
conn.close()

