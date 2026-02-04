import argparse
import json
from datetime import datetime
from pathlib import Path

from models import get_active_season, get_team_players, get_all_teams


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCHEDULE_PATH = ROOT_DIR / "schedule_spring2026.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a roster text file for scheduled games."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="ISO date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--schedule",
        default=str(DEFAULT_SCHEDULE_PATH),
        help="Path to schedule_spring2026.json",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (defaults to scoresheets_YYYY-MM-DD.txt).",
    )
    return parser.parse_args()


def load_schedule(path):
    schedule_path = Path(path)
    if not schedule_path.exists():
        raise FileNotFoundError(f"Schedule not found: {schedule_path}")
    with schedule_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("games", [])


def format_player_line(player):
    number = player.get("jersey_number") or ""
    name = player.get("full_name") or player.get("name") or ""
    return f"{str(number).rjust(2)}  {name}"


def main():
    args = parse_args()
    date = args.date or datetime.now().date().isoformat()
    games = load_schedule(args.schedule)
    day_games = [game for game in games if game.get("date") == date]
    if not day_games:
        raise ValueError(f"No games found for date {date}")

    season = get_active_season()
    if not season:
        raise ValueError("No active season found in DB.")

    teams = {team["name"].lower(): team["id"] for team in get_all_teams()}

    lines = [f"Scoresheets - {date}", ""]

    for game in day_games:
        home = game["home_team"]
        away = game["away_team"]
        lines.append(f"Game: {away} at {home}")
        lines.append(f"Date: {date}  Week: {game['week']}")
        lines.append("")

        away_id = teams[away.lower()]
        home_id = teams[home.lower()]
        away_players = get_team_players(away_id, season["id"])
        home_players = get_team_players(home_id, season["id"])

        lines.append(f"Away Team: {away}")
        lines.append("#  Player")
        for player in away_players:
            lines.append(format_player_line(player))

        lines.append("")
        lines.append(f"Home Team: {home}")
        lines.append("#  Player")
        for player in home_players:
            lines.append(format_player_line(player))

        lines.append("")
        lines.append("----------------------------------------")
        lines.append("")

    output_path = (
        Path(args.output)
        if args.output
        else ROOT_DIR / f"scoresheets_{date}.txt"
    )
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
