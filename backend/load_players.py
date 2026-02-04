"""
Load players from players JSON into the players table.

Behavior:
- Uses customer_id when present to match existing players
- Falls back to name match if customer_id absent
- Updates team_id, jersey_number, name, full_name if changed
- Inserts new players when not found
- For goalies (is_goalie: true), creates entries in goalie_season_stats

JSON Format Expected:
{
  "players": [
    {
      "customer_id": "123",
      "first_name": "John",
      "last_name": "Doe",  // Can be "D." or full "Doe"
      "full_name": "John Doe",  // Optional - will be built if missing
      "team_name": "Bruins",
      "jersey_number": "7",
      "is_goalie": false
    }
  ]
}
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
CURRENT_SEASON = os.getenv('CURRENT_SEASON', 'Spring 2026')
# Default to merged file, allow override via command line
PLAYERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'players_spring2026_merged.json')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

# Allow override via command line
if len(sys.argv) > 1:
    PLAYERS_FILE = sys.argv[1]

if not os.path.exists(PLAYERS_FILE):
    print(f"ERROR: Players file not found: {PLAYERS_FILE}")
    sys.exit(1)


def normalize_jersey(j):
    if j is None:
        return None
    if isinstance(j, int):
        return j
    j = str(j).strip()
    if not j:
        return None
    try:
        return int(j)
    except ValueError:
        return None


def build_display_name(first, last):
    """Build public display name: 'First L.'"""
    first = (first or '').strip()
    last = (last or '').strip()
    if not first:
        return last or ''
    if not last:
        return first
    # Get first letter of last name (remove '.' if present)
    last_initial = last[0].upper()
    return f"{first} {last_initial}."


def build_full_name(first, last, provided_full=None):
    """Build full name for announcer: 'First Last'"""
    # If provided_full exists, use it (even if it's just "First L." - it's what we have)
    if provided_full and provided_full.strip():
        return provided_full.strip()
    
    # Otherwise, try to build from first + last
    first = (first or '').strip()
    last = (last or '').strip()
    if not first and not last:
        return None
    if not first:
        return last
    if not last:
        return first
    
    # If last name looks like just an initial (ends with '.'), we can't build full
    # Return None to indicate we need API data
    if last.endswith('.') and len(last) <= 2:
        return None
    
    return f"{first} {last}".strip()


def load_players():
    try:
        # Read players JSON
        print(f"Reading players from: {PLAYERS_FILE}")
        with open(PLAYERS_FILE, 'r', encoding='utf-8') as f:
            players_data = json.load(f)

        players_list = players_data.get('players', [])
        print(f"Found {len(players_list)} players in file")
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

        created = 0
        updated = 0
        skipped = 0
        goalies_processed = 0
        errors = []

        for p in players_list:
            first_name = p.get('first_name', '').strip()
            last_name = p.get('last_name', '').strip()
            provided_full_name = p.get('full_name', '').strip() or None
            
            # Build display name (public: "First L.")
            display_name = build_display_name(first_name, last_name)
            if not display_name:
                errors.append("Missing name for player record")
                continue
            
            # Build full name (announcer: "First Last") - may be None if we only have initial
            full_name = build_full_name(first_name, last_name, provided_full_name)

            team_name = p.get('team_name')
            team_id = team_map.get(team_name)
            if not team_id:
                errors.append(f"Team not found in DB: {team_name} for player {display_name}")
                continue

            jersey_number = normalize_jersey(p.get('jersey_number'))
            customer_id = (p.get('customer_id') or "").strip() or None
            is_goalie = p.get('is_goalie', False)

            # Try to find existing player
            existing = None
            if customer_id:
                cursor.execute("SELECT * FROM players WHERE customer_id = %s", (customer_id,))
                existing = cursor.fetchone()
            if not existing:
                # Fallback by exact name match (case-sensitive to avoid noise)
                cursor.execute("SELECT * FROM players WHERE name = %s", (display_name,))
                existing = cursor.fetchone()

            player_id = None
            if existing:
                player_id = existing['id']
                changes = []
                # Prepare new values with fallback to existing
                new_team_id = team_id
                new_name = display_name
                new_full_name = full_name if full_name else existing.get('full_name')
                new_jersey = jersey_number
                # Only update fields that actually change
                if existing['team_id'] != new_team_id:
                    changes.append('team_id')
                if existing['name'] != new_name:
                    changes.append('name')
                if existing.get('full_name') != new_full_name:
                    changes.append('full_name')
                if existing['jersey_number'] != new_jersey:
                    changes.append('jersey_number')
                if existing.get('customer_id') != customer_id:
                    changes.append('customer_id')

                if changes:
                    cursor.execute("""
                        UPDATE players
                        SET team_id = %s,
                            name = %s,
                            full_name = %s,
                            jersey_number = %s,
                            customer_id = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (new_team_id, new_name, new_full_name, new_jersey, customer_id, player_id))
                    updated += 1
                    print(f"[UPDATE] {display_name} -> team_id={new_team_id}, jersey={new_jersey}, customer_id={customer_id or 'NULL'}")
                else:
                    skipped += 1
            else:
                cursor.execute("""
                    INSERT INTO players (team_id, name, full_name, jersey_number, customer_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (team_id, display_name, full_name, jersey_number, customer_id))
                player_id = cursor.fetchone()['id']
                created += 1
                print(f"[CREATE] {display_name} (ID: {player_id}) -> team_id={team_id}, jersey={jersey_number}, customer_id={customer_id or 'NULL'}")
            
            # Handle goalies - ensure goalies table + stats entry
            if is_goalie:
                # Upsert goalie record (goalie_id references goalies table)
                goalie_id = None
                if full_name:
                    cursor.execute("SELECT id FROM goalies WHERE full_name = %s", (full_name,))
                else:
                    cursor.execute("SELECT id FROM goalies WHERE name = %s", (display_name,))
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

                cursor.execute("""
                    INSERT INTO goalie_season_stats (
                        goalie_id, team_id, season_id,
                        shots_against, goals_allowed, saves, save_percentage,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, 0, 0, 0, 0.0, NOW(), NOW())
                    ON CONFLICT (goalie_id, season_id)
                    DO UPDATE SET
                        team_id = EXCLUDED.team_id,
                        updated_at = NOW()
                """, (goalie_id, team_id, season_id))
                goalies_processed += 1

        conn.commit()

        conn.commit()

        print()
        print("============================================================")
        print("Players Load Summary")
        print("============================================================")
        print(f"Players created: {created}")
        print(f"Players updated: {updated}")
        print(f"Players skipped (no changes): {skipped}")
        print(f"Goalies processed: {goalies_processed}")
        if errors:
            print()
            print("Errors:")
            for e in errors:
                print(f"  - {e}")
        
        # Warn about missing full names
        cursor.execute("""
            SELECT COUNT(*) FROM players 
            WHERE full_name IS NULL AND name IS NOT NULL
        """)
        result = cursor.fetchone()
        missing_full = result['count'] if isinstance(result, dict) else result[0]
        if missing_full > 0:
            print()
            print(f"[NOTE] {missing_full} players missing full_name (need API pull for announcer)")

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
    load_players()


