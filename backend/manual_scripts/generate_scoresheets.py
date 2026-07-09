import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, NumberObject, TextStringObject

from models import get_active_season, get_season_by_name, get_team_goalie, get_team_players, get_all_teams


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCHEDULE_PATH = ROOT_DIR / "schedule_spring2026.json"


def slugify(value):
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip())
    return cleaned.strip("_").lower()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate weekly USA Hockey scoresheets from schedule and DB rosters."
    )
    parser.add_argument(
        "--schedule",
        default=str(DEFAULT_SCHEDULE_PATH),
        help="Path to schedule_spring2026.json",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Path to the blank scoresheet PDF template.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT_DIR / "scoresheets_output"),
        help="Directory to write generated scoresheets.",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Week number to generate (defaults to today's date lookup).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="ISO date (YYYY-MM-DD) to generate (overrides --week if set).",
    )
    parser.add_argument(
        "--season",
        default=None,
        help="Season name override (defaults to active season in DB).",
    )
    parser.add_argument(
        "--home-side",
        choices=["left", "right"],
        default="left",
        help="Which side of the PDF is the home team roster.",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=4,
        help="Font size to use for filled fields.",
    )
    parser.add_argument(
        "--line-offset",
        type=int,
        default=1,
        help="Blank lines to prepend for roster fields.",
    )
    parser.add_argument(
        "--line-offset-meta",
        type=int,
        default=0,
        help="Blank lines to prepend for date/division/week fields.",
    )
    return parser.parse_args()


def resolve_template_path(template_arg):
    if template_arg:
        return Path(template_arg)
    preferred = Path("C:/Projects/Blank_scoresheet.pdf")
    if preferred.exists():
        return preferred
    fallback = ROOT_DIR / "Blank_scoresheet.pdf"
    return fallback


def load_schedule(path):
    schedule_path = Path(path)
    if not schedule_path.exists():
        raise FileNotFoundError(f"Schedule not found: {schedule_path}")
    with schedule_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("games", [])


def select_games(games, week=None, date_str=None):
    if date_str:
        return [game for game in games if game.get("date") == date_str]
    if week is None:
        today = datetime.now().date().isoformat()
        return [game for game in games if game.get("date") == today]
    return [game for game in games if game.get("week") == week]


def parse_date_parts(date_str):
    parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
    return f"{parsed.month:02d}", f"{parsed.day:02d}", f"{parsed.year % 100:02d}"


def get_season_id(season_name):
    if season_name:
        season = get_season_by_name(season_name)
    else:
        season = get_active_season()
    if not season:
        raise ValueError("No active season found. Use --season to specify one.")
    return season["id"], season["name"]


def build_team_lookup():
    teams = get_all_teams()
    return {team["name"].lower(): team["id"] for team in teams}


def get_team_id(team_lookup, team_name):
    team_id = team_lookup.get(team_name.lower())
    if team_id is None:
        raise ValueError(f"Team not found in DB: {team_name}")
    return team_id


def format_player_name(player):
    return player.get("full_name") or player.get("name") or ""


def format_goalie_name(goalie):
    return goalie.get("full_name") or goalie.get("name") or ""


def extract_fields(writer):
    acroform = writer._root_object.get("/AcroForm")
    if not acroform or "/Fields" not in acroform:
        raise ValueError("Template PDF does not contain AcroForm fields.")
    return [field.get_object() for field in acroform["/Fields"]]


def collect_field_entries(fields):
    entries = []
    for field in fields:
        entries.append(
            {
                "field": field,
                "name": field.get("/T"),
                "rect": field.get("/Rect"),
            }
        )
    return entries


def rename_duplicate_fields(entries):
    counts = {}
    for entry in entries:
        name = entry["name"]
        counts[name] = counts.get(name, 0) + 1

    seen = {}
    for entry in entries:
        name = entry["name"]
        if counts.get(name, 0) > 1:
            seen[name] = seen.get(name, 0) + 1
            unique_name = f"{name}__{seen[name]}"
            entry["field"].update({NameObject("/T"): TextStringObject(unique_name)})



def split_sides(entries):
    left = []
    right = []
    for entry in entries:
        rect = entry["rect"]
        if not rect:
            continue
        side = "left" if rect[0] < 400 else "right"
        if side == "left":
            left.append(entry)
        else:
            right.append(entry)
    return left, right


def set_field_value(field, value):
    field.update(
        {
            NameObject("/V"): TextStringObject(value),
            NameObject("/DV"): TextStringObject(value),
        }
    )


def set_field_font(field, size=8):
    if field.get("/FT") != "/Tx":
        return
    field.update({NameObject("/DA"): TextStringObject(f"/He {size} Tf 0 g")})


def enable_multiline(field):
    if field.get("/FT") != "/Tx":
        return
    flags = int(field.get("/Ff", 0))
    field.update({NameObject("/Ff"): NumberObject(flags | (1 << 12))})


def apply_line_offset(value, line_offset):
    if not value:
        return value
    if line_offset <= 0:
        return value
    return ("\n" * line_offset) + value


def populate_fields(
    writer,
    game,
    home_team,
    away_team,
    home_players,
    away_players,
    home_goalie,
    away_goalie,
    home_side,
    font_size,
    line_offset,
    line_offset_meta,
):
    acroform = writer._root_object.get("/AcroForm")
    acroform.update({NameObject("/NeedAppearances"): BooleanObject(True)})
    fields = extract_fields(writer)
    entries = collect_field_entries(fields)
    rename_duplicate_fields(entries)
    left_entries, right_entries = split_sides(entries)
    sides = {"left": left_entries, "right": right_entries}
    away_side = "right" if home_side == "left" else "left"

    # Single-instance fields (date, week, division)
    division = "In-House 14/16U"
    mm, dd, yy = parse_date_parts(game["date"])
    week_str = str(game["week"])

    for entry in entries:
        field = entry["field"]
        name = entry["name"]
        set_field_font(field, size=font_size)
        if name == "Division":
            enable_multiline(field)
            set_field_value(field, apply_line_offset(division, line_offset_meta))
        elif name == "Game Date MM":
            enable_multiline(field)
            set_field_value(field, apply_line_offset(mm, line_offset_meta))
        elif name == "Game Date DD":
            enable_multiline(field)
            set_field_value(field, apply_line_offset(dd, line_offset_meta))
        elif name == "Game Date YY":
            enable_multiline(field)
            set_field_value(field, apply_line_offset(yy, line_offset_meta))
        elif name == "Game Week Number":
            enable_multiline(field)
            set_field_value(field, apply_line_offset(week_str, line_offset_meta))

    # Team-level fields by side
    team_map = {
        home_side: {
            "team_name": home_team,
            "goalie_name": format_goalie_name(home_goalie) if home_goalie else "",
            "goalie_number": str(home_goalie.get("jersey_number") or "") if home_goalie else "",
            "players": home_players,
        },
        away_side: {
            "team_name": away_team,
            "goalie_name": format_goalie_name(away_goalie) if away_goalie else "",
            "goalie_number": str(away_goalie.get("jersey_number") or "") if away_goalie else "",
            "players": away_players,
        },
    }

    for side, side_entries in sides.items():
        team_data = team_map[side]
        for entry in side_entries:
            field = entry["field"]
            name = entry["name"]
            set_field_font(field, size=font_size)
            if name == "Team Name":
                set_field_value(field, team_data["team_name"])
            elif name == "Goalie First Name Goalie Last Name":
                set_field_value(
                    field, apply_line_offset(team_data["goalie_name"], line_offset)
                )
            elif name == "Goalie Jersey Number":
                set_field_value(
                    field, apply_line_offset(team_data["goalie_number"], line_offset)
                )

        player_number_entries = [
            entry
            for entry in side_entries
            if entry["name"] == "Player Jersey Number"
        ]
        player_name_entries = [
            entry
            for entry in side_entries
            if entry["name"] == "Player First Name Last Name"
        ]

        player_number_entries.sort(key=lambda e: e["rect"][1], reverse=True)
        player_name_entries.sort(key=lambda e: e["rect"][1], reverse=True)

        players = team_data["players"]
        max_rows = min(len(player_number_entries), len(player_name_entries))
        for idx in range(max_rows):
            number_value = ""
            name_value = ""
            if idx < len(players):
                player = players[idx]
                number_value = str(player.get("jersey_number") or "")
                name_value = format_player_name(player)
            number_field = player_number_entries[idx]["field"]
            name_field = player_name_entries[idx]["field"]
            enable_multiline(number_field)
            enable_multiline(name_field)
            set_field_value(
                number_field, apply_line_offset(number_value, line_offset)
            )
            set_field_value(name_field, apply_line_offset(name_value, line_offset))


def main():
    args = parse_args()
    schedule_games = load_schedule(args.schedule)
    template_path = resolve_template_path(args.template)
    if not template_path.exists():
        raise FileNotFoundError(f"Template PDF not found: {template_path}")

    season_id, season_name = get_season_id(args.season)
    team_lookup = build_team_lookup()

    games = select_games(schedule_games, week=args.week, date_str=args.date)
    if not games:
        raise ValueError("No games found for the requested week/date.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for game in games:
        home_team = game["home_team"]
        away_team = game["away_team"]

        home_team_id = get_team_id(team_lookup, home_team)
        away_team_id = get_team_id(team_lookup, away_team)

        home_players = get_team_players(home_team_id, season_id)
        away_players = get_team_players(away_team_id, season_id)
        home_goalie = get_team_goalie(home_team_id, season_id)
        away_goalie = get_team_goalie(away_team_id, season_id)

        reader = PdfReader(str(template_path))
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)

        populate_fields(
            writer,
            game,
            home_team,
            away_team,
            home_players,
            away_players,
            home_goalie,
            away_goalie,
            args.home_side,
            args.font_size,
            args.line_offset,
        )

        mm, dd, yy = parse_date_parts(game["date"])
        output_name = f"{slugify(home_team)}_vs_{slugify(away_team)}_{mm}_{dd}_{yy}.pdf"
        output_path = output_dir / output_name
        with output_path.open("wb") as handle:
            writer.write(handle)

        print(
            f"Generated {output_path} for {away_team} at {home_team} ({season_name})"
        )


if __name__ == "__main__":
    main()
