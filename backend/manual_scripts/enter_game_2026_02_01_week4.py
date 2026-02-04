#!/usr/bin/env python3
"""
Enter game data for Week 4 (2026-02-01).

Games:
- Canadiens (home) vs Maple Leafs (away)
- Red Wings (home) vs Bruins (away)
"""

import os
import sys
import json
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from sync_service import update_aggregated_stats_for_game

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GAME_DATE = "2026-02-01"

GAMES = [
    {
        "home_team": "Canadiens",
        "away_team": "Maple Leafs",
        "home_score": 1,
        "away_score": 7,
        "home_shots": 17,
        "away_shots": 17,
        "went_to_overtime": False,
        "went_to_shootout": False,
        "goals": {
            "home": [
                {"scorer": "Jake Fife", "assists": ["Jack Wiseman"]},
            ],
            "away": [
                {"scorer": "Nathan Liu", "assists": ["Theo Rosenbaum"]},
                {"scorer": "Theo Rosenbaum", "assists": ["Nathan Liu"]},
                {"scorer": "Elijah Frizz", "assists": ["Sebastian Rivera"]},
                {
                    "scorer": "Julian",
                    "scorer_jersey": 72,
                    "assist_jerseys": [10],
                },
                {"scorer": "Noah Gaitan", "assists": []},
                {"scorer": "Austin Pollard", "assists": ["Noah Gaitan"]},
                {"scorer": "Elijah Frizz", "assists": []},
            ],
        },
        "penalties": {
            "home": [
                {"player": "Jack Wiseman", "penalty_type": "interference"},
                {"player": "Joel Jackson", "penalty_type": "roughing"},
                {"player": "Giovanni Kainz", "penalty_type": "interference"},
            ],
            "away": [
                {"player": "Noah Gaitan", "penalty_type": "boarding"},
                {
                    "player": "Noah Gaitan",
                    "penalty_type": "unsportsmanlike",
                    "minutes": 5,
                },
            ],
        },
        "goalies": {
            "home": {
                "name": "Olivia Baker",
                "shots_against": 17,
                "goals_allowed": 7,
            },
            "away": {
                "name": "Phillip Wiggins",
                "shots_against": 17,
                "goals_allowed": 1,
            },
        },
    },
    {
        "home_team": "Red Wings",
        "away_team": "Bruins",
        "home_score": 1,
        "away_score": 3,
        "home_shots": 19,
        "away_shots": 28,
        "went_to_overtime": False,
        "went_to_shootout": False,
        "goals": {
            "home": [
                {"scorer": "Henry Liffman", "assists": []},
            ],
            "away": [
                {"scorer": "Kaiden Sanchez", "assists": ["Nate McPhie"]},
                {"scorer": "Jacoby Fernandez", "assists": ["Javier Rodriguez"]},
                {"scorer": "Jadiel Lopez-Harrison", "assists": []},
            ],
        },
        "penalties": {
            "home": [
                {"player": "Ramsay Campbell", "penalty_type": "interference"},
            ],
            "away": [
                {"player": "Jadiel Lopez-Harrison", "penalty_type": "roughing"},
            ],
        },
        "goalies": {
            "home": {
                "name": "Briar Peeples",
                "shots_against": 28,
                "goals_allowed": 2,  # Empty-net goal not counted against goalie
            },
            "away": {
                "name": "Phillip Wiggins",
                "shots_against": 19,
                "goals_allowed": 1,
            },
        },
    },
]


def normalize_name(name):
    return " ".join(name.strip().split())


def split_first_last(name):
    parts = normalize_name(name).replace(".", "").split()
    if len(parts) < 2:
        return parts[0], None
    return parts[0], parts[-1]


def find_player_id_by_jersey(cursor, team_id, jersey_number):
    cursor.execute(
        """
        SELECT id
        FROM players
        WHERE team_id = %s AND jersey_number = %s
        """,
        (team_id, jersey_number),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return matches[0]["id"]
    if not matches:
        raise ValueError(
            f"Player with jersey #{jersey_number} not found on team_id {team_id}"
        )
    raise ValueError(
        f"Multiple players matched jersey #{jersey_number} on team_id {team_id}"
    )


def find_player_id(cursor, team_id, name):
    normalized = normalize_name(name)
    cursor.execute(
        """
        SELECT id, full_name, name
        FROM players
        WHERE team_id = %s
          AND (lower(full_name) = lower(%s) OR lower(name) = lower(%s))
        """,
        (team_id, normalized, normalized),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) > 1:
        raise ValueError(f"Multiple players matched '{name}' on team_id {team_id}")

    first, last = split_first_last(normalized)
    if not last:
        raise ValueError(f"Player '{name}' not found on team_id {team_id}")
    last_initial = last[0]
    first_pattern = f"{first}%"
    last_initial_pattern = f"% {last_initial}%"
    cursor.execute(
        """
        SELECT id, full_name, name
        FROM players
        WHERE team_id = %s
          AND (
                (full_name ILIKE %s AND full_name ILIKE %s)
             OR (name ILIKE %s AND name ILIKE %s)
          )
        """,
        (
            team_id,
            first_pattern,
            last_initial_pattern,
            first_pattern,
            last_initial_pattern,
        ),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return matches[0]["id"]
    if not matches:
        raise ValueError(f"Player '{name}' not found on team_id {team_id}")
    raise ValueError(f"Multiple players matched '{name}' on team_id {team_id}")


def find_goalie_id(cursor, name):
    normalized = normalize_name(name)
    cursor.execute(
        """
        SELECT id, full_name, name, team_id
        FROM goalies
        WHERE lower(full_name) = lower(%s) OR lower(name) = lower(%s)
        """,
        (normalized, normalized),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) > 1:
        raise ValueError(f"Multiple goalies matched '{name}'")

    first, last = split_first_last(normalized)
    if not last:
        raise ValueError(f"Goalie '{name}' not found")
    last_initial = last[0]
    first_pattern = f"{first}%"
    last_initial_pattern = f"% {last_initial}%"
    cursor.execute(
        """
        SELECT id, full_name, name
        FROM goalies
        WHERE (full_name ILIKE %s AND full_name ILIKE %s)
           OR (name ILIKE %s AND name ILIKE %s)
        """,
        (
            first_pattern,
            last_initial_pattern,
            first_pattern,
            last_initial_pattern,
        ),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return matches[0]["id"]
    if not matches:
        raise ValueError(f"Goalie '{name}' not found")
    raise ValueError(f"Multiple goalies matched '{name}'")


def get_game(cursor, game_date, home_team, away_team):
    cursor.execute(
        """
        SELECT g.id, g.season_id, ht.id as home_team_id, at.id as away_team_id
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.game_date::date = %s::date AND ht.name = %s AND at.name = %s
        """,
        (game_date, home_team, away_team),
    )
    return cursor.fetchone()


def clear_existing_game_data(cursor, game_id):
    cursor.execute("DELETE FROM events WHERE game_id = %s", (game_id,))
    cursor.execute("DELETE FROM goalie_game_stats WHERE game_id = %s", (game_id,))
    cursor.execute("DELETE FROM game_goalies WHERE game_id = %s", (game_id,))


def insert_goal_event(cursor, game_id, player_id, period=1, assists=None, details=None):
    payload = details or {}
    if assists:
        payload["assists"] = assists
    cursor.execute(
        """
        INSERT INTO events (
            game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at
        )
        VALUES (%s, 'goal', %s, %s, 0, %s, NOW(), NOW())
        """,
        (game_id, player_id, period, json.dumps(payload) if payload else None),
    )


def insert_penalty_event(cursor, game_id, player_id, period=1, penalty_type=None, minutes=None):
    details = {}
    if penalty_type:
        details["penalty_type"] = penalty_type
    if minutes is not None:
        details["minutes"] = minutes
    cursor.execute(
        """
        INSERT INTO events (
            game_id, event_type, player_id, period, time_seconds, details, created_at, updated_at
        )
        VALUES (%s, 'penalty', %s, %s, 0, %s, NOW(), NOW())
        """,
        (game_id, player_id, period, json.dumps(details) if details else None),
    )


def assign_goalie(cursor, game_id, team_id, goalie_id, is_home_team):
    cursor.execute(
        """
        INSERT INTO game_goalies (
            game_id, team_id, goalie_id, is_home_team, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, NOW(), NOW())
        """,
        (game_id, team_id, goalie_id, is_home_team),
    )


def upsert_goalie_stats(cursor, game_id, goalie_id, team_id, shots_against, goals_allowed):
    saves = shots_against - goals_allowed
    save_percentage = round((saves / shots_against), 3) if shots_against > 0 else 0.0
    cursor.execute(
        """
        INSERT INTO goalie_game_stats (
            game_id, goalie_id, team_id,
            shots_against, goals_allowed, saves, save_percentage,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (game_id, goalie_id) DO UPDATE SET
            team_id = EXCLUDED.team_id,
            shots_against = EXCLUDED.shots_against,
            goals_allowed = EXCLUDED.goals_allowed,
            saves = EXCLUDED.saves,
            save_percentage = EXCLUDED.save_percentage,
            updated_at = NOW()
        """,
        (game_id, goalie_id, team_id, shots_against, goals_allowed, saves, save_percentage),
    )


def get_outcome(home_score, away_score, went_to_overtime, went_to_shootout):
    if home_score > away_score:
        if went_to_shootout:
            return "so_win"
        if went_to_overtime:
            return "ot_win"
        return "regulation_win"
    if away_score > home_score:
        if went_to_shootout:
            return "so_loss"
        if went_to_overtime:
            return "ot_loss"
        return "regulation_loss"
    return "tie"


def upsert_game_summary(
    cursor,
    game_id,
    season_id,
    home_score,
    away_score,
    home_shots,
    away_shots,
    outcome,
    winner_team_id,
    went_to_overtime,
    went_to_shootout,
):
    cursor.execute(
        """
        INSERT INTO game_summaries (
            game_id, season_id,
            home_team_score, away_team_score,
            home_team_shots, away_team_shots,
            game_outcome, winner_team_id,
            went_to_overtime, went_to_shootout,
            processed_at, awaiting_manual_update,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), false, NOW(), NOW())
        ON CONFLICT (game_id) DO UPDATE SET
            home_team_score = EXCLUDED.home_team_score,
            away_team_score = EXCLUDED.away_team_score,
            home_team_shots = EXCLUDED.home_team_shots,
            away_team_shots = EXCLUDED.away_team_shots,
            game_outcome = EXCLUDED.game_outcome,
            winner_team_id = EXCLUDED.winner_team_id,
            went_to_overtime = EXCLUDED.went_to_overtime,
            went_to_shootout = EXCLUDED.went_to_shootout,
            processed_at = EXCLUDED.processed_at,
            awaiting_manual_update = false,
            updated_at = NOW()
        """,
        (
            game_id,
            season_id,
            home_score,
            away_score,
            home_shots,
            away_shots,
            outcome,
            winner_team_id,
            went_to_overtime,
            went_to_shootout,
        ),
    )


def update_game_record(
    cursor,
    game_id,
    outcome,
    winner_team_id,
    went_to_overtime,
    went_to_shootout,
):
    cursor.execute(
        """
        UPDATE games
        SET status = 'locked',
            game_outcome = %s,
            winner_team_id = %s,
            went_to_overtime = %s,
            went_to_shootout = %s,
            leaderboard_processed_at = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            outcome,
            winner_team_id,
            went_to_overtime,
            went_to_shootout,
            datetime.now(),
            game_id,
        ),
    )


def ensure_score_matches_events(
    cursor,
    game_id,
    team_id,
    team_key,
    expected_score,
    existing_goal_count,
):
    missing = expected_score - existing_goal_count
    if missing < 0:
        raise ValueError(
            f"Goal count exceeds final score for {team_key} (expected {expected_score}, got {existing_goal_count})"
        )
    for _ in range(missing):
        insert_goal_event(
            cursor,
            game_id,
            player_id=None,
            details={"team": team_key, "unknown_scorer": True, "final_score_only": True},
        )


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        for game in GAMES:
            matchup = f"{game['away_team']} @ {game['home_team']}"
            db_game = get_game(cursor, GAME_DATE, game["home_team"], game["away_team"])
            if not db_game:
                raise ValueError(f"Game not found for {GAME_DATE}: {matchup}")

            game_id = db_game["id"]
            season_id = db_game["season_id"]
            home_team_id = db_game["home_team_id"]
            away_team_id = db_game["away_team_id"]

            clear_existing_game_data(cursor, game_id)

            # Goals
            home_goal_count = 0
            for goal in game["goals"]["home"]:
                if goal.get("scorer_jersey") is not None:
                    scorer_id = find_player_id_by_jersey(
                        cursor, home_team_id, goal["scorer_jersey"]
                    )
                else:
                    scorer_id = find_player_id(cursor, home_team_id, goal["scorer"])

                assist_ids = []
                assist_names = goal.get("assists", [])
                assist_jerseys = goal.get("assist_jerseys", [])
                if assist_jerseys:
                    assist_ids.extend(
                        find_player_id_by_jersey(cursor, home_team_id, number)
                        for number in assist_jerseys
                    )
                if assist_names:
                    assist_ids.extend(
                        find_player_id(cursor, home_team_id, name)
                        for name in assist_names
                    )
                insert_goal_event(cursor, game_id, scorer_id, assists=assist_ids)
                home_goal_count += 1

            away_goal_count = 0
            for goal in game["goals"]["away"]:
                if goal.get("scorer_jersey") is not None:
                    scorer_id = find_player_id_by_jersey(
                        cursor, away_team_id, goal["scorer_jersey"]
                    )
                else:
                    scorer_id = find_player_id(cursor, away_team_id, goal["scorer"])

                assist_ids = []
                assist_names = goal.get("assists", [])
                assist_jerseys = goal.get("assist_jerseys", [])
                if assist_jerseys:
                    assist_ids.extend(
                        find_player_id_by_jersey(cursor, away_team_id, number)
                        for number in assist_jerseys
                    )
                if assist_names:
                    assist_ids.extend(
                        find_player_id(cursor, away_team_id, name)
                        for name in assist_names
                    )
                insert_goal_event(cursor, game_id, scorer_id, assists=assist_ids)
                away_goal_count += 1

            ensure_score_matches_events(
                cursor, game_id, home_team_id, "home", game["home_score"], home_goal_count
            )
            ensure_score_matches_events(
                cursor, game_id, away_team_id, "away", game["away_score"], away_goal_count
            )

            # Penalties
            for penalty in game["penalties"]["home"]:
                player_id = find_player_id(cursor, home_team_id, penalty["player"])
                insert_penalty_event(
                    cursor,
                    game_id,
                    player_id,
                    penalty_type=penalty.get("penalty_type"),
                    minutes=penalty.get("minutes"),
                )

            for penalty in game["penalties"]["away"]:
                player_id = find_player_id(cursor, away_team_id, penalty["player"])
                insert_penalty_event(
                    cursor,
                    game_id,
                    player_id,
                    penalty_type=penalty.get("penalty_type"),
                    minutes=penalty.get("minutes"),
                )

            # Goalies
            home_goalie_id = find_goalie_id(cursor, game["goalies"]["home"]["name"])
            away_goalie_id = find_goalie_id(cursor, game["goalies"]["away"]["name"])
            assign_goalie(cursor, game_id, home_team_id, home_goalie_id, True)
            assign_goalie(cursor, game_id, away_team_id, away_goalie_id, False)
            upsert_goalie_stats(
                cursor,
                game_id,
                home_goalie_id,
                home_team_id,
                game["goalies"]["home"]["shots_against"],
                game["goalies"]["home"]["goals_allowed"],
            )
            upsert_goalie_stats(
                cursor,
                game_id,
                away_goalie_id,
                away_team_id,
                game["goalies"]["away"]["shots_against"],
                game["goalies"]["away"]["goals_allowed"],
            )

            # Game summary + game record
            outcome = get_outcome(
                game["home_score"],
                game["away_score"],
                game["went_to_overtime"],
                game["went_to_shootout"],
            )
            winner_team_id = None
            if game["home_score"] > game["away_score"]:
                winner_team_id = home_team_id
            elif game["away_score"] > game["home_score"]:
                winner_team_id = away_team_id

            upsert_game_summary(
                cursor,
                game_id,
                season_id,
                game["home_score"],
                game["away_score"],
                game["home_shots"],
                game["away_shots"],
                outcome,
                winner_team_id,
                game["went_to_overtime"],
                game["went_to_shootout"],
            )
            update_game_record(
                cursor,
                game_id,
                outcome,
                winner_team_id,
                game["went_to_overtime"],
                game["went_to_shootout"],
            )

            conn.commit()
            update_aggregated_stats_for_game(game_id, season_id)
            print(f"[OK] Updated {matchup} (game_id={game_id})")

    except Exception as exc:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
