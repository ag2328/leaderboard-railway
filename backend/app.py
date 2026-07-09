"""
Flask application for the leaderboard API.

Provides public endpoints for:
- Team standings
- Game summaries
- Player statistics
- Goalie statistics

And admin endpoints for:
- Manual sync triggers
- Sync status
- Recalculation
"""

import os
from datetime import datetime, date
from flask import Flask, Blueprint, jsonify, request, send_from_directory
from flask_cors import CORS
from models import (
    get_active_season, get_season_by_name,
    get_all_teams, get_team_by_id,
    get_team_standings, get_team_standing,
    get_team_games, get_game_by_id, get_game_summary,
    get_team_players, get_team_goalie, get_game_goalie_stats,
    get_game_period_stats, get_game_events, get_db_connection
)
from sync_service import (
    process_pending_games, process_single_game,
    manual_sync_trigger,
    recalculate_all_stats,
    get_sync_status
)
from dotenv import load_dotenv

load_dotenv()

# Configure Flask to serve frontend static files
# Get the path to the frontend directory (one level up from backend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, 
            static_folder=FRONTEND_DIR,
            static_url_path='/spring2026')
CORS(app)  # Enable CORS for frontend

# Create Blueprint with /spring2026 prefix
main_bp = Blueprint('main', __name__)

# Custom JSON encoder to handle datetime/date objects
def convert_datetime_to_iso(obj):
    """Recursively convert datetime/date objects to ISO format strings."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_iso(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_iso(item) for item in obj]
    return obj

# Add request logging middleware (log every request)
@app.before_request
def log_request_info():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    client_ip = forwarded_for.split(',')[0].strip() if forwarded_for else request.remote_addr
    print(
        f"[Request] {request.method} {request.path} ip={client_ip}",
        flush=True
    )

# Configuration
CURRENT_SEASON = os.getenv('CURRENT_SEASON', 'Spring 2026')
AUTO_SYNC_ENABLED = os.getenv('AUTO_SYNC_ENABLED', 'false').lower() == 'true'


# ============================================================================
# Helper Functions
# ============================================================================

def get_season_from_request():
    """Get season from query parameter or use active season."""
    season_name = request.args.get('season', CURRENT_SEASON)
    season = get_season_by_name(season_name)
    if not season:
        season = get_active_season()
    return season


# ============================================================================
# Public API Endpoints
# ============================================================================

@main_bp.route('/', methods=['GET'])
def root():
    """Serve the frontend index.html."""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@main_bp.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint with database connection test."""
    try:
        health_status = {
            'status': 'ok',
            'database': 'unknown',
            'environment': {
                'current_season': CURRENT_SEASON,
                'auto_sync_enabled': AUTO_SYNC_ENABLED,
                'flask_env': os.getenv('FLASK_ENV', 'not set'),
                'database_url_set': bool(os.getenv('DATABASE_URL'))
            }
        }
        
        # Test database connection
        try:
            from models import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT version();')
            db_version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            health_status['database'] = {
                'status': 'connected',
                'version': db_version.split(',')[0]  # Just the PostgreSQL version
            }
        except ValueError as e:
            # DATABASE_URL not set
            health_status['status'] = 'error'
            health_status['database'] = {
                'status': 'error',
                'error': 'DATABASE_URL not configured: ' + str(e)
            }
            return jsonify(health_status), 500
        except Exception as e:
            health_status['status'] = 'error'
            health_status['database'] = {
                'status': 'error',
                'error': str(e)
            }
            return jsonify(health_status), 500
        
        return jsonify(health_status)
    except Exception as e:
        # Catch any other errors in the outer try block
        import traceback
        print(f"[Health Endpoint Error] {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@main_bp.route('/api/test-db', methods=['GET'])
def test_database():
    """Test database connection and check for required tables."""
    results = {
        'connection': 'unknown',
        'tables': {},
        'season_check': {}
    }
    
    try:
        from models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute('SELECT version();')
        db_version = cursor.fetchone()[0]
        results['connection'] = {
            'status': 'connected',
            'version': db_version.split(',')[0]
        }
        
        # Check for required tables
        required_tables = ['seasons', 'teams', 'games', 'game_summaries', 
                          'team_standings', 'player_season_stats', 'goalie_season_stats']
        
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            exists = cursor.fetchone()[0]
            results['tables'][table] = 'exists' if exists else 'missing'
        
        # Check for Spring 2026 season
        cursor.execute("SELECT id, name, is_active FROM seasons WHERE name = %s", ('Spring 2026',))
        season = cursor.fetchone()
        if season:
            results['season_check'] = {
                'status': 'found',
                'id': season[0],
                'name': season[1],
                'is_active': season[2]
            }
        else:
            results['season_check'] = {
                'status': 'not_found',
                'message': 'Spring 2026 season not found. Run setup_season.py'
            }
        
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except ValueError as e:
        results['connection'] = {
            'status': 'error',
            'error': 'DATABASE_URL not configured: ' + str(e)
        }
        return jsonify(results), 500
    except Exception as e:
        results['connection'] = {
            'status': 'error',
            'error': str(e)
        }
        return jsonify(results), 500


@main_bp.route('/api/standings', methods=['GET'])
def get_standings():
    """Get team standings for a season."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    standings = get_team_standings(season['id'])
    return jsonify({
        'season': season['name'],
        'standings': standings
    })


@main_bp.route('/api/teams', methods=['GET'])
def get_teams():
    """Get all teams."""
    teams = get_all_teams()
    return jsonify({'teams': teams})


@main_bp.route('/api/teams/<int:team_id>', methods=['GET'])
def get_team(team_id):
    """Get a specific team."""
    team = get_team_by_id(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    return jsonify({'team': team})


@main_bp.route('/api/teams/<int:team_id>/games', methods=['GET'])
def get_team_games_endpoint(team_id):
    """Get all games for a team in a season."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    # Get all games regardless of status (so we can show scheduled games too)
    games = get_team_games(team_id, season['id'], status=None)
    
    # Get game summaries for each game
    games_with_summaries = []
    for game in games:
        summary = get_game_summary(game['id'])
        game_data = convert_datetime_to_iso(dict(game))
        if summary:
            game_data['summary'] = convert_datetime_to_iso(dict(summary))
        games_with_summaries.append(game_data)
    
    return jsonify({
        'team_id': team_id,
        'season': season['name'],
        'games': games_with_summaries
    })


@main_bp.route('/api/teams/<int:team_id>/players', methods=['GET'])
def get_team_players_endpoint(team_id):
    """Get player statistics for a team in a season."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    players = get_team_players(team_id, season['id'])
    return jsonify({
        'team_id': team_id,
        'season': season['name'],
        'players': players
    })


@main_bp.route('/api/teams/<int:team_id>/goalie', methods=['GET'])
def get_team_goalie_endpoint(team_id):
    """Get goalie statistics for a team in a season."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    goalie = get_team_goalie(team_id, season['id'])
    if not goalie:
        return jsonify({'error': 'Goalie not found'}), 404
    
    return jsonify({
        'team_id': team_id,
        'season': season['name'],
        'goalie': goalie
    })


@main_bp.route('/api/games/<int:game_id>', methods=['GET'])
def get_game(game_id):
    """Get a specific game."""
    game = get_game_by_id(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    summary = get_game_summary(game_id)
    game_data = dict(game)
    if summary:
        game_data['summary'] = dict(summary)
    
    return jsonify({'game': game_data})


@main_bp.route('/api/games/<int:game_id>/summary', methods=['GET'])
def get_game_summary_endpoint(game_id):
    """Get game summary for a game."""
    summary = get_game_summary(game_id)
    if not summary:
        return jsonify({'error': 'Game summary not found'}), 404
    return jsonify({'summary': summary})


@main_bp.route('/api/games/<int:game_id>/goalies', methods=['GET'])
def get_game_goalies_endpoint(game_id):
    """Get goalie stats for a specific game."""
    goalies = get_game_goalie_stats(game_id)
    if not goalies:
        return jsonify({'goalies': []}), 200
    return jsonify({'goalies': goalies})


@main_bp.route('/api/games/<int:game_id>/periods', methods=['GET'])
def get_game_periods_endpoint(game_id):
    """Get period-by-period stats for a game."""
    period_stats = get_game_period_stats(game_id)
    if not period_stats:
        return jsonify({'error': 'Game not found or no stats available'}), 404
    return jsonify(period_stats)


@main_bp.route('/api/games/<int:game_id>/events-summary', methods=['GET'])
def get_game_events_summary_endpoint(game_id):
    """Get goal/assist summary for a game (grouped by team)."""
    game = get_game_by_id(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    home_team_id = game['home_team_id']
    away_team_id = game['away_team_id']

    events = get_game_events(game_id)
    goal_counts = {}
    assist_counts = {}
    assist_player_ids = set()

    for event in events:
        if event.get('event_type') != 'goal':
            continue

        player_id = event.get('player_id')
        player_name = event.get('player_name')
        player_team_id = event.get('player_team_id')

        if player_id and player_name and player_team_id:
            goal_counts[player_id] = {
                'player_id': player_id,
                'player_name': player_name,
                'team_id': player_team_id,
                'count': goal_counts.get(player_id, {}).get('count', 0) + 1
            }

        details = event.get('details') or {}
        assists = details.get('assists') if isinstance(details, dict) else None
        if isinstance(assists, list):
            for assist_id in assists:
                if assist_id is None:
                    continue
                try:
                    assist_player_ids.add(int(assist_id))
                except (TypeError, ValueError):
                    continue

    if assist_player_ids:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, team_id
            FROM players
            WHERE id = ANY(%s)
        """, (list(assist_player_ids),))
        for player_id, name, team_id in cursor.fetchall():
            assist_counts[player_id] = {
                'player_id': player_id,
                'player_name': name,
                'team_id': team_id,
                'count': 0
            }
        cursor.close()
        conn.close()

    for event in events:
        if event.get('event_type') != 'goal':
            continue

        details = event.get('details') or {}
        assists = details.get('assists') if isinstance(details, dict) else None
        if isinstance(assists, list):
            for assist_id in assists:
                try:
                    assist_id = int(assist_id)
                except (TypeError, ValueError):
                    continue
                if assist_id in assist_counts:
                    assist_counts[assist_id]['count'] += 1

    def split_by_team(rows):
        home = []
        away = []
        for row in rows:
            target = home if row['team_id'] == home_team_id else away
            target.append(row)
        return {
            'home': sorted(home, key=lambda r: (-r['count'], r['player_name'])),
            'away': sorted(away, key=lambda r: (-r['count'], r['player_name']))
        }

    return jsonify({
        'game_id': game_id,
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'goals': split_by_team(goal_counts.values()),
        'assists': split_by_team(assist_counts.values())
    })


# ============================================================================
# Admin API Endpoints (Protected - add auth later if needed)
# ============================================================================

@main_bp.route('/api/admin/sync-games', methods=['POST'])
def sync_games():
    """Manually trigger processing of pending games."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    result = process_pending_games(season['id'])
    return jsonify(result)


@main_bp.route('/api/admin/process-game/<int:game_id>', methods=['POST'])
def process_single_game_endpoint(game_id):
    """Process a single game by ID (called by scorekeepr_lite after locking)."""
    result = process_single_game(game_id)
    
    if result.get('error'):
        return jsonify(result), 400
    return jsonify(result)


@main_bp.route('/api/admin/sync-status', methods=['GET'])
def sync_status():
    """Get current sync status."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    status = get_sync_status(season['id'])
    return jsonify(status)


@main_bp.route('/api/admin/manual-sync', methods=['POST'])
def manual_sync():
    """Manually trigger stats update for processed games."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    result = manual_sync_trigger(season['id'])
    return jsonify(result)


@main_bp.route('/api/admin/recalculate-stats', methods=['POST'])
def recalculate_stats():
    """Recalculate all stats for a season."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    result = recalculate_all_stats(season['id'])
    return jsonify(result)


# ============================================================================
# Error Handlers
# ============================================================================

@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404s - if it's an API route, return JSON error, otherwise serve frontend."""
    # If it's an API route, return JSON error
    if request.path.startswith('/spring2026/api/') or request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    # Otherwise, serve the frontend (for client-side routing)
    return send_from_directory(FRONTEND_DIR, 'index.html')


@main_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Register Blueprint with /spring2026 prefix
app.register_blueprint(main_bp, url_prefix='/spring2026')


# ============================================================================
# Root-level endpoints (for Railway health checks, etc.)
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway (separate from frontend)."""
    return jsonify({
        'status': 'ok',
        'service': 'leaderboard-api',
        'version': '1.0.0'
    }), 200


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)

