"""
Load schedule data from schedule_spring2026.json into the database.

This script:
1. Reads schedule_spring2026.json
2. Creates or updates games in the games table
3. Sets season_id to Spring 2026
4. Sets status to 'scheduled' for future games
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
CURRENT_SEASON = os.getenv('CURRENT_SEASON', 'Spring 2026')
SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schedule_spring2026.json')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

if not os.path.exists(SCHEDULE_FILE):
    print(f"ERROR: Schedule file not found: {SCHEDULE_FILE}")
    sys.exit(1)


def load_schedule():
    """Load schedule from JSON into database."""
    try:
        # Read schedule JSON
        print(f"Reading schedule from: {SCHEDULE_FILE}")
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
        
        print(f"Found {len(schedule_data['games'])} games in schedule")
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
        print(f"[OK] Found season: {season['name']} (ID: {season_id})")
        print()
        
        # Get team name to ID mapping
        cursor.execute("SELECT id, name FROM teams")
        teams = cursor.fetchall()
        team_map = {team['name']: team['id'] for team in teams}
        
        print("Teams in database:")
        for name, team_id in team_map.items():
            print(f"  {name}: ID {team_id}")
        print()
        
        # Process each game
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for game in schedule_data['games']:
            home_team_name = game['home_team']
            away_team_name = game['away_team']
            game_date = datetime.strptime(game['date'], '%Y-%m-%d').date()
            week = game.get('week')
            
            # Get team IDs
            home_team_id = team_map.get(home_team_name)
            away_team_id = team_map.get(away_team_name)
            
            if not home_team_id:
                errors.append(f"Home team '{home_team_name}' not found in database")
                continue
            if not away_team_id:
                errors.append(f"Away team '{away_team_name}' not found in database")
                continue
            
            # Check if game already exists (by date and teams)
            cursor.execute("""
                SELECT id, season_id, status 
                FROM games 
                WHERE game_date = %s 
                AND home_team_id = %s 
                AND away_team_id = %s
            """, (game_date, home_team_id, away_team_id))
            
            existing_game = cursor.fetchone()
            
            if existing_game:
                # Update existing game
                needs_update = False
                update_fields = []
                update_values = []
                
                if existing_game['season_id'] != season_id:
                    update_fields.append("season_id = %s")
                    update_values.append(season_id)
                    needs_update = True
                
                # Check if week needs updating
                cursor.execute("SELECT week FROM games WHERE id = %s", (existing_game['id'],))
                current_week = cursor.fetchone()['week']
                if current_week != week:
                    update_fields.append("week = %s")
                    update_values.append(week)
                    needs_update = True
                
                if needs_update:
                    update_values.append(existing_game['id'])
                    cursor.execute(f"""
                        UPDATE games 
                        SET {', '.join(update_fields)}, updated_at = NOW()
                        WHERE id = %s
                    """, tuple(update_values))
                    updated_count += 1
                    print(f"[UPDATE] {game_date}: {home_team_name} vs {away_team_name} (Week {week})")
                else:
                    skipped_count += 1
            else:
                # Create new game
                # Use 'pending' status for all new games (they'll be 'locked' when scores are entered)
                status = 'pending'
                
                cursor.execute("""
                    INSERT INTO games (
                        home_team_id, 
                        away_team_id, 
                        game_date, 
                        season_id, 
                        status,
                        week,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (home_team_id, away_team_id, game_date, season_id, status, week))
                
                new_game_id = cursor.fetchone()['id']
                created_count += 1
                print(f"[CREATE] {game_date}: {home_team_name} vs {away_team_name} (Week {week}) - ID: {new_game_id}")
        
        conn.commit()
        
        print()
        print("=" * 60)
        print("Schedule Load Summary")
        print("=" * 60)
        print(f"Games created: {created_count}")
        print(f"Games updated: {updated_count}")
        print(f"Games skipped (already correct): {skipped_count}")
        print(f"Total processed: {created_count + updated_count + skipped_count}")
        
        if errors:
            print()
            print("Errors:")
            for error in errors:
                print(f"  - {error}")
        
        print()
        print("=" * 60)
        print("[SUCCESS] Schedule loaded successfully!")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        sys.exit(1)


if __name__ == '__main__':
    load_schedule()

