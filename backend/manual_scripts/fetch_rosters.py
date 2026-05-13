#!/usr/bin/env python3
"""
Fetch rosters from DaySmart Dash JSON:API and save a cleaned JSON file.

Each row includes customer_id, names, team_name, jersey_number, is_goalie, email.

If Dash only shows schedules for some teams, the API often omits roster registrations for
those teams for your login (role / privacy). The script cannot bypass that; use an account
with league or team manager access, or ask The Cube to grant roster visibility.

Configuration
-------------
1. Team resource IDs and display names live in JSON (see daysmart_roster_teams_summer2026.json).
   For Summer 2026, replace numeric keys with the team IDs from Dash (DevTools -> Network,
   open a team roster request, path .../teams/<ID>).

2. Authentication expires often. Set in repo-root .env or the environment:
     DASH_AUTHORIZATION=Bearer <token from Request headers>
     DASH_COOKIE=<Cookie header string from the same request>
   If unset, the script falls back to embedded headers (likely stale -> 401).

Usage
-----
  python fetch_rosters.py --preset summer
  python fetch_rosters.py --preset spring
  python fetch_rosters.py --teams-json path/to/teams.json --output path/out.json
  python fetch_rosters.py --preset summer --debug
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

_JWT = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVYYXVubUwifQ.eyJpYXQiOjE3Nzc1MDE0NzEsIm5iZiI6MTc3NzUwMTQ3MSwiZXhwIjoxNzc3Njc0MjcxLCJpc3MiOiIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSIsImF1ZCI6WyIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSJdLCJjb20iOiJ0aGVjdWJlIiwianRpIjoiNTI3OWM0MzU1ZGFhNjViZDJmYzFjYjA2NjVhNTFkZjkiLCJ0b2siOiI1Mjc5YzQzNTVkYWE2NWJkMmZjMWNiMDY2NWE1MWRmOSIsInV0eSI6ImN1c3RvbWVyIiwiZmlkIjoxLCJzdWIiOjU4NSwiZ3R5IjoiY2xpZW50X2NyZWRlbnRpYWxzIn0.dB1OOsD8lzW9zj00AHqetZHmwrRb7xrqvcHtcAoQV54BZjf4zgq-Dcryco1m67vQ6JKCFAQdWcoupA1xjd58LuqnEBk6y-hBhLu9PhCe5CebHPl90si2Wj5Rgmc7zWqnjwx98sne4fSGV1y7OtHHuePJ7eQSL3LnN_XXcSFwzW44B6YPvJKF36oWuwTz5s1HBuIsAvKaZ3PK2im-4wU_hp8SzG_Wg1BzeE1_orWA8SOraEVzcOl1rOd6fSJjkjJSbT8gV3BOrqwFgZMrHUF7QfoC2zB5OoepoON8VSTyOaegrvGAU7B0tntFRC--wWFfXcdgNmy37gqa-CMGuDoQVKD1ms9jOUIT2DDAGcMYYzTpLE_dy-q1Tb_bltTfh9yv2Z2mi2XesKb0qxOGdtGSPCg79zahhjzhhctg_MtbMNWs7r9e4eoU-zGYTjn_B2EKd7WmAR9PUE8y5mpyZm0eFj3YG13PY_Mzni-4EpbodWd6bxzQMNErKKtixrgma9s9n6QYYfGrpj0X9IEPVq8yXJ_xQr3YmrK2uug-vxTm3TxhTtpqyWUcp9lhxlRwzcqS0vkDnPjHp4OlzH0swrIEMPzmRh2Shrsp7oj6mJ35McqjGBiHsf9QE9sc2Eo-nAbtX9xOJGrutXdyXJhJZRVgn4wVoRdRUxMZ3qjo3lwRWl0"
)
_DEFAULT_AUTH = "Bearer " + _JWT
_DEFAULT_COOKIE = (
    "__stripe_mid=db6313c4-dbe1-49b1-9c3b-8e5782b57b408ffbb4; "
    "_ga=GA1.1.2027603213.1764613524; "
    "_ga_XGC3Z6JY04=GS2.1.s1777501465$o17$g1$t1777502455$j51$l0$h0; "
    "api_company=thecube; "
    "dash_waitroom=true; "
    "dashOnlineSession=7uhgnokesn27635ckc0er8gnpq; "
    "dashx_user=" + _JWT
)

BASE_URL = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/teams"
INCLUDE_PARAMS = "events.eventType,events.homeTeam,events.visitingTeam,events.resource.facility,events.resourceArea,events.comments,league.playoffEvents.eventType,league.playoffEvents.homeTeam,league.playoffEvents.visitingTeam,league.playoffEvents.resource.facility,league.playoffEvents.resourceArea,league.playoffEvents.comments,league.programType,product.locations,programType,season,skillLevel,ageRange,sport,registrations.finances,registrations.customer.makeUps,registrations.customer.address,finances,managers,teamMessages.customer,facility,invoiceItems.product,invoiceItems.childItems.product,purchaseOrders.product,purchaseOrders,events.rsvpStates,league.playoffEvents.rsvpStates,events.registrations,notes"


def load_dotenv_if_available() -> None:
    if load_dotenv is None:
        return
    env_path = PROJECT_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def _sync_dashx_user_cookie(cookie: str, bearer_header: str) -> str:
    """Align dashx_user in Cookie with Authorization JWT (Dash often requires both)."""
    jwt = bearer_header.removeprefix("Bearer ").strip()
    if not jwt or "dashx_user=" not in cookie:
        return cookie
    parts = []
    for segment in cookie.split("; "):
        if segment.startswith("dashx_user="):
            parts.append(f"dashx_user={jwt}")
        else:
            parts.append(segment)
    return "; ".join(parts)


def build_headers() -> dict:
    load_dotenv_if_available()
    auth = os.environ.get("DASH_AUTHORIZATION", "").strip() or _DEFAULT_AUTH
    cookie = os.environ.get("DASH_COOKIE", "").strip() or _DEFAULT_COOKIE
    bearer = auth if auth.startswith("Bearer ") else f"Bearer {auth}"
    if not os.environ.get("DASH_COOKIE"):
        cookie = _sync_dashx_user_cookie(cookie, bearer)
    if not os.environ.get("DASH_AUTHORIZATION"):
        print(
            "Note: DASH_AUTHORIZATION not set; using embedded token (often expired -> 401).\n"
            "      Paste a fresh Authorization header value from Dash into .env as DASH_AUTHORIZATION.\n"
        )
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "application/vnd.api+json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://apps.daysmartrecreation.com/dash/x/",
        "Authorization": bearer,
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie,
    }


def load_teams_config(path: Path) -> tuple[str, dict[int, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    season = raw.get("season")
    teams: dict[int, str] = {}
    for key, value in raw.items():
        if key == "season":
            continue
        if not isinstance(value, str):
            continue
        try:
            teams[int(key)] = value
        except ValueError as exc:
            raise ValueError(f"Invalid team id key in {path}: {key!r}") from exc
    if not teams:
        raise ValueError(f"No team entries found in {path}")
    if not season:
        season = "Unknown season"
    return season, teams


def fetch_team_roster(team_id: int, team_name: str, headers: dict, company: str):
    url = f"{BASE_URL}/{team_id}"
    params = {
        "cache[save]": "false",
        "filterRelations[notes.private]": "false",
        "include": INCLUDE_PARAMS,
        "company": company,
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching team {team_name}: {e}")
        return None


def _registration_team_id(reg_item: dict) -> int | None:
    """Resolve team resource id from a registrations included object."""
    rel = reg_item.get("relationships") or {}
    for key in ("team", "teams"):
        node = rel.get(key)
        if not isinstance(node, dict):
            continue
        ref = node.get("data")
        if isinstance(ref, dict) and ref.get("type") == "teams" and ref.get("id") is not None:
            try:
                return int(ref["id"])
            except (TypeError, ValueError):
                continue
        if isinstance(ref, list):
            for r in ref:
                if isinstance(r, dict) and r.get("type") == "teams" and r.get("id") is not None:
                    try:
                        return int(r["id"])
                    except (TypeError, ValueError):
                        continue
    attrs = reg_item.get("attributes") or {}
    for key in ("team_id", "teamId"):
        raw = attrs.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def _player_from_registration(reg_data: dict, included: list, team_name: str) -> dict | None:
    reg_id = reg_data.get("id")
    reg_attrs = reg_data.get("attributes", {})
    customer_ref = reg_data.get("relationships", {}).get("customer", {}).get("data", {})
    customer_id = customer_ref.get("id") if isinstance(customer_ref, dict) else None
    if not customer_id:
        return None
    customer_data = None
    for item2 in included:
        if item2.get("type") == "customers" and item2.get("id") == customer_id:
            customer_data = item2
            break
    if not customer_data:
        return None
    cust_attrs = customer_data.get("attributes", {})
    first_name = cust_attrs.get("first_name", "").strip()
    last_name = cust_attrs.get("last_name", "").strip()
    full_name = cust_attrs.get("full_name", f"{first_name} {last_name}").strip()
    jersey_number = reg_attrs.get("jersey_number") or cust_attrs.get("jersey_number")
    if jersey_number:
        jersey_number = str(jersey_number).strip()
    else:
        jersey_number = ""
    is_goalie = False
    cust_type = cust_attrs.get("cust_type", "").lower()
    position = reg_attrs.get("position", "").lower() or cust_attrs.get("position", "").lower()
    role = reg_attrs.get("role", "").lower() or cust_attrs.get("role", "").lower()
    if "goalie" in cust_type or "goalie" in position or "goalie" in role:
        is_goalie = True
    if reg_attrs.get("is_goalie") or cust_attrs.get("is_goalie"):
        is_goalie = True
    return {
        "customer_id": customer_id,
        "registration_id": reg_id,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "team_name": team_name,
        "jersey_number": jersey_number,
        "is_goalie": is_goalie,
        "email": cust_attrs.get("email", ""),
    }


def extract_roster_data(data, team_id, team_name, debug: bool = False):
    """
    Prefer team.relationships.registrations (what Dash shows for roster managers).
    If that list is empty, fall back to included registrations linked to this team_id
    (covers some JSON:API shapes). If both are empty, Dash is not returning roster rows
    for this session (often permission / role), which the script cannot override.
    """
    included = data.get("included", [])
    team_payload = data.get("data", {}) or {}
    registrations_refs = (
        team_payload.get("relationships", {}).get("registrations", {}).get("data", [])
    )
    if debug:
        rel_keys = sorted((team_payload.get("relationships") or {}).keys())
        type_counts: dict[str, int] = {}
        for item in included:
            t = item.get("type") or "?"
            type_counts[t] = type_counts.get(t, 0) + 1
        linked = sum(
            1
            for item in included
            if item.get("type") == "registrations" and _registration_team_id(item) == team_id
        )
        print(
            f"  [debug] team rel keys: {rel_keys}\n"
            f"  [debug] primary registration refs: {len(registrations_refs)}\n"
            f"  [debug] included registrations tied to team_id {team_id}: {linked}\n"
            f"  [debug] included type counts: {dict(sorted(type_counts.items()))}"
        )

    seen: set[str] = set()
    players: list[dict] = []

    def add_player(reg_data: dict) -> None:
        reg_id = reg_data.get("id")
        if not reg_id or reg_id in seen:
            return
        player = _player_from_registration(reg_data, included, team_name)
        if player:
            seen.add(reg_id)
            players.append(player)

    for reg_ref in registrations_refs:
        reg_id = reg_ref.get("id")
        for item in included:
            if item.get("type") == "registrations" and item.get("id") == reg_id:
                add_player(item)
                break

    if not players:
        for item in included:
            if item.get("type") != "registrations":
                continue
            if _registration_team_id(item) != team_id:
                continue
            add_player(item)

    return players


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch rosters from DaySmart Dash.")
    p.add_argument(
        "--preset",
        choices=("spring", "summer"),
        default="spring",
        help="spring -> Spring 2026 team file + default output; summer -> Summer 2026.",
    )
    p.add_argument("--teams-json", type=Path, help="Override team id JSON (see daysmart_roster_teams_*.json).")
    p.add_argument("--season", type=str, help="Override season label in output JSON.")
    p.add_argument("--output", type=Path, help="Output JSON path (default: project root).")
    p.add_argument("--company", default="thecube", help="DaySmart company code (default thecube).")
    p.add_argument(
        "--debug",
        action="store_true",
        help="Print API shape hints per team (registration ref counts, included types).",
    )
    return p.parse_args()


def resolve_paths(args: argparse.Namespace) -> tuple[Path, str, Path, dict[int, str]]:
    if args.teams_json:
        teams_path = args.teams_json
    elif args.preset == "summer":
        teams_path = SCRIPT_DIR / "daysmart_roster_teams_summer2026.json"
    else:
        teams_path = SCRIPT_DIR / "daysmart_roster_teams_spring2026.json"

    file_season, team_ids = load_teams_config(teams_path)
    season_label = args.season or file_season

    if args.output:
        out_path = args.output
    elif args.preset == "summer":
        out_path = PROJECT_ROOT / "players_summer2026_from_daysmart.json"
    else:
        out_path = PROJECT_ROOT / "players_spring2026_fresh.json"

    return teams_path, season_label, out_path, team_ids


def main() -> int:
    args = parse_args()
    teams_path, season_label, output_path, team_ids = resolve_paths(args)

    print(f"Teams config: {teams_path}")
    print(f"Season label: {season_label}")
    print(f"Output file:  {output_path}\n")

    headers = build_headers()
    print("Fetching rosters from DaySmart API...\n")

    all_players = []
    goalies_found = 0

    for team_id, team_name in sorted(team_ids.items()):
        print(f"Fetching {team_name} roster...")
        data = fetch_team_roster(team_id, team_name, headers, args.company)
        if not data:
            print(f"  [ERROR] Failed to fetch {team_name} data")
            continue
        players = extract_roster_data(data, team_id, team_name, debug=args.debug)
        print(f"  [OK] Found {len(players)} players")
        team_goalies = sum(1 for p in players if p.get("is_goalie"))
        if team_goalies > 0:
            goalies_found += team_goalies
            print(f"  [OK] Found {team_goalies} goalie(s)")
        all_players.extend(players)

    print()
    print("=" * 60)
    print("Fetch Summary")
    print("=" * 60)
    print(f"Total players: {len(all_players)}")
    print(f"Total goalies: {goalies_found}")
    print(f"Teams:         {len(team_ids)}")
    print()

    if not all_players:
        print(
            "[FAILED] No players fetched. Fix auth (DASH_AUTHORIZATION / DASH_COOKIE), "
            "team IDs in the JSON config, and retry."
        )
        return 1

    output_data = {
        "season": season_label,
        "lastUpdated": datetime.now().isoformat() + "Z",
        "players": all_players,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] Saved to: {output_path}\n")

    print("Sample players (first 3):")
    print("-" * 60)
    for i, player in enumerate(all_players[:3], 1):
        print(f"{i}. {player['full_name']}")
        print(f"   Team: {player['team_name']}")
        print(f"   Jersey: {player['jersey_number'] or 'None'}")
        print(f"   Customer ID: {player['customer_id']}")
        print(f"   Goalie: {'Yes' if player['is_goalie'] else 'No'}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
