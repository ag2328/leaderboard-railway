#!/usr/bin/env python3
"""
Load goalies from goalies_spring2026.json into the database.

Creates entries in goalie_season_stats table for goalies.
Assumes goalies already exist as players in the players table.
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
CURRENT_SEASON = os.getenv('CURRENT_SEASON', 'Spring 2026')

# Get project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

GOALIES_FILE = os.path.join(PROJECT_ROOT, 'goalies_spring2026.json')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

if not os.path.exists(GOALIES_FILE):
    print(f"ERROR: Goalies file not found: {GOALIES_FILE}")
    sys.exit(1)


def load_goalies():
    """Load goalies into database."""
    try:
        # Read goalies JSON
        print(f"Reading goalies from: {GOALIES_FILE}")
        with open(GOALIES_FILE, 'r', encoding='utf-8') as f:
            goalies_data = json.load(f)

        goalies_list = goalies_data.get('goalies', [])
        print(f"Found {len(goalies_list)} goalies in file")
        print()

        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get season ID
        cursor.execute("SELECT id, name FROM seasons WHERE name = %s", (CURRENT_SEASON,))
        season = cursor.fetchone()

        if not season:
            print(f"[ERROR] Season '{CURRENT_SEASON}' not found in database")
            print("Run: python backend/setup_season.py")
            cursor.close()
            conn.close()
            return

        season_id = season['id']
        print(f"[OK] Season: {season['name']} (ID: {season_id})")
        print()

        # Get team mapping
        cursor.execute("SELECT id, name FROM teams")
        teams = cursor.fetchall()
        team_map = {t['name']: t['id'] for t in teams}

        print("Teams in database:")
        for name, tid in team_map.items():
            print(f"  {name}: ID {tid}")
        print()

        created_stats = 0
        updated_stats = 0
        created_goalies = 0
        updated_goalies = 0
        created_players = 0
        errors = []

        for goalie in goalies_list:
            customer_id = goalie.get('customer_id')
            team_name = goalie.get('team_name')
            first_name = goalie.get('first_name', '').strip()
            last_name = goalie.get('last_name', '').strip()
            provided_full = goalie.get('full_name', '').strip()
            jersey_number = goalie.get('jersey_number', '')

            # Build display and full names
            if first_name and last_name:
                display_name = f"{first_name} {last_name[0].upper()}."
                full_name = provided_full or f"{first_name} {last_name}"
            else:
                display_name = provided_full or f"{first_name} {last_name}".strip()
                full_name = provided_full or display_name

            # Normalize jersey number
            jersey_number = int(jersey_number) if str(jersey_number).strip().isdigit() else None

            # Get team ID
            team_id = team_map.get(team_name)
            if not team_id:
                errors.append(f"Team not found in DB: {team_name} for goalie {full_name}")
                continue

            # Upsert goalie record in goalies table
            goalie_id = None
            if full_name:
                cursor.execute("SELECT id, team_id FROM goalies WHERE full_name = %s", (full_name,))
            else:
                cursor.execute("SELECT id, team_id FROM goalies WHERE name = %s", (display_name,))
            existing_goalie = cursor.fetchone()

            if existing_goalie:
                goalie_id = existing_goalie['id']
                cursor.execute("""
                    UPDATE goalies
                    SET team_id = %s,
                        first_name = %s,
                        last_name = %s,
                        name = %s,
                        full_name = %s,
                        jersey_number = %s,
                        status = 'active',
                        updated_at = NOW()
                    WHERE id = %s
                """, (team_id, first_name, last_name, display_name, full_name, jersey_number, goalie_id))
                updated_goalies += 1
            else:
                cursor.execute("""
                    INSERT INTO goalies (
                        team_id, first_name, last_name, name, full_name,
                        jersey_number, status, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
                    RETURNING id
                """, (team_id, first_name, last_name, display_name, full_name, jersey_number))
                goalie_id = cursor.fetchone()['id']
                created_goalies += 1

            # Find player by customer_id
            player_id = None
            if customer_id:
                cursor.execute("SELECT id, name, team_id FROM players WHERE customer_id = %s", (customer_id,))
                player = cursor.fetchone()
                if player:
                    player_id = player['id']
                    # Update team_id if it changed (shouldn't happen, but just in case)
                    if player['team_id'] != team_id:
                        cursor.execute("""
                            UPDATE players 
                            SET team_id = %s, updated_at = NOW() 
                            WHERE id = %s
                        """, (team_id, player_id))
                        print(f"[UPDATE] {full_name} team_id updated: {player['team_id']} -> {team_id}")
            
            if not player_id:
                # Try to find by name as fallback
                cursor.execute("SELECT id FROM players WHERE name = %s AND team_id = %s", (full_name, team_id))
                player = cursor.fetchone()
                if player:
                    player_id = player['id']
                    print(f"[NOTE] {full_name} found by name (no customer_id match)")
            
            if not player_id:
                # Goalie doesn't exist as player yet - create them
                first_name = goalie.get('first_name', '').strip()
                last_name = goalie.get('last_name', '').strip()
                jersey_number = goalie.get('jersey_number', '').strip() or None
                
                # Build display name (public: "First L.")
                if last_name:
                    last_initial = last_name[0].upper()
                    display_name = f"{first_name} {last_initial}."
                else:
                    display_name = full_name
                
                # Create player record
                cursor.execute("""
                    INSERT INTO players (team_id, name, full_name, jersey_number, customer_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (team_id, display_name, full_name, jersey_number, customer_id))
                player_id = cursor.fetchone()['id']
                created_player = True
                print(f"[CREATE PLAYER] {full_name} (ID: {player_id}) -> team_id={team_id}, jersey={jersey_number or 'None'}, customer_id={customer_id or 'NULL'}")
            else:
                created_player = False

            # Create or update goalie_season_stats entry (goalie_id references goalies table)
            cursor.execute("""
                SELECT id FROM goalie_season_stats 
                WHERE goalie_id = %s AND season_id = %s
            """, (goalie_id, season_id))
            
            existing = cursor.fetchone()

            if existing:
                # Update existing entry (in case team changed)
                cursor.execute("""
                    UPDATE goalie_season_stats
                    SET team_id = %s,
                        updated_at = NOW()
                    WHERE goalie_id = %s AND season_id = %s
                """, (team_id, goalie_id, season_id))
                updated_stats += 1
                print(f"[UPDATE STATS] {full_name} ({team_name}) - Goalie stats updated")
            else:
                # Create new entry with zero stats (will be calculated when games are played)
                cursor.execute("""
                    INSERT INTO goalie_season_stats (
                        goalie_id, team_id, season_id,
                        shots_against, goals_allowed, saves, save_percentage,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, 0, 0, 0, 0.0, NOW(), NOW())
                    RETURNING id
                """, (goalie_id, team_id, season_id))
                new_id = cursor.fetchone()['id']
                created_stats += 1
                print(f"[CREATE STATS] {full_name} ({team_name}, #{goalie.get('jersey_number', 'N/A')}) - Goalie stats created (ID: {new_id})")
            
            if created_player:
                created_players += 1

        conn.commit()

        print()
        print("=" * 60)
        print("Goalies Load Summary")
        print("=" * 60)
        print(f"Goalies created: {created_goalies}")
        print(f"Goalies updated: {updated_goalies}")
        print(f"Players created: {created_players}")
        print(f"Goalie stats created: {created_stats}")
        print(f"Goalie stats updated: {updated_stats}")

        if errors:
            print()
            print("Errors:")
            for e in errors:
                print(f"  - {e}")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)


if __name__ == "__main__":
    load_goalies()

