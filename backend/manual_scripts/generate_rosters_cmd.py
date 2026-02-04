import os
import re
from datetime import date

import fitz
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


DATE_PATTERN = re.compile(r"^(0[1-9]|1[0-2])[/-](0[1-9]|[12][0-9]|3[01])[/-](20\\d{2})$")
TEMPLATE_SOURCE = "Blank_scoresheet.pdf"
TEMPLATE_FILLABLE = "Blank_scoresheet_fillable.pdf"

DIVISION_TEXT = "14/16U"
ROSTER_ROWS = 16
ROSTER_PLAYER_COUNT = 14

ROSTER_AWAY_Y0 = 15.1
ROSTER_AWAY_Y1 = 207.4
ROSTER_HOME_Y0 = 778.0
ROSTER_HOME_Y1 = 970.3
ROSTER_NO_X0 = 104.2
ROSTER_NO_X1 = 116.4
ROSTER_NAME_X0 = 140.9
ROSTER_NAME_X1 = 361.3


def parse_mm_dd_yyyy(value):
    match = DATE_PATTERN.match(value.strip())
    if not match:
        return None
    month = int(match.group(1))
    day = int(match.group(2))
    year = int(match.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(database_url)


def jersey_sort_key(value):
    if value is None:
        return (1, 9999)
    if isinstance(value, int):
        return (0, value)
    text = str(value).strip()
    if not text:
        return (1, 9999)
    try:
        return (0, int(text))
    except ValueError:
        return (1, 9999)


def format_mm_dd_yy(value):
    return value.strftime("%m/%d/%y")


def get_games_for_date(cursor, game_date):
    cursor.execute(
        """
        SELECT g.id,
               g.game_date::date AS game_date,
               g.week,
               ht.name AS home_team,
               at.name AS away_team
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.game_date::date = %s
        ORDER BY g.game_date, g.id
        """,
        (game_date,),
    )
    return cursor.fetchall()


def get_players_for_team(cursor, team_name):
    cursor.execute(
        """
        SELECT p.jersey_number,
               p.full_name,
               p.name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        LEFT JOIN goalies g ON p.id = g.id
        WHERE t.name = %s
          AND p.status = 'active'
          AND g.id IS NULL
        """,
        (team_name,),
    )
    players = cursor.fetchall()
    players.sort(
        key=lambda player: (
            jersey_sort_key(player["jersey_number"]),
            (player.get("full_name") or player.get("name") or ""),
        )
    )
    return players


def get_goalie_for_team(cursor, team_name):
    cursor.execute(
        """
        SELECT g.jersey_number,
               g.full_name,
               g.name
        FROM goalies g
        JOIN teams t ON g.team_id = t.id
        WHERE t.name = %s
          AND g.status = 'active'
        LIMIT 1
        """,
        (team_name,),
    )
    return cursor.fetchone()


def build_roster_lines(cursor, team_name):
    goalie = get_goalie_for_team(cursor, team_name)
    goalie_name = (goalie.get("full_name") or goalie.get("name")) if goalie else ""
    goalie_number = goalie.get("jersey_number") if goalie else ""

    players = get_players_for_team(cursor, team_name)
    players = players[:ROSTER_PLAYER_COUNT]

    roster = []
    roster.append((goalie_number, goalie_name))
    roster.append(("", ""))  # blank goalie line

    for player in players:
        name = player.get("full_name") or player.get("name") or ""
        roster.append((player.get("jersey_number") or "", name))

    while len(roster) < ROSTER_ROWS:
        roster.append(("", ""))

    return roster[:ROSTER_ROWS]


def add_text_field(page, name, rect, font_size=8):
    widget = fitz.Widget()
    widget.field_name = name
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(rect)
    widget.text_font = "helv"
    widget.text_fontsize = font_size
    widget.text_color = (0, 0, 0)
    widget.border_width = 0
    page.add_widget(widget)


def rect_right_of(label_rect, width, height, x_gap=6):
    y_center = (label_rect.y0 + label_rect.y1) / 2
    y0 = y_center - (height / 2)
    y1 = y0 + height
    x0 = label_rect.x1 + x_gap
    x1 = x0 + width
    return (x0, y0, x1, y1)


def pick_label_rect(rects, y_min, y_max):
    for rect in rects:
        if y_min <= rect.y0 <= y_max:
            return rect
    return rects[0] if rects else None


def ensure_fillable_template():
    if os.path.exists(TEMPLATE_FILLABLE):
        return
    if not os.path.exists(TEMPLATE_SOURCE):
        raise SystemExit(f"Missing template: {TEMPLATE_SOURCE}")

    doc = fitz.open(TEMPLATE_SOURCE)
    page = doc[0]
    original_rotation = page.rotation
    if original_rotation != 0:
        page.set_rotation(0)

    visiting_labels = page.search_for("VISITING TEAM")
    home_labels = page.search_for("HOME TEAM")
    visiting_label = pick_label_rect(visiting_labels, 680, 740)
    home_label = pick_label_rect(home_labels, 690, 740)

    date_label = page.search_for("DATE")
    game_label = page.search_for("GAME")
    division_label = page.search_for("AGE DIVISION")

    if visiting_label:
        add_text_field(page, "scoreboard_away_team", rect_right_of(visiting_label, 160, 12), 9)
    if home_label:
        add_text_field(page, "scoreboard_home_team", rect_right_of(home_label, 160, 12), 9)
    if date_label:
        add_text_field(page, "game_date", rect_right_of(date_label[0], 90, 12), 9)
    if game_label:
        add_text_field(page, "game_number", rect_right_of(game_label[0], 50, 12), 9)
    if division_label:
        add_text_field(page, "division", rect_right_of(division_label[0], 70, 12), 9)

    def add_roster_fields(prefix, y0, y1):
        row_height = (y1 - y0) / ROSTER_ROWS
        for idx in range(ROSTER_ROWS):
            row_top = y0 + (idx * row_height)
            row_bottom = row_top + row_height
            no_rect = (
                ROSTER_NO_X0 + 1,
                row_top + 1,
                ROSTER_NO_X1 - 1,
                row_bottom - 1,
            )
            name_rect = (
                ROSTER_NAME_X0 + 1,
                row_top + 1,
                ROSTER_NAME_X1 - 1,
                row_bottom - 1,
            )
            add_text_field(page, f"{prefix}_no_{idx + 1:02d}", no_rect, 7)
            add_text_field(page, f"{prefix}_name_{idx + 1:02d}", name_rect, 7)

    add_roster_fields("away", ROSTER_AWAY_Y0, ROSTER_AWAY_Y1)
    add_roster_fields("home", ROSTER_HOME_Y0, ROSTER_HOME_Y1)

    if original_rotation != 0:
        page.set_rotation(original_rotation)

    doc.save(TEMPLATE_FILLABLE)
    doc.close()


def fill_scoresheet(output_path, fields):
    doc = fitz.open(TEMPLATE_FILLABLE)
    for page in doc:
        for widget in page.widgets() or []:
            if widget.field_name in fields:
                widget.field_value = fields[widget.field_name]
                widget.update()
    doc.save(output_path)
    doc.close()


def format_filename(value):
    safe = value.lower().replace(" ", "_")
    safe = re.sub(r"[^a-z0-9_]+", "", safe)
    return safe


if __name__ == "__main__":
    load_dotenv()

    raw_date = input("Enter game date (MM-DD-YYYY): ").strip()
    game_date = parse_mm_dd_yyyy(raw_date)
    if not game_date:
        raise SystemExit("Invalid date format. Please use MM-DD-YYYY (e.g., 01-25-2026).")

    ensure_fillable_template()

    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        games = get_games_for_date(cursor, game_date)

        if not games:
            raise SystemExit(f"No games found for {game_date}.")

        for game in games:
            away_team = game["away_team"]
            home_team = game["home_team"]
            week = game["week"]

            away_roster = build_roster_lines(cursor, away_team)
            home_roster = build_roster_lines(cursor, home_team)

            fields = {
                "scoreboard_away_team": away_team,
                "scoreboard_home_team": home_team,
                "game_date": format_mm_dd_yy(game["game_date"]),
                "game_number": str(week),
                "division": DIVISION_TEXT,
            }

            for idx, (number, name) in enumerate(away_roster, start=1):
                number_text = "" if not number else str(number).strip()
                fields[f"away_no_{idx:02d}"] = number_text
                fields[f"away_name_{idx:02d}"] = name

            for idx, (number, name) in enumerate(home_roster, start=1):
                number_text = "" if not number else str(number).strip()
                fields[f"home_no_{idx:02d}"] = number_text
                fields[f"home_name_{idx:02d}"] = name

            filename = (
                f"scoresheet_{game['game_date']}_"
                f"{format_filename(away_team)}_at_{format_filename(home_team)}.pdf"
            )
            fill_scoresheet(filename, fields)
            print(f"Saved: {filename}")
