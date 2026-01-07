"""
Database models and query functions for the leaderboard application.

This module provides read-only database access functions for:
- Seasons
- Teams
- Games and game summaries
- Team standings
- Player and goalie statistics
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    """Get a database connection."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(DATABASE_URL)


# ============================================================================
# Seasons
# ============================================================================

def get_season_by_name(season_name):
    """Get a season by name."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM seasons WHERE name = %s", (season_name,))
    season = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(season) if season else None


def get_active_season():
    """Get the currently active season."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM seasons WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
    season = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(season) if season else None


# ============================================================================
# Teams
# ============================================================================

def get_all_teams():
    """Get all teams."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM teams ORDER BY name")
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(team) for team in teams]


def get_team_by_id(team_id):
    """Get a team by ID."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
    team = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(team) if team else None


# ============================================================================
# Games and Game Summaries
# ============================================================================

def get_games_by_season(season_id, status='locked'):
    """Get all games for a season, optionally filtered by status."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    if status:
        cursor.execute("""
            SELECT g.*, 
                   ht.name as home_team_name,
                   at.name as away_team_name
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE g.season_id = %s AND g.status = %s
            ORDER BY g.game_date
        """, (season_id, status))
    else:
        cursor.execute("""
            SELECT g.*, 
                   ht.name as home_team_name,
                   at.name as away_team_name
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE g.season_id = %s
            ORDER BY g.game_date
        """, (season_id,))
    
    games = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(game) for game in games]


def get_team_games(team_id, season_id, status='locked'):
    """Get all games for a specific team in a season."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    if status:
        cursor.execute("""
            SELECT g.*, 
                   ht.name as home_team_name,
                   at.name as away_team_name
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE g.season_id = %s 
              AND g.status = %s
              AND (g.home_team_id = %s OR g.away_team_id = %s)
            ORDER BY g.game_date
        """, (season_id, status, team_id, team_id))
    else:
        cursor.execute("""
            SELECT g.*, 
                   ht.name as home_team_name,
                   at.name as away_team_name
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE g.season_id = %s 
              AND (g.home_team_id = %s OR g.away_team_id = %s)
            ORDER BY g.game_date
        """, (season_id, team_id, team_id))
    
    games = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(game) for game in games]


def get_game_by_id(game_id):
    """Get a game by ID."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT g.*, 
               ht.name as home_team_name,
               at.name as away_team_name
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.id = %s
    """, (game_id,))
    game = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(game) if game else None


def get_game_summary(game_id):
    """Get game summary for a game."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT gs.*,
               ht.name as home_team_name,
               at.name as away_team_name
        FROM game_summaries gs
        JOIN games g ON gs.game_id = g.id
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE gs.game_id = %s
    """, (game_id,))
    summary = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(summary) if summary else None


def get_pending_games(season_id):
    """Get games that are locked but not yet processed."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT g.*, 
               ht.name as home_team_name,
               at.name as away_team_name
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.season_id = %s 
          AND g.status = 'locked'
          AND g.leaderboard_processed_at IS NULL
        ORDER BY g.game_date
    """, (season_id,))
    games = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(game) for game in games]


# ============================================================================
# Team Standings
# ============================================================================

def get_team_standings(season_id):
    """Get team standings for a season. Returns all teams, with zero values for teams without standings."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all teams with their standings (if they exist), or zero values if they don't
    cursor.execute("""
        SELECT 
            t.id as team_id,
            t.name as team_name,
            COALESCE(ts.games_played, 0) as games_played,
            COALESCE(ts.wins, 0) as wins,
            COALESCE(ts.losses, 0) as losses,
            COALESCE(ts.ties, 0) as ties,
            COALESCE(ts.tiebreaker_wins, 0) as tiebreaker_wins,
            COALESCE(ts.tiebreaker_losses, 0) as tiebreaker_losses,
            COALESCE(ts.goals_scored, 0) as goals_scored,
            COALESCE(ts.goals_against, 0) as goals_against,
            COALESCE(ts.points, 0) as points
        FROM teams t
        LEFT JOIN team_standings ts ON t.id = ts.team_id AND ts.season_id = %s
        ORDER BY COALESCE(ts.points, 0) DESC, COALESCE(ts.wins, 0) DESC, COALESCE(ts.goals_scored, 0) DESC, t.name ASC
    """, (season_id,))
    standings = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(standing) for standing in standings]


def get_team_standing(team_id, season_id):
    """Get standings for a specific team."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT ts.*,
               t.name as team_name
        FROM team_standings ts
        JOIN teams t ON ts.team_id = t.id
        WHERE ts.team_id = %s AND ts.season_id = %s
    """, (team_id, season_id))
    standing = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(standing) if standing else None


# ============================================================================
# Player Statistics
# ============================================================================

def get_team_players(team_id, season_id):
    """Get all players for a team with their season stats."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT p.*,
               COALESCE(pss.goals, 0) as goals,
               COALESCE(pss.assists, 0) as assists,
               COALESCE(pss.penalties, 0) as penalties
        FROM players p
        LEFT JOIN player_season_stats pss ON p.id = pss.player_id AND pss.season_id = %s
        WHERE p.team_id = %s
        ORDER BY p.jersey_number NULLS LAST, p.name
    """, (season_id, team_id))
    players = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(player) for player in players]


def get_team_goalie(team_id, season_id):
    """Get goalie stats for a team. Returns goalie with zero stats if no stats exist."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT g.*,
               COALESCE(gss.shots_against, 0) as shots_against,
               COALESCE(gss.goals_allowed, 0) as goals_allowed,
               COALESCE(gss.saves, 0) as saves,
               COALESCE(gss.save_percentage, 0.0) as save_percentage
        FROM goalies g
        LEFT JOIN goalie_season_stats gss ON g.id = gss.goalie_id AND gss.season_id = %s
        WHERE g.team_id = %s AND g.status = 'active'
        LIMIT 1
    """, (season_id, team_id))
    goalie = cursor.fetchone()
    cursor.close()
    conn.close()
    if goalie:
        goalie_dict = dict(goalie)
        # Ensure all stats are integers/floats, not None
        goalie_dict['shots_against'] = goalie_dict.get('shots_against', 0) or 0
        goalie_dict['goals_allowed'] = goalie_dict.get('goals_allowed', 0) or 0
        goalie_dict['saves'] = goalie_dict.get('saves', 0) or 0
        goalie_dict['save_percentage'] = goalie_dict.get('save_percentage', 0.0) or 0.0
        return goalie_dict
    return None


# ============================================================================
# Events (for calculating stats)
# ============================================================================

def get_game_events(game_id):
    """Get all events for a game."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT e.*,
               p.name as player_name,
               p.team_id as player_team_id
        FROM events e
        LEFT JOIN players p ON e.player_id = p.id
        WHERE e.game_id = %s
        ORDER BY e.period, e.time_seconds
    """, (game_id,))
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(event) for event in events]


def count_goals_by_team(game_id, team_id):
    """Count goals scored by a team in a game."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM events e
        JOIN players p ON e.player_id = p.id
        WHERE e.game_id = %s 
          AND e.event_type = 'goal'
          AND p.team_id = %s
    """, (game_id, team_id))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count


def get_game_period_stats(game_id):
    """
    Get period-by-period stats (goals and shots) for a game.
    
    Returns a dict with:
    - goals: {home: [period1, period2, ...], away: [period1, period2, ...]}
    - shots: {home: [period1, period2, ...], away: [period1, period2, ...]}
    - periods: list of period numbers
    """
    # Get game info
    game = get_game_by_id(game_id)
    if not game:
        return None
    
    home_team_id = game['home_team_id']
    away_team_id = game['away_team_id']
    
    # Get all events for this game
    events = get_game_events(game_id)
    
    # Count goals by period and team
    goals = {'home': {}, 'away': {}}
    max_period = 3
    
    for event in events:
        if event['event_type'] == 'goal' and event.get('player_team_id'):
            period = event.get('period', 1)
            max_period = max(max_period, period)
            
            if event['player_team_id'] == home_team_id:
                goals['home'][period] = goals['home'].get(period, 0) + 1
            elif event['player_team_id'] == away_team_id:
                goals['away'][period] = goals['away'].get(period, 0) + 1
    
    # Convert to arrays (periods 1, 2, 3, etc.)
    goals_home = [goals['home'].get(i, 0) for i in range(1, max_period + 1)]
    goals_away = [goals['away'].get(i, 0) for i in range(1, max_period + 1)]
    
    # For shots, we'll use the summary data
    # Since we don't track shots by period, we'll distribute evenly
    summary = get_game_summary(game_id)
    shots_home = []
    shots_away = []
    
    if summary:
        total_shots_home = summary.get('home_team_shots', 0)
        total_shots_away = summary.get('away_team_shots', 0)
        
        # Distribute shots evenly across periods (rounded)
        if max_period > 0:
            base_home = total_shots_home // max_period
            base_away = total_shots_away // max_period
            remainder_home = total_shots_home % max_period
            remainder_away = total_shots_away % max_period
            
            for i in range(max_period):
                shots_home.append(base_home + (1 if i < remainder_home else 0))
                shots_away.append(base_away + (1 if i < remainder_away else 0))
        else:
            shots_home = [0]
            shots_away = [0]
    else:
        shots_home = [0] * max_period
        shots_away = [0] * max_period
    
    return {
        'periods': list(range(1, max_period + 1)),
        'goals': {
            'home': goals_home,
            'away': goals_away
        },
        'shots': {
            'home': shots_home,
            'away': shots_away
        },
        'totals': {
            'goals': {
                'home': sum(goals_home),
                'away': sum(goals_away)
            },
            'shots': {
                'home': sum(shots_home) if summary else 0,
                'away': sum(shots_away) if summary else 0
            }
        }
    }


def get_game_goalie_stats(game_id):
    """
    Get goalie stats for a specific game.
    
    Returns list of goalie stats with goalie info and team info.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT 
            ggs.goalie_id,
            ggs.team_id,
            ggs.shots_against,
            ggs.goals_allowed,
            ggs.saves,
            ggs.save_percentage,
            g.name,
            g.full_name,
            g.jersey_number,
            t.name as team_name
        FROM goalie_game_stats ggs
        JOIN goalies g ON ggs.goalie_id = g.id
        JOIN teams t ON ggs.team_id = t.id
        WHERE ggs.game_id = %s
        ORDER BY ggs.team_id, g.name
    """, (game_id,))
    goalies = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(goalie) for goalie in goalies]

