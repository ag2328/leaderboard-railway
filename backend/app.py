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
from flask import Flask, jsonify, request
from flask_cors import CORS
from models import (
    get_active_season, get_season_by_name,
    get_all_teams, get_team_by_id,
    get_team_standings, get_team_standing,
    get_team_games, get_game_by_id, get_game_summary,
    get_team_players, get_team_goalie
)
from sync_service import (
    process_pending_games,
    manual_sync_trigger,
    recalculate_all_stats,
    get_sync_status
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

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

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/api/standings', methods=['GET'])
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


@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get all teams."""
    teams = get_all_teams()
    return jsonify({'teams': teams})


@app.route('/api/teams/<int:team_id>', methods=['GET'])
def get_team(team_id):
    """Get a specific team."""
    team = get_team_by_id(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    return jsonify({'team': team})


@app.route('/api/teams/<int:team_id>/games', methods=['GET'])
def get_team_games_endpoint(team_id):
    """Get all games for a team in a season."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    games = get_team_games(team_id, season['id'])
    
    # Get game summaries for each game
    games_with_summaries = []
    for game in games:
        summary = get_game_summary(game['id'])
        game_data = dict(game)
        if summary:
            game_data['summary'] = dict(summary)
        games_with_summaries.append(game_data)
    
    return jsonify({
        'team_id': team_id,
        'season': season['name'],
        'games': games_with_summaries
    })


@app.route('/api/teams/<int:team_id>/players', methods=['GET'])
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


@app.route('/api/teams/<int:team_id>/goalie', methods=['GET'])
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


@app.route('/api/games/<int:game_id>', methods=['GET'])
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


@app.route('/api/games/<int:game_id>/summary', methods=['GET'])
def get_game_summary_endpoint(game_id):
    """Get game summary for a game."""
    summary = get_game_summary(game_id)
    if not summary:
        return jsonify({'error': 'Game summary not found'}), 404
    return jsonify({'summary': summary})


# ============================================================================
# Admin API Endpoints (Protected - add auth later if needed)
# ============================================================================

@app.route('/api/admin/sync-games', methods=['POST'])
def sync_games():
    """Manually trigger processing of pending games."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    result = process_pending_games(season['id'])
    return jsonify(result)


@app.route('/api/admin/sync-status', methods=['GET'])
def sync_status():
    """Get current sync status."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    status = get_sync_status(season['id'])
    return jsonify(status)


@app.route('/api/admin/manual-sync', methods=['POST'])
def manual_sync():
    """Manually trigger stats update for processed games."""
    season = get_season_from_request()
    if not season:
        return jsonify({'error': 'Season not found'}), 404
    
    result = manual_sync_trigger(season['id'])
    return jsonify(result)


@app.route('/api/admin/recalculate-stats', methods=['POST'])
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

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

