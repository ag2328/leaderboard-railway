#!/usr/bin/env python3
"""
Simulate a test game for troubleshooting.

Game: Canadiens at Red Wings
- Creates game, events, summary, and calculates stats
- Provides reset functionality to clear test data
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from models import get_season_by_name, get_team_by_id
from stats_calculator import (
    calculate_game_summary,
    calculate_goalie_game_stats
)
from sync_service import update_aggregated_stats_for_game

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
CURRENT_SEASON = 'Spring 2026'

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

# Test game data
TEST_GAMES = {
    'game1': {
        'home_team': 'Canadiens',
        'away_team': 'Maple Leafs',
        'game_date': '2026-01-11',  # Use actual scheduled game date
        'goals': [
            # Canadiens goals
            {'scorer': 37, 'assists': [18], 'team': 'Canadiens', 'period': 1},  # Jack W. assisted by Brady M.
            {'scorer': 23, 'assists': [15], 'team': 'Canadiens', 'period': 1},  # Luca H. assisted by Marley M.
            {'scorer': 4, 'assists': [2, 23], 'team': 'Canadiens', 'period': 2},  # Eithan M. assisted by Cristian K. and Luca H.
            {'scorer': 22, 'assists': [18], 'team': 'Canadiens', 'period': 2},  # Jake F. assisted by Brady M.
            {'scorer': 2, 'assists': [21], 'team': 'Canadiens', 'period': 3},  # Cristian K. assisted by Owen H.
            # Maple Leafs goals
            {'scorer': 12, 'assists': [19], 'team': 'Maple Leafs', 'period': 1},  # Terry M. assisted by Sebastian R.
            {'scorer': 29, 'assists': [24], 'team': 'Maple Leafs', 'period': 2},  # Jack P. assisted by Julian R.
            {'scorer': 19, 'assists': [], 'team': 'Maple Leafs', 'period': 3},  # Sebastian R. unassisted
        ],
        'penalties': [
            {'player': 37, 'team': 'Canadiens', 'period': 2},  # Jack W.
            {'player': 12, 'team': 'Maple Leafs', 'period': 1},  # Terry M.
        ],
        'shots': {
            'Canadiens': 28,
            'Maple Leafs': 22
        },
        'scores': {
            'Canadiens': 5,
            'Maple Leafs': 3
        },
        'went_to_overtime': False,
        'went_to_shootout': False
    },
    'game2': {
        'home_team': 'Bruins',
        'away_team': 'Red Wings',
        'game_date': '2026-01-11',  # Week 1 actual scheduled game
        'goals': [
            # Regulation goals - Bruins (20 shots, 3 goals)
            {'scorer': 7, 'assists': [14], 'team': 'Bruins', 'period': 1},  # Jacoby F. assisted by Jayce A.
            {'scorer': 14, 'assists': [42], 'team': 'Bruins', 'period': 2},  # Jayce A. assisted by Nate M.
            {'scorer': 42, 'assists': [7, 18], 'team': 'Bruins', 'period': 3},  # Nate M. assisted by Jacoby F. and Phineas T.
            # Regulation goals - Red Wings (15 shots, 3 goals)
            {'scorer': 8, 'assists': [19], 'team': 'Red Wings', 'period': 1},  # Daelyn L. assisted by Josiah R.
            {'scorer': 19, 'assists': [13, 77], 'team': 'Red Wings', 'period': 2},  # Josiah R. assisted by Jason G. and Alex W.
            {'scorer': 77, 'assists': [], 'team': 'Red Wings', 'period': 3},  # Alex W. unassisted
            # Overtime goal - Bruins wins
            {'scorer': 18, 'assists': [42], 'team': 'Bruins', 'period': 4},  # Phineas T. assisted by Nate M. (OT)
        ],
        'penalties': [
            {'player': 18, 'team': 'Bruins', 'period': 2},  # Phineas T.
            {'player': 29, 'team': 'Red Wings', 'period': 2},  # Beau B.
        ],
        'shots': {
            'Bruins': 20,
            'Red Wings': 15
        },
        'scores': {
            'Bruins': 4,  # 3 regulation + 1 OT
            'Red Wings': 3
        },
        'went_to_overtime': True,
        'went_to_shootout': False
    }
}

TEST_GAME_IDS = {}  # Will store game IDs when created


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def get_player_by_jersey(team_id, jersey_number):
    """Get player by jersey number and team."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, name, jersey_number, team_id
        FROM players
        WHERE team_id = %s AND jersey_number = %s
    """, (team_id, jersey_number))
    player = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(player) if player else None


def get_goalie_by_team(team_id):
    """Get active goalie for a team."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, name, jersey_number, team_id
        FROM goalies
        WHERE team_id = %s AND status = 'active'
        LIMIT 1
    """, (team_id,))
    goalie = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(goalie) if goalie else None


def create_test_game(game_config, game_name='Test Game'):
    """Create a test game and all associated data."""
    print("=" * 60)
    print(f"Creating {game_name}")
    print("=" * 60)
    print()
    
    # Get season
    season = get_season_by_name(CURRENT_SEASON)
    if not season:
        print(f"ERROR: Season '{CURRENT_SEASON}' not found")
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get teams by name
    cursor.execute("SELECT id, name FROM teams WHERE name IN (%s, %s)", 
                   (game_config['home_team'], game_config['away_team']))
    teams = {t['name']: t for t in cursor.fetchall()}
    
    if game_config['home_team'] not in teams or game_config['away_team'] not in teams:
        print(f"ERROR: Teams not found")
        cursor.close()
        conn.close()
        return None
    
    home_team_id = teams[game_config['home_team']]['id']
    away_team_id = teams[game_config['away_team']]['id']
    
    print(f"Home Team: {game_config['home_team']} (ID: {home_team_id})")
    print(f"Away Team: {game_config['away_team']} (ID: {away_team_id})")
    print()
    
    # Create game
    cursor.execute("""
        INSERT INTO games (
            home_team_id, away_team_id, game_date, season_id, status,
            went_to_overtime, went_to_shootout,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, 'locked', %s, %s, NOW(), NOW())
        RETURNING id
    """, (home_team_id, away_team_id, game_config['game_date'], season['id'],
          game_config.get('went_to_overtime', False),
          game_config.get('went_to_shootout', False)))
    
    game_result = cursor.fetchone()
    game_id = game_result['id']
    print(f"[OK] Created game ID: {game_id}")
    
    # Assign goalies
    home_goalie = get_goalie_by_team(home_team_id)
    away_goalie = get_goalie_by_team(away_team_id)
    
    if home_goalie:
        cursor.execute("""
            INSERT INTO game_goalies (
                game_id, team_id, goalie_id, is_home_team,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, true, NOW(), NOW())
        """, (game_id, home_team_id, home_goalie['id']))
        print(f"[OK] Assigned goalie: {home_goalie['name']} (#{home_goalie['jersey_number']}) for {game_config['home_team']}")
    
    if away_goalie:
        cursor.execute("""
            INSERT INTO game_goalies (
                game_id, team_id, goalie_id, is_home_team,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, false, NOW(), NOW())
        """, (game_id, away_team_id, away_goalie['id']))
        print(f"[OK] Assigned goalie: {away_goalie['name']} (#{away_goalie['jersey_number']}) for {game_config['away_team']}")
    
    # Create events for goals
    print()
    print("Creating goal events...")
    for goal in game_config['goals']:
        team_id = home_team_id if goal['team'] == game_config['home_team'] else away_team_id
        scorer = get_player_by_jersey(team_id, goal['scorer'])
        
        if not scorer:
            print(f"  [WARN] Player #{goal['scorer']} not found for {goal['team']}")
            continue
        
        # Get assist player IDs
        assist_player_ids = []
        for assist_jersey in goal.get('assists', []):
            assister = get_player_by_jersey(team_id, assist_jersey)
            if assister:
                assist_player_ids.append(assister['id'])
            else:
                print(f"  [WARN] Player #{assist_jersey} not found for assist")
        
        # Create goal event with assists in details JSONB
        import json
        details = {'assists': assist_player_ids} if assist_player_ids else {}
        
        # Use period from goal config, default to 1 (regulation)
        period = goal.get('period', 1)
        
        cursor.execute("""
            INSERT INTO events (
                game_id, event_type, player_id, period, time_seconds,
                details, created_at, updated_at
            )
            VALUES (%s, 'goal', %s, %s, 0, %s, NOW(), NOW())
        """, (game_id, scorer['id'], period, json.dumps(details)))
        
        print(f"  [OK] Goal (P{period}): {scorer['name']} (#{goal['scorer']}) - Assists: {', '.join([f'#{a}' for a in goal.get('assists', [])]) if goal.get('assists') else 'None'}")
    
    # Create penalty events
    print()
    print("Creating penalty events...")
    for penalty in game_config.get('penalties', []):
        team_id = home_team_id if penalty['team'] == game_config['home_team'] else away_team_id
        player = get_player_by_jersey(team_id, penalty['player'])
        
        if not player:
            print(f"  [WARN] Player #{penalty['player']} not found for {penalty['team']}")
            continue
        
        period = penalty.get('period', 1)
        cursor.execute("""
            INSERT INTO events (
                game_id, event_type, player_id, period, time_seconds,
                created_at, updated_at
            )
            VALUES (%s, 'penalty', %s, %s, 0, NOW(), NOW())
        """, (game_id, player['id'], period))
        print(f"  [OK] Penalty (P{period}): {player['name']} (#{penalty['player']})")
    
    conn.commit()
    print()
    print("[OK] All events created")
    print()
    
    # Create game summary
    print("Creating game summary...")
    summary = calculate_game_summary(game_id)
    if summary:
        # Update with correct shots (calculate_game_summary uses simplified shots = goals)
        cursor.execute("""
            UPDATE game_summaries
            SET home_team_shots = %s,
                away_team_shots = %s,
                went_to_overtime = %s,
                went_to_shootout = %s,
                updated_at = NOW()
            WHERE game_id = %s
        """, (game_config['shots'][game_config['home_team']], 
              game_config['shots'][game_config['away_team']],
              game_config.get('went_to_overtime', False),
              game_config.get('went_to_shootout', False),
              game_id))
        conn.commit()
        
        print(f"  [OK] Game summary created")
        print(f"    Score: {game_config['away_team']} {summary.get('away_score', 0)} - {summary.get('home_score', 0)} {game_config['home_team']}")
        print(f"    Shots: {game_config['away_team']} {game_config['shots'][game_config['away_team']]} - {game_config['shots'][game_config['home_team']]} {game_config['home_team']}")
        if game_config.get('went_to_overtime'):
            print(f"    Went to Overtime: Yes")
        if game_config.get('went_to_shootout'):
            print(f"    Went to Shootout: Yes")
    else:
        print("  [WARN] Could not create game summary")
    
    # Calculate goalie game stats
    print()
    print("Calculating goalie game stats...")
    goalie_stats = calculate_goalie_game_stats(game_id)
    if goalie_stats:
        print(f"  [OK] Goalie game stats calculated for {len(goalie_stats)} goalie(s)")
    else:
        print("  [WARN] Could not calculate goalie game stats")
    
    # Update aggregated stats
    print()
    print("Updating aggregated stats...")
    update_aggregated_stats_for_game(game_id, season['id'])
    print("  [OK] Team standings updated")
    print("  [OK] Player season stats updated")
    print("  [OK] Goalie season stats updated")
    
    cursor.close()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"{game_name} Created Successfully!")
    print("=" * 60)
    print(f"Game ID: {game_id}")
    print(f"Date: {game_config['game_date']}")
    print(f"Matchup: {game_config['away_team']} @ {game_config['home_team']}")
    away_score = game_config['scores'][game_config['away_team']]
    home_score = game_config['scores'][game_config['home_team']]
    print(f"Score: {game_config['away_team']} {away_score} - {home_score} {game_config['home_team']}")
    if game_config.get('went_to_overtime'):
        print(f"Result: Overtime")
    print()
    
    return game_id


def reset_test_games(auto_confirm=False):
    """Delete all test games and associated data."""
    global TEST_GAME_IDS
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Find all test games
    game_ids = []
    for game_key, game_config in TEST_GAMES.items():
        cursor.execute("""
            SELECT g.id, g.game_date, ht.name as home_team, at.name as away_team
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE ht.name = %s AND at.name = %s
              AND g.game_date = %s
            ORDER BY g.created_at DESC
        """, (game_config['home_team'], game_config['away_team'], game_config['game_date']))
        games = cursor.fetchall()
        for game in games:
            game_ids.append(game['id'])
    
    if not game_ids:
        print("No test games found. Nothing to reset.")
        cursor.close()
        conn.close()
        return
    
    print("=" * 60)
    print("Resetting Test Games")
    print("=" * 60)
    print()
    print(f"Found {len(game_ids)} test game(s) to delete:")
    for game_id in game_ids:
        print(f"  - Game ID: {game_id}")
    print()
    print("This will cascade delete:")
    print("  - Game events")
    print("  - Game summaries")
    print("  - Goalie game stats")
    print("  - Game goalie assignments")
    print()
    
    if not auto_confirm:
        try:
            response = input("Are you sure you want to delete all test games? (yes/no): ")
            if response.lower() != 'yes':
                print("Reset cancelled.")
                cursor.close()
                conn.close()
                return
        except (EOFError, KeyboardInterrupt):
            print("\nReset cancelled.")
            cursor.close()
            conn.close()
            return
    
    # Delete all test games
    for game_id in game_ids:
        cursor.execute("DELETE FROM games WHERE id = %s", (game_id,))
    
    deleted = cursor.rowcount
    
    conn.commit()
    cursor.close()
    conn.close()
    
    if deleted > 0:
        print(f"[OK] Deleted {deleted} test game(s)")
        print()
        print("Note: Season stats (player_season_stats, goalie_season_stats, team_standings)")
        print("      need to be recalculated. Run the sync service to update them.")
        print()
    else:
        print("[WARN] Games not found. They may have already been deleted.")
    
    TEST_GAME_IDS = {}


def find_test_games():
    """Find all test game IDs if they exist."""
    global TEST_GAME_IDS
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    found_games = {}
    for game_key, game_config in TEST_GAMES.items():
        cursor.execute("""
            SELECT g.id, g.game_date, ht.name as home_team, at.name as away_team
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE ht.name = %s AND at.name = %s
              AND g.game_date = %s
            ORDER BY g.created_at DESC
            LIMIT 1
        """, (game_config['home_team'], game_config['away_team'], game_config['game_date']))
        
        game = cursor.fetchone()
        if game:
            found_games[game_key] = dict(game)
            TEST_GAME_IDS[game_key] = game['id']
    
    cursor.close()
    conn.close()
    
    return found_games


def create_all_test_games():
    """Create all test games."""
    global TEST_GAME_IDS
    
    created_games = []
    for game_key, game_config in TEST_GAMES.items():
        game_id = create_test_game(game_config, f"Test Game: {game_config['away_team']} @ {game_config['home_team']}")
        if game_id:
            TEST_GAME_IDS[game_key] = game_id
            created_games.append(game_id)
        print()
    
    if created_games:
        print("=" * 60)
        print("All Test Games Created!")
        print("=" * 60)
        print(f"Created {len(created_games)} game(s)")
        print("You can now refresh the web app to see the game stats!")
        print()
    
    return len(created_games) > 0


if __name__ == "__main__":
    # Check for command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'create':
            existing = find_test_games()
            if existing:
                print("[WARN] Test games already exist:")
                for key, game in existing.items():
                    print(f"  - {key}: Game ID {game['id']} ({game['away_team']} @ {game['home_team']})")
                print("\nUse 'reset' first to delete them, or use 'create --force' to recreate.")
                if '--force' not in sys.argv:
                    sys.exit(1)
                reset_test_games(auto_confirm=True)
            success = create_all_test_games()
            sys.exit(0 if success else 1)
        
        elif command == 'reset':
            reset_test_games(auto_confirm=True)
            sys.exit(0)
        
        elif command == 'status':
            existing = find_test_games()
            if existing:
                print(f"Test games found: {len(existing)}")
                for key, game in existing.items():
                    print(f"  - {key}: ID {game['id']}, Date: {game['game_date']}, Matchup: {game['away_team']} @ {game['home_team']}")
            else:
                print("No test games found.")
            sys.exit(0)
        
        else:
            print("Usage: python simulate_test_game.py [create|reset|status]")
            print()
            print("Commands:")
            print("  create       - Create all test games")
            print("  create --force - Force recreate (deletes existing first)")
            print("  reset        - Delete all test games")
            print("  status       - Check if test games exist")
            sys.exit(1)
    
    # Interactive mode (simplified for now)
    print("Test Game Simulator - Use command line arguments:")
    print("  python simulate_test_game.py create   - Create all test games")
    print("  python simulate_test_game.py reset    - Delete all test games")
    print("  python simulate_test_game.py status   - Check test games")
    sys.exit(0)

