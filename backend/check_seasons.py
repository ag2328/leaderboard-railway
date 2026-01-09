#!/usr/bin/env python3
"""Check what seasons exist in the database."""

import os
from dotenv import load_dotenv
from models import get_db_connection
from psycopg2.extras import RealDictCursor

load_dotenv()

conn = get_db_connection()
cursor = conn.cursor(cursor_factory=RealDictCursor)

cursor.execute("""
    SELECT id, name, start_date, end_date, is_active, created_at
    FROM seasons
    ORDER BY start_date DESC
""")

seasons = cursor.fetchall()

print("=" * 80)
print("Seasons in Database")
print("=" * 80)
print()

if seasons:
    for season in seasons:
        print(f"Season: {season['name']}")
        print(f"  ID: {season['id']}")
        print(f"  Start Date: {season['start_date']}")
        print(f"  End Date: {season['end_date']}")
        print(f"  Active: {season['is_active']}")
        print(f"  Created: {season['created_at']}")
        print()
        
        # Check if there are standings for this season
        cursor.execute("""
            SELECT COUNT(*) as count FROM team_standings WHERE season_id = %s
        """, (season['id'],))
        standings_count = cursor.fetchone()['count']
        print(f"  Team Standings Records: {standings_count}")
        
        if standings_count > 0:
            cursor.execute("""
                SELECT t.name, ts.games_played, ts.wins, ts.losses, ts.ties,
                       ts.tiebreaker_wins, ts.tiebreaker_losses, ts.points,
                       ts.goals_scored, ts.goals_against
                FROM team_standings ts
                JOIN teams t ON ts.team_id = t.id
                WHERE ts.season_id = %s
                ORDER BY ts.points DESC, ts.wins DESC
            """, (season['id'],))
            standings = cursor.fetchall()
            
            print(f"  Final Standings:")
            print(f"    {'Team':<15} {'GP':<4} {'W':<4} {'L':<4} {'T':<4} {'TW':<4} {'TL':<4} {'PTS':<5} {'GF':<4} {'GA':<4}")
            print(f"    {'-'*70}")
            for standing in standings:
                print(f"    {standing['name']:<15} {standing['games_played']:<4} {standing['wins']:<4} "
                      f"{standing['losses']:<4} {standing['ties']:<4} {standing['tiebreaker_wins']:<4} "
                      f"{standing['tiebreaker_losses']:<4} {standing['points']:<5} {standing['goals_scored']:<4} "
                      f"{standing['goals_against']:<4}")
        
        print()
else:
    print("No seasons found in database.")

cursor.close()
conn.close()

