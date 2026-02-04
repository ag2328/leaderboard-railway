#!/usr/bin/env python3
"""
Fetch Spring 2026 schedule from DaySmart API and create schedule.json
"""

import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# Team IDs from the API response
TEAM_IDS = {
    5252: "Maple Leafs",
    5250: "Bruins",
    5253: "Red Wings",
    5251: "Canadiens"
}

BASE_URL = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/teams"
INCLUDE_PARAMS = "events.eventType,events.homeTeam,events.visitingTeam,events.resource.facility,events.resourceArea,events.comments,league.playoffEvents.eventType,league.playoffEvents.homeTeam,league.playoffEvents.visitingTeam,league.playoffEvents.resource.facility,league.playoffEvents.resourceArea,league.playoffEvents.comments,league.programType,product.locations,programType,season,skillLevel,ageRange,sport,registrations.finances,registrations.customer.makeUps,registrations.customer.address,finances,managers,teamMessages.customer,facility,invoiceItems.product,invoiceItems.childItems.product,purchaseOrders.product,purchaseOrders,events.rsvpStates,league.playoffEvents.rsvpStates,events.registrations,notes"

# Resource ID to rink name mapping
RINK_MAP = {
    1: "NHL",
    4: "OLY"
}

def fetch_team_data(team_id):
    """Fetch team data including events from API"""
    url = f"{BASE_URL}/{team_id}"
    params = {
        "cache[save]": "false",
        "filterRelations[notes.private]": "false",
        "include": INCLUDE_PARAMS,
        "company": "thecube"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "application/vnd.api+json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://apps.daysmartrecreation.com/dash/x/",
        "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVYYXVubUwifQ.eyJpYXQiOjE3Njc3Mzc1MzgsIm5iZiI6MTc2NzczNzUzOCwiZXhwIjoxNzY3OTEwMzM4LCJpc3MiOiIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSIsImF1ZCI6WyIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSJdLCJjb20iOiJ0aGVjdWJlIiwianRpIjoiMzA3NDk3OGY1ZDU2MDc4ZTM3ZjAyMTkxNTk3YTk3ZjEiLCJ0b2siOiIzMDc0OTc4ZjVkNTYwNzhlMzdmMDIxOTE1OTdhOTdmMSIsInV0eSI6ImN1c3RvbWVyIiwiZmlkIjoxLCJzdWIiOjU4NSwiZ3R5IjoiY2xpZW50X2NyZWRlbnRpYWxzIn0.Q2gYcXBEg00PAXrcY7CjlbUVJxCjlWzumZRR8O6ToDKm3R4OvRfLpUJpSL1Tss-pDYrNzRN01Az2Df5uuFraN8--_znUjnhhrn2rCgDAVTh-aMvAge2j2yAaBh2YMyqZ70yG4WGNDPXccytIZ1fxVxA1HXKHWkXYt8J7JFyXlLZGo2mxnICidOhfYzuUNRFsEuXDboAKYlaKzxaHPoZmIrcTFP7TAh_Xd9geT4vNEcWa7tWyAa_22I_EjO1-gnyK-OvIeP39ktjWLyKwUYpvrefy-GoRJuoeFmHhrOkRx2P_v_Tzp1tLjDvnyau6ecN3dx_4VrktVU_9_ww38WSh8JSsf1xc0zGgKLJw4GuVOTi_YcojLUEtOQgd7YZQIPmhyBmUf5Eu7O6K6A0hpZIppQBCUtWpNTWLbD4ESY-mfgh_8aJYHxb73VJHXN8aBmSIx9M_SHz4eIBXX5veOA4LkGmiNuMBbjAYO_kx9ZDhTK9rWa9IPpmnW7moQRr_2bfkesEPdXbOXD5fG679dWjJpbHfMmo1677a1KC1TTIUnu7cvzcWNb7XXsv_d3AQ7RYTDq06heFo65KKKACIfuW0Hx-fCZpKgUAe9iIJBtRUy0OLZU8StrWdcUIqJGJKfSsNrGKX3juphEhxvskBZ_VoZoK5-0L6DpZmWt0lx9_H7L4",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": "mysam_company=thecube; mysam_email=Andrewggaitan%40gmail.com; _ga_XGC3Z6JY04=GS2.1.s1767737536$o2$g1$t1767740460$j58$l0$h0; _ga=GA1.1.2027603213.1764613524; dash_quick_connect_thecube_585=%7B%22customer_name%22%3A%22Andrew%20Gaitan%22%2C%22company_name%22%3A%22The%20Cube%20Ice%20and%20Entertainment%20Center%22%2C%22token%22%3A%22a9ad9e5580dd85fb115126b2ca7a2633%22%2C%22customer_id%22%3A%22585%22%2C%22company_code%22%3A%22thecube%22%2C%22expiration%22%3A1769999137%7D; api_company=thecube; __stripe_mid=db6313c4-dbe1-49b1-9c3b-8e5782b57b408ffbb4; dashOnlineSession=a02v2r8hnptph4rafm16fnsvl9; __stripe_sid=54c628b8-5bcc-48ed-9169-d7a0dc7346843eab9f; dashx_user=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVYYXVubUwifQ.eyJpYXQiOjE3Njc3Mzc1MzgsIm5iZiI6MTc2NzczNzUzOCwiZXhwIjoxNzY3OTEwMzM4LCJpc3MiOiIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSIsImF1ZCI6WyIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSJdLCJjb20iOiJ0aGVjdWJlIiwianRpIjoiMzA3NDk3OGY1ZDU2MDc4ZTM3ZjAyMTkxNTk3YTk3ZjEiLCJ0b2siOiIzMDc0OTc4ZjVkNTYwNzhlMzdmMDIxOTE1OTdhOTdmMSIsInV0eSI6ImN1c3RvbWVyIiwiZmlkIjoxLCJzdWIiOjU4NSwiZ3R5IjoiY2xpZW50X2NyZWRlbnRpYWxzIn0.Q2gYcXBEg00PAXrcY7CjlbUVJxCjlWzumZRR8O6ToDKm3R4OvRfLpUJpSL1Tss-pDYrNzRN01Az2Df5uuFraN8--_znUjnhhrn2rCgDAVTh-aMvAge2j2yAaBh2YMyqZ70yG4WGNDPXccytIZ1fxVxA1HXKHWkXYt8J7JFyXlLZGo2mxnICidOhfYzuUNRFsEuXDboAKYlaKzxaHPoZmIrcTFP7TAh_Xd9geT4vNEcWa7tWyAa_22I_EjO1-gnyK-OvIeP39ktjWLyKwUYpvrefy-GoRJuoeFmHhrOkRx2P_v_Tzp1tLjDvnyau6ecN3dx_4VrktVU_9_ww38WSh8JSsf1xc0zGgKLJw4GuVOTi_YcojLUEtOQgd7YZQIPmhyBmUf5Eu7O6K6A0hpZIppQBCUtWpNTWLbD4ESY-mfgh_8aJYHxb73VJHXN8aBmSIx9M_SHz4eIBXX5veOA4LkGmiNuMBbjAYO_kx9ZDhTK9rWa9IPpmnW7moQRr_2bfkesEPdXbOXD5fG679dWjJpbHfMmo1677a1KC1TTIUnu7cvzcWNb7XXsv_d3AQ7RYTDq06heFo65KKKACIfuW0Hx-fCZpKgUAe9iIJBtRUy0OLZU8StrWdcUIqJGJKfSsNrGKX3juphEhxvskBZ_VoZoK5-0L6DpZmWt0lx9_H7L4"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        # Debug: check if we got data
        if "included" in json_data:
            print(f"  Response OK, {len(json_data.get('included', []))} items in included array")
        return json_data
    except Exception as e:
        print(f"Error fetching team {team_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response status: {e.response.status_code}")
        return None

def parse_event(event_data, included_data):
    """Parse an event from the API response"""
    attrs = event_data.get("attributes", {})
    
    # Get event type - only process "Game" events
    event_type_id = attrs.get("event_type_id")
    if event_type_id != "g":  # "g" = Game
        return None
    
    # Debug: check if we have required fields
    start_str = attrs.get("start")
    hteam_id = attrs.get("hteam_id")
    vteam_id = attrs.get("vteam_id")
    
    if not start_str or not hteam_id or not vteam_id:
        return None
    
    # Get start date/time
    start_str = attrs.get("start")
    if not start_str:
        return None
    
    # Parse datetime (handle timezone)
    try:
        if start_str.endswith("Z"):
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        else:
            start_dt = datetime.fromisoformat(start_str)
    except:
        return None
    
    # Skip Friday practices (1/9/2026 at 6:00pm)
    if start_dt.date() == datetime(2026, 1, 9).date() and start_dt.hour == 18:
        return None
    
    # Only include Sunday games
    if start_dt.weekday() != 6:  # 6 = Sunday
        return None
    
    # Get home and away team IDs
    hteam_id = attrs.get("hteam_id")
    vteam_id = attrs.get("vteam_id")
    
    if not hteam_id or not vteam_id:
        return None
    
    # Convert to int for comparison
    hteam_id = int(hteam_id)
    vteam_id = int(vteam_id)
    
    # Get team names from included data, fallback to TEAM_IDS mapping
    home_team_name = TEAM_IDS.get(hteam_id)
    away_team_name = TEAM_IDS.get(vteam_id)
    
    # Try to get from included data first (more reliable)
    teams_included = [item for item in included_data if item.get("type") == "teams"]
    
    for item in teams_included:
        item_id = int(item.get("id"))
        if item_id == hteam_id:
            home_team_name = item.get("attributes", {}).get("name")
        if item_id == vteam_id:
            away_team_name = item.get("attributes", {}).get("name")
    
    if not home_team_name or not away_team_name:
        return None
    
    # Get rink from resource_id
    resource_id = attrs.get("resource_id")
    rink = RINK_MAP.get(resource_id, None)
    
    return {
        "date": start_dt.date().isoformat(),
        "datetime": start_dt,
        "home_team": home_team_name,
        "away_team": away_team_name,
        "rink": rink,
        "hteam_id": hteam_id,
        "vteam_id": vteam_id
    }

def fetch_all_games():
    """Fetch all games from all teams"""
    all_games = {}
    
    for team_id, team_name in TEAM_IDS.items():
        print(f"Fetching data for {team_name} (ID: {team_id})...")
        data = fetch_team_data(team_id)
        
        if not data:
            continue
        
        # Get included data (events and teams are in included array)
        included = data.get("included", [])
        
        # Find all events in included array
        events = [item for item in included if item.get("type") == "events"]
        print(f"  Found {len(events)} events in included data")
        
        # Debug: print first event structure
        if events:
            first_event = events[0]
            print(f"  Sample event: type_id={first_event.get('attributes', {}).get('event_type_id')}, start={first_event.get('attributes', {}).get('start')}, hteam={first_event.get('attributes', {}).get('hteam_id')}, vteam={first_event.get('attributes', {}).get('vteam_id')}")
        
        # Parse each event
        parsed_count = 0
        for event in events:
            game = parse_event(event, included)
            if game:
                parsed_count += 1
        print(f"  Parsed {parsed_count} valid games")
        
        # Re-parse to collect games
        for event in events:
            game = parse_event(event, included)
            if game:
                # Create unique key (date + sorted team IDs)
                key = (game["date"], min(game["hteam_id"], game["vteam_id"]), max(game["hteam_id"], game["vteam_id"]))
                if key not in all_games:
                    all_games[key] = game
    
    return list(all_games.values())

def assign_weeks(games):
    """Assign week numbers starting from 1/11/2026 as week 1"""
    games_sorted = sorted(games, key=lambda x: x["datetime"])
    
    week1_date = datetime(2026, 1, 11).date()
    
    for game in games_sorted:
        days_diff = (game["datetime"].date() - week1_date).days
        game["week"] = (days_diff // 7) + 1
        # Remove datetime, keep just date string
        del game["datetime"]
        del game["hteam_id"]
        del game["vteam_id"]
    
    return games_sorted

def create_schedule_json(games):
    """Create the final schedule.json structure"""
    
    # Create team schedules for backwards compatibility
    team_schedules = defaultdict(list)
    for game in games:
        # Add to home team schedule
        team_schedules[game["home_team"]].append({
            "week": game["week"],
            "date": game["date"],
            "opponent": game["away_team"],
            "rink": game["rink"]
        })
        # Add to away team schedule
        team_schedules[game["away_team"]].append({
            "week": game["week"],
            "date": game["date"],
            "opponent": game["home_team"],
            "rink": game["rink"]
        })
    
    # Sort each team's schedule by week
    for team in team_schedules:
        team_schedules[team].sort(key=lambda x: x["week"])
    
    return {
        "season": "Spring 2026",
        "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "games": games,
        "teams": dict(team_schedules)
    }

def main():
    print("Fetching games from DaySmart API...")
    games = fetch_all_games()
    
    if not games:
        print("No games found!")
        return
    
    print(f"Found {len(games)} unique games")
    
    games = assign_weeks(games)
    schedule_json = create_schedule_json(games)
    
    # Write to file
    with open("schedule_spring2026.json", "w", encoding="utf-8") as f:
        json.dump(schedule_json, f, indent=4, ensure_ascii=False)
    
    print(f"\nCreated schedule_spring2026.json with {len(games)} games")
    print(f"Week 1 starts: {games[0]['date']} (Week {games[0]['week']})")
    print(f"Last game: {games[-1]['date']} (Week {games[-1]['week']})")

if __name__ == "__main__":
    main()

