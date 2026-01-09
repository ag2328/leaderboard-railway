"""
Stats calculation engine for the leaderboard.

Calculates:
- Game summaries (scores, shots, outcomes)
- Goalie game stats
- Team standings (aggregated)
- Player season stats (aggregated)
- Goalie season stats (aggregated)
"""

import os
import json
import psycopg2
from datetime import datetime
from models import (
    get_game_by_id, get_game_events, count_goals_by_team,
    get_team_games, get_all_teams
)
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    """Get a database connection."""
    return psycopg2.connect(DATABASE_URL)


# ============================================================================
# Points Calculation
# ============================================================================

def calculate_points(game_outcome, team_id, winner_team_id):
    """
    Calculate points for a team based on game outcome.
    
    Points system (matching Fall 2025 formula: =2*B3+1*D3+1*E3):
    - Regulation win: 2 points
    - Regulation loss: 0 points
    - Regulation tie: 1 point each
    - OT/SO win: 2 points total (1 for tie + 1 for win)
      - Counted in ties column (1 point)
      - Counted in tiebreaker wins column (1 additional point)
    - OT/SO loss: 1 point total (1 for tie, 0 for loss)
      - Counted in ties column (1 point)
      - Tiebreaker losses column gives 0 points
    """
    if game_outcome == 'regulation_win':
        return 2 if team_id == winner_team_id else 0
    elif game_outcome == 'regulation_loss':
        return 0 if team_id == winner_team_id else 2
    elif game_outcome == 'tie':
        return 1
    elif game_outcome in ['ot_win', 'so_win']:
        return 2 if team_id == winner_team_id else 1  # Winner: 1 (tie) + 1 (win) = 2, Loser: 1 (tie)
    elif game_outcome in ['ot_loss', 'so_loss']:
        return 1 if team_id == winner_team_id else 2  # Loser: 1 (tie), Winner: 2 (tie + win)
    return 0


# ============================================================================
# Game Summary Calculation
# ============================================================================

def calculate_game_summary(game_id):
    """
    Calculate and store game summary for a locked game.
    
    Creates or updates game_summaries record with:
    - Final scores
    - Shots on goal (simplified: goals + saves, or just goals for now)
    - Game outcome
    - Overtime/shootout info
    """
    game = get_game_by_id(game_id)
    if not game:
        return None
    
    if game['status'] != 'locked':
        return None
    
    # Get scores
    home_score = count_goals_by_team(game_id, game['home_team_id'])
    away_score = count_goals_by_team(game_id, game['away_team_id'])
    
    # Get events to determine max period and shots
    events = get_game_events(game_id)
    max_period = max([e['period'] for e in events], default=3)
    # Use game record's overtime/shootout flags if set, otherwise calculate from events
    went_to_overtime = game.get('went_to_overtime', False) or (max_period > 3)
    went_to_shootout = game.get('went_to_shootout', False)
    
    # Determine outcome
    if home_score > away_score:
        if went_to_shootout:
            outcome = 'so_win'
        elif went_to_overtime:
            outcome = 'ot_win'
        else:
            outcome = 'regulation_win'
        winner_id = game['home_team_id']
    elif away_score > home_score:
        if went_to_shootout:
            outcome = 'so_loss'
        elif went_to_overtime:
            outcome = 'ot_loss'
        else:
            outcome = 'regulation_loss'
        winner_id = game['away_team_id']
    else:
        outcome = 'tie'
        winner_id = None
    
    # For now, shots = goals (simplified)
    # TODO: Add actual shot tracking later
    home_shots = home_score
    away_shots = away_score
    
    # Get season_id
    season_id = game.get('season_id')
    if not season_id:
        return None
    
    # Insert or update game_summary
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO game_summaries (
            game_id, season_id,
            home_team_score, away_team_score,
            home_team_shots, away_team_shots,
            game_outcome, winner_team_id,
            went_to_overtime, went_to_shootout,
            processed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (game_id) 
        DO UPDATE SET
            home_team_score = EXCLUDED.home_team_score,
            away_team_score = EXCLUDED.away_team_score,
            home_team_shots = EXCLUDED.home_team_shots,
            away_team_shots = EXCLUDED.away_team_shots,
            game_outcome = EXCLUDED.game_outcome,
            winner_team_id = EXCLUDED.winner_team_id,
            went_to_overtime = EXCLUDED.went_to_overtime,
            went_to_shootout = EXCLUDED.went_to_shootout,
            processed_at = EXCLUDED.processed_at,
            updated_at = NOW()
    """, (
        game_id, season_id,
        home_score, away_score,
        home_shots, away_shots,
        outcome, winner_id,
        went_to_overtime, went_to_shootout,
        datetime.now()
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'game_id': game_id,
        'home_score': home_score,
        'away_score': away_score,
        'outcome': outcome,
        'winner_id': winner_id
    }


# ============================================================================
# Goalie Game Stats Calculation
# ============================================================================

def calculate_goalie_game_stats(game_id):
    """
    Calculate goalie stats for a game.
    
    Uses game_goalies table to identify which goalie(s) played in the game,
    and game_summaries to get shots and goals.
    
    For each goalie in the game, calculate:
    - Shots against
    - Goals allowed
    - Saves
    - Save percentage
    
    Handles:
    - Registered goalies (goalie_id is set)
    - Sub goalies (goalie_id is NULL, uses first_name/last_name)
    - Goalies playing for different teams
    """
    game = get_game_by_id(game_id)
    if not game:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get game summary (shots and goals)
    cursor.execute("""
        SELECT home_team_shots, away_team_shots,
               home_team_score, away_team_score
        FROM game_summaries
        WHERE game_id = %s
    """, (game_id,))
    summary = cursor.fetchone()
    
    if not summary:
        # No summary yet, can't calculate stats
        cursor.close()
        conn.close()
        return None
    
    home_team_shots, away_team_shots, home_team_score, away_team_score = summary
    
    # Get goalies assigned to this game from game_goalies table
    cursor.execute("""
        SELECT gg.id, gg.goalie_id, gg.team_id, gg.is_home_team,
               gg.first_name, gg.last_name, gg.jersey_number,
               g.name, g.full_name
        FROM game_goalies gg
        LEFT JOIN goalies g ON gg.goalie_id = g.id
        WHERE gg.game_id = %s
    """, (game_id,))
    game_goalies = cursor.fetchall()
    
    if not game_goalies:
        # No goalies assigned to this game yet
        cursor.close()
        conn.close()
        return None
    
    results = []
    
    # Calculate stats for each goalie in the game
    for gg in game_goalies:
        gg_id, goalie_id, team_id, is_home_team, first_name, last_name, jersey_number, goalie_name, goalie_full_name = gg
        
        # Determine shots against and goals allowed based on which team they're on
        if is_home_team:
            shots_against = away_team_shots
            goals_allowed = away_team_score
        else:
            shots_against = home_team_shots
            goals_allowed = home_team_score
        
        # Calculate saves and save percentage
        saves = shots_against - goals_allowed
        save_percentage = (saves / shots_against * 100) if shots_against > 0 else 0.0
        
        # Only insert stats if goalie_id is set (registered goalie)
        # Sub goalies (goalie_id is NULL) won't have game stats tracked
        if goalie_id:
            # Insert or update goalie_game_stats
            cursor.execute("""
                INSERT INTO goalie_game_stats (
                    game_id, goalie_id, team_id,
                    shots_against, goals_allowed, saves, save_percentage
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, goalie_id)
                DO UPDATE SET
                    team_id = EXCLUDED.team_id,
                    shots_against = EXCLUDED.shots_against,
                    goals_allowed = EXCLUDED.goals_allowed,
                    saves = EXCLUDED.saves,
                    save_percentage = EXCLUDED.save_percentage,
                    updated_at = NOW()
            """, (game_id, goalie_id, team_id, shots_against, goals_allowed, saves, round(save_percentage, 3)))
            
            results.append({
                'goalie_id': goalie_id,
                'team_id': team_id,
                'shots_against': shots_against,
                'goals_allowed': goals_allowed,
                'saves': saves,
                'save_percentage': round(save_percentage, 3)
            })
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return results if results else None


# ============================================================================
# Team Standings Calculation
# ============================================================================

def calculate_team_standings(team_id, season_id):
    """
    Calculate and update team standings for a season.
    
    Aggregates from game_summaries:
    - Games played
    - Wins, losses, ties
    - Tiebreaker wins/losses (OT/SO)
    - Goals scored/against
    - Points
    """
    # Get all game summaries for this team
    games = get_team_games(team_id, season_id, status='locked')
    
    wins = 0
    losses = 0
    ties = 0
    tiebreaker_wins = 0
    tiebreaker_losses = 0
    goals_scored = 0
    goals_against = 0
    points = 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for game in games:
        # Get game summary
        cursor.execute("""
            SELECT * FROM game_summaries WHERE game_id = %s
        """, (game['id'],))
        summary = cursor.fetchone()
        
        if not summary:
            continue
        
        is_home = game['home_team_id'] == team_id
        team_score = summary[3] if is_home else summary[4]  # home_score or away_score
        opp_score = summary[4] if is_home else summary[3]
        
        goals_scored += team_score
        goals_against += opp_score
        
        outcome = summary[7]  # game_outcome (stored from home team's perspective)
        winner_id = summary[8]  # winner_team_id
        
        # Determine if this team won, lost, or tied
        # outcome is from home team's perspective, so we need to check who actually won
        if winner_id is None:
            # Regulation tie game (NOT OT/SO games)
            ties += 1
            points += 1
        elif winner_id == team_id:
            # This team won
            if outcome in ['regulation_win', 'regulation_loss']:
                # Regulation win (outcome could be 'regulation_win' if home won, or 'regulation_loss' if away won)
                wins += 1
                points += 2
            elif outcome in ['ot_win', 'ot_loss', 'so_win', 'so_loss']:
                # OT/SO win - per Fall 2025 formula: both teams get 1 point for tie, winner gets +1 for win
                # Counted in ties column (1 point) + tiebreaker wins column (1 point) = 2 points total
                ties += 1  # Count as a tie (game was tied at end of regulation)
                wins += 1  # Count as a win (won in OT/SO)
                tiebreaker_wins += 1  # Track for tiebreaker purposes (additional point)
                points += 2  # 1 for tie + 1 for win = 2 points total
        else:
            # This team lost
            if outcome in ['regulation_win', 'regulation_loss']:
                # Regulation loss
                losses += 1
                points += 0
            elif outcome in ['ot_win', 'ot_loss', 'so_win', 'so_loss']:
                # OT/SO loss - per Fall 2025 formula: both teams get 1 point for tie, loser gets 0 additional
                # Counted in ties column (1 point) + 0 from tiebreaker losses = 1 point total
                ties += 1  # Count as a tie (game was tied at end of regulation)
                losses += 1  # Count as a loss (lost in OT/SO)
                tiebreaker_losses += 1  # Track for tiebreaker purposes (but gives 0 points)
                points += 1  # 1 for tie + 0 for loss = 1 point total
    
    # Insert or update standings
    cursor.execute("""
        INSERT INTO team_standings (
            team_id, season_id,
            games_played, wins, losses, ties,
            tiebreaker_wins, tiebreaker_losses,
            goals_scored, goals_against, points
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (team_id, season_id)
        DO UPDATE SET
            games_played = EXCLUDED.games_played,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            ties = EXCLUDED.ties,
            tiebreaker_wins = EXCLUDED.tiebreaker_wins,
            tiebreaker_losses = EXCLUDED.tiebreaker_losses,
            goals_scored = EXCLUDED.goals_scored,
            goals_against = EXCLUDED.goals_against,
            points = EXCLUDED.points,
            updated_at = NOW()
    """, (
        team_id, season_id,
        len(games), wins, losses, ties,
        tiebreaker_wins, tiebreaker_losses,
        goals_scored, goals_against, points
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'team_id': team_id,
        'games_played': len(games),
        'wins': wins,
        'losses': losses,
        'ties': ties,
        'points': points
    }


# ============================================================================
# Player Season Stats Calculation
# ============================================================================

def calculate_player_season_stats(player_id, season_id):
    """
    Calculate and update player season statistics.
    
    Aggregates from events:
    - Goals
    - Assists
    - Penalties
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get player's team
    cursor.execute("SELECT team_id FROM players WHERE id = %s", (player_id,))
    player = cursor.fetchone()
    if not player:
        cursor.close()
        conn.close()
        return None
    
    team_id = player[0]
    
    # Get all games for this team in this season
    cursor.execute("""
        SELECT id FROM games 
        WHERE season_id = %s 
          AND status = 'locked'
          AND (home_team_id = %s OR away_team_id = %s)
    """, (season_id, team_id, team_id))
    game_ids = [row[0] for row in cursor.fetchall()]
    
    if not game_ids:
        cursor.close()
        conn.close()
        return None
    
    # Count goals
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE game_id = ANY(%s)
          AND player_id = %s
          AND event_type = 'goal'
    """, (game_ids, player_id))
    goals = cursor.fetchone()[0]
    
    # Count assists (from goal events' details JSONB)
    # Check if player_id is in the assists array using JSONB operators
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE game_id = ANY(%s)
          AND event_type = 'goal'
          AND details ? 'assists'
          AND details->'assists' @> %s::jsonb
    """, (game_ids, json.dumps([player_id])))
    assists = cursor.fetchone()[0]
    
    # Count penalties
    cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE game_id = ANY(%s)
          AND player_id = %s
          AND event_type = 'penalty'
    """, (game_ids, player_id))
    penalties = cursor.fetchone()[0]
    
    # Insert or update player stats
    cursor.execute("""
        INSERT INTO player_season_stats (
            player_id, team_id, season_id,
            goals, assists, penalties
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (player_id, season_id)
        DO UPDATE SET
            goals = EXCLUDED.goals,
            assists = EXCLUDED.assists,
            penalties = EXCLUDED.penalties,
            updated_at = NOW()
    """, (player_id, team_id, season_id, goals, assists, penalties))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'player_id': player_id,
        'goals': goals,
        'assists': assists,
        'penalties': penalties
    }


# ============================================================================
# Goalie Season Stats Calculation
# ============================================================================

def calculate_goalie_season_stats(goalie_id, season_id):
    """
    Calculate and update goalie season statistics.
    
    Aggregates from goalie_game_stats (per-game stats) across all teams.
    This allows goalies who play for multiple teams to have combined season stats.
    
    Stats calculated:
    - Shots against (sum across all games)
    - Goals allowed (sum across all games)
    - Saves (calculated)
    - Save percentage (calculated)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify goalie exists
    cursor.execute("SELECT id FROM goalies WHERE id = %s", (goalie_id,))
    goalie = cursor.fetchone()
    if not goalie:
        cursor.close()
        conn.close()
        return None
    
    # Aggregate stats from goalie_game_stats for this goalie in this season
    # This aggregates across all teams the goalie played for
    cursor.execute("""
        SELECT 
            COALESCE(SUM(shots_against), 0) as shots_against,
            COALESCE(SUM(goals_allowed), 0) as goals_allowed,
            COALESCE(SUM(saves), 0) as saves
        FROM goalie_game_stats ggs
        JOIN games g ON ggs.game_id = g.id
        WHERE ggs.goalie_id = %s
          AND g.season_id = %s
          AND g.status = 'locked'
    """, (goalie_id, season_id))
    
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        return None
    
    shots_against, goals_allowed, saves = result
    
    # Recalculate saves and save percentage (in case of data inconsistencies)
    saves = shots_against - goals_allowed
    save_percentage = (saves / shots_against * 100) if shots_against > 0 else 0.0
    
    # Get the goalie's current team_id (for display purposes, but stats are aggregated)
    cursor.execute("SELECT team_id FROM goalies WHERE id = %s", (goalie_id,))
    current_team_id = cursor.fetchone()[0]
    
    # Insert or update goalie season stats
    # Note: team_id is stored but stats are aggregated across all teams
    cursor.execute("""
        INSERT INTO goalie_season_stats (
            goalie_id, team_id, season_id,
            shots_against, goals_allowed, saves, save_percentage
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (goalie_id, season_id)
        DO UPDATE SET
            team_id = EXCLUDED.team_id,
            shots_against = EXCLUDED.shots_against,
            goals_allowed = EXCLUDED.goals_allowed,
            saves = EXCLUDED.saves,
            save_percentage = EXCLUDED.save_percentage,
            updated_at = NOW()
    """, (goalie_id, current_team_id, season_id, shots_against, goals_allowed, saves, round(save_percentage, 3)))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'goalie_id': goalie_id,
        'shots_against': shots_against,
        'goals_allowed': goals_allowed,
        'saves': saves,
        'save_percentage': round(save_percentage, 3)
    }

