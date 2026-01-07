"""
Setup script to create the Spring 2026 season record.

Run this after running migrations to set up the initial season.
"""

import os
import sys
import psycopg2
from datetime import date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
CURRENT_SEASON = os.getenv('CURRENT_SEASON', 'Spring 2026')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)


def create_season():
    """Create the Spring 2026 season record."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if season already exists
        cursor.execute("SELECT id, name FROM seasons WHERE name = %s", (CURRENT_SEASON,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"✓ Season '{CURRENT_SEASON}' already exists (ID: {existing[0]})")
            cursor.close()
            conn.close()
            return
        
        # Create season
        # Set start date to January 1, 2026
        start_date = date(2026, 1, 1)
        
        cursor.execute("""
            INSERT INTO seasons (name, start_date, is_active)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (CURRENT_SEASON, start_date, True))
        
        season_id = cursor.fetchone()[0]
        conn.commit()
        
        print("=" * 60)
        print(f"✓ Created season: {CURRENT_SEASON}")
        print(f"  Season ID: {season_id}")
        print(f"  Start Date: {start_date}")
        print(f"  Active: True")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    create_season()

