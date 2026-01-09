#!/usr/bin/env python3
"""
Export all players and goalies from database to a text file.

Creates a formatted text file with all roster data for easy review.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# Get project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'roster_export.txt')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)


def export_roster():
    """Export all players and goalies to text file."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        output_lines = []
        output_lines.append("=" * 80)
        output_lines.append("LEGENDS HOCKEY - SPRING 2026 ROSTER")
        output_lines.append("=" * 80)
        output_lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("")
        
        # Get teams
        cursor.execute("SELECT id, name FROM teams ORDER BY name")
        teams = cursor.fetchall()
        team_map = {t['id']: t['name'] for t in teams}
        
        # Export Players
        output_lines.append("=" * 80)
        output_lines.append("PLAYERS")
        output_lines.append("=" * 80)
        output_lines.append("")
        
        for team_id, team_name in sorted(team_map.items()):
            output_lines.append(f"\n{team_name.upper()}")
            output_lines.append("-" * 80)
            
            cursor.execute("""
                SELECT id, name, full_name, jersey_number, customer_id, team_id
                FROM players
                WHERE team_id = %s
                ORDER BY jersey_number NULLS LAST, name
            """, (team_id,))
            
            players = cursor.fetchall()
            
            if not players:
                output_lines.append("  (No players)")
            else:
                # Header
                output_lines.append(f"{'ID':<6} {'Jersey':<8} {'Name (Display)':<25} {'Full Name (Announcer)':<30} {'Customer ID':<12}")
                output_lines.append("-" * 80)
                
                for p in players:
                    player_id = str(p['id']) if p['id'] else 'N/A'
                    jersey = str(p['jersey_number']) if p['jersey_number'] else 'None'
                    display_name = p.get('name', 'N/A')
                    full_name = p.get('full_name', 'N/A') or 'N/A'
                    customer_id = p.get('customer_id', 'N/A') or 'N/A'
                    
                    output_lines.append(f"{player_id:<6} {jersey:<8} {display_name:<25} {full_name:<30} {customer_id:<12}")
            
            output_lines.append("")
        
        # Export Goalies
        output_lines.append("")
        output_lines.append("=" * 80)
        output_lines.append("GOALIES")
        output_lines.append("=" * 80)
        output_lines.append("")
        
        cursor.execute("""
            SELECT g.*, t.name as team_name
            FROM goalies g
            LEFT JOIN teams t ON g.team_id = t.id
            WHERE g.status = 'active'
            ORDER BY t.name, g.last_name
        """)
        goalies = cursor.fetchall()
        
        if not goalies:
            output_lines.append("  (No active goalies)")
        else:
            # Header
            output_lines.append(f"{'ID':<6} {'Jersey':<8} {'First Name':<20} {'Last Name':<20} {'Team':<15} {'Status':<12}")
            output_lines.append("-" * 80)
            
            for g in goalies:
                goalie_id = str(g['id']) if g['id'] else 'N/A'
                jersey = str(g['jersey_number']) if g['jersey_number'] else 'None'
                first_name = g.get('first_name', 'N/A')
                last_name = g.get('last_name', 'N/A')
                team_name = g.get('team_name', 'N/A')
                status = g.get('status', 'N/A')
                
                output_lines.append(f"{goalie_id:<6} {jersey:<8} {first_name:<20} {last_name:<20} {team_name:<15} {status:<12}")
        
        output_lines.append("")
        output_lines.append("=" * 80)
        output_lines.append("SUMMARY")
        output_lines.append("=" * 80)
        output_lines.append("")
        
        # Count players by team
        for team_id, team_name in sorted(team_map.items()):
            cursor.execute("SELECT COUNT(*) as count FROM players WHERE team_id = %s", (team_id,))
            count = cursor.fetchone()['count']
            output_lines.append(f"{team_name}: {count} players")
        
        cursor.execute("SELECT COUNT(*) as count FROM goalies WHERE status = 'active'")
        goalie_count = cursor.fetchone()['count']
        output_lines.append(f"Active Goalies: {goalie_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM players")
        total_players = cursor.fetchone()['count']
        output_lines.append(f"Total Players: {total_players}")
        
        output_lines.append("")
        output_lines.append("=" * 80)
        
        # Write to file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        print(f"[SUCCESS] Roster exported to: {OUTPUT_FILE}")
        print()
        print(f"Total players: {total_players}")
        print(f"Active goalies: {goalie_count}")
        print()
        print("File saved successfully!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    export_roster()

