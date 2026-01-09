#!/usr/bin/env python3
"""
Fetch Spring 2026 rosters from DaySmart API and save to JSON file.

Outputs a cleaned JSON file with:
- customer_id
- first_name, last_name, full_name
- team_name (mapped from team_id)
- jersey_number
- is_goalie (determined from registration attributes if available)
"""

import json
import os
import requests
from datetime import datetime

# Team IDs from the API
TEAM_IDS = {
    5252: "Maple Leafs",
    5250: "Bruins",
    5253: "Red Wings",
    5251: "Canadiens"
}

BASE_URL = "https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/teams"
INCLUDE_PARAMS = "events.eventType,events.homeTeam,events.visitingTeam,events.resource.facility,events.resourceArea,events.comments,league.playoffEvents.eventType,league.playoffEvents.homeTeam,league.playoffEvents.visitingTeam,league.playoffEvents.resource.facility,league.playoffEvents.resourceArea,league.playoffEvents.comments,league.programType,product.locations,programType,season,skillLevel,ageRange,sport,registrations.finances,registrations.customer.makeUps,registrations.customer.address,finances,managers,teamMessages.customer,facility,invoiceItems.product,invoiceItems.childItems.product,purchaseOrders.product,purchaseOrders,events.rsvpStates,league.playoffEvents.rsvpStates,events.registrations,notes"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Accept": "application/vnd.api+json",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://apps.daysmartrecreation.com/dash/x/",
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVYYXVubUwifQ.eyJpYXQiOjE3Njc3Mzc1MzgsIm5iZiI6MTc2NzczNzUzOCwiZXhwIjoxNzY3OTEwMzM4LCJpc3MiOiIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSIsImF1ZCI6WyIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSJdLCJjb20iOiJ0aGVjdWJlIiwianRpIjoiMzA3NDk3OGY1ZDU2MDc4ZTM3ZjAyMTkxNTk3YTk3ZjEiLCJ0b2siOiIzMDc0OTc4ZjVkNTYwNzhlMzdmMDIxOTE1OTdhOTdmMSIsInV0eSI6ImN1c3RvbWVyIiwiZmlkIjoxLCJzdWIiOjU4NSwiZ3R5IjoiY2xpZW50X2NyZWRlbnRpYWxzIn0.Q2gYcXBEg00PAXrcY7CjlbUVJxCjlWzumZRR8O6ToDKm3R4OvRfLpUJpSL1Tss-pDYrNzRN01Az2Df5uuFraN8--_znUjnhhrn2rCgDAVTh-aMvAge2j2yAaBh2YMyqZ70yG4WGNDPXccytIZ1fxVxA1HXKHWkXYt8J7JFyXlLZGo2mxnICidOhfYzuUNRFsEuXDboAKYlaKzxaHPoZmIrcTFP7TAh_Xd9geT4vNEcWa7tWyAa_22I_EjO1-gnyK-OvIeP39ktjWLyKwUYpvrefy-GoRJuoeFmHhrOkRx2P_v_Tzp1tLjDvnyau6ecN3dx_4VrktVU_9_ww38WSh8JSsf1xc0zGgKLJw4GuVOTi_YcojLUEtOQgd7YZQIPmhyBmUf5Eu7O6K6A0hpZIppQBCUtWpNTWLbD4ESY-mfgh_8aJYHxb73VJHXN8aBmSIx9M_SHz4eIBXX5veOA4LkGmiNuMBbjAYO_kx9ZDhTK9rWa9IPpmnW7moQRr_2bfkesEPdXbOXD5fG679dWjJpbHfMmo1677a1KC1TTIUnu7cvzcWNb7XXsv_d3AQ7RYTDq06heFo65KKKACIfuW0Hx-fCZpKgUAe9iIJBtRUy0OLZU8StrWdcUIqJGJKfSsNrGKX3juphEhxvskBZ_VoZoK5-0L6DpZmWt0lx9_H7L4",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": "mysam_company=thecube; mysam_email=Andrewggaitan%40gmail.com; _ga_XGC3Z6JY04=GS2.1.s1767737536$o2$g1$t1767740460$j58$l0$h0; _ga=GA1.1.2027603213.1764613524; dash_quick_connect_thecube_585=%7B%22customer_name%22%3A%22Andrew%20Gaitan%22%2C%22company_name%22%3A%22The%20Cube%20Ice%20and%20Entertainment%20Center%22%2C%22token%22%3A%22a9ad9e5580dd85fb115126b2ca7a2633%22%2C%22customer_id%22%3A%22585%22%2C%22company_code%22%3A%22thecube%22%2C%22expiration%22%3A1769999137%7D; api_company=thecube; __stripe_mid=db6313c4-dbe1-49b1-9c3b-8e5782b57b408ffbb4; dashOnlineSession=a02v2r8hnptph4rafm16fnsvl9; __stripe_sid=54c628b8-5bcc-48ed-9169-d7a0dc7346843eab9f; dashx_user=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVYYXVubUwifQ.eyJpYXQiOjE3Njc3Mzc1MzgsIm5iZiI6MTc2NzczNzUzOCwiZXhwIjoxNzY3OTEwMzM4LCJpc3MiOiIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSIsImF1ZCI6WyIuZGF5c21hcnRyZWNyZWF0aW9uLmNvbSJdLCJjb20iOiJ0aGVjdWJlIiwianRpIjoiMzA3NDk3OGY1ZDU2MDc4ZTM3ZjAyMTkxNTk3YTk3ZjEiLCJ0b2siOiIzMDc0OTc4ZjVkNTYwNzhlMzdmMDIxOTE1OTdhOTdmMSIsInV0eSI6ImN1c3RvbWVyIiwiZmlkIjoxLCJzdWIiOjU4NSwiZ3R5IjoiY2xpZW50X2NyZWRlbnRpYWxzIn0.Q2gYcXBEg00PAXrcY7CjlbUVJxCjlWzumZRR8O6ToDKm3R4OvRfLpUJpSL1Tss-pDYrNzRN01Az2Df5uuFraN8--_znUjnhhrn2rCgDAVTh-aMvAge2j2yAaBh2YMyqZ70yG4WGNDPXccytIZ1fxVxA1HXKHWkXYt8J7JFyXlLZGo2mxnICidOhfYzuUNRFsEuXDboAKYlaKzxaHPoZmIrcTFP7TAh_Xd9geT4vNEcWa7tWyAa_22I_EjO1-gnyK-OvIeP39ktjWLyKwUYpvrefy-GoRJuoeFmHhrOkRx2P_v_Tzp1tLjDvnyau6ecN3dx_4VrktVU_9_ww38WSh8JSsf1xc0zGgKLJw4GuVOTi_YcojLUEtOQgd7YZQIPmhyBmUf5Eu7O6K6A0hpZIppQBCUtWpNTWLbD4ESY-mfgh_8aJYHxb73VJHXN8aBmSIx9M_SHz4eIBXX5veOA4LkGmiNuMBbjAYO_kx9ZDhTK9rWa9IPpmnW7moQRr_2bfkesEPdXbOXD5fG679dWjJpbHfMmo1677a1KC1TTIUnu7cvzcWNb7XXsv_d3AQ7RYTDq06heFo65KKKACIfuW0Hx-fCZpKgUAe9iIJBtRUy0OLZU8StrWdcUIqJGJKfSsNrGKX3juphEhxvskBZ_VoZoK5-0L6DpZmWt0lx9_H7L4"
}

def fetch_team_roster(team_id, team_name):
    """Fetch team roster data from API"""
    url = f"{BASE_URL}/{team_id}"
    params = {
        "cache[save]": "false",
        "filterRelations[notes.private]": "false",
        "include": INCLUDE_PARAMS,
        "company": "thecube"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching team {team_name}: {e}")
        return None

def extract_roster_data(data, team_id, team_name):
    """Extract roster information from API response"""
    included = data.get("included", [])
    
    # Get registrations from relationships
    registrations_refs = data.get("data", {}).get("relationships", {}).get("registrations", {}).get("data", [])
    
    # Find actual registration and customer data in included array
    players = []
    for reg_ref in registrations_refs:
        reg_id = reg_ref.get("id")
        # Find registration in included
        for item in included:
            if item.get("type") == "registrations" and item.get("id") == reg_id:
                reg_data = item
                reg_attrs = reg_data.get("attributes", {})
                
                # Get customer relationship
                customer_ref = reg_data.get("relationships", {}).get("customer", {}).get("data", {})
                customer_id = customer_ref.get("id")
                
                # Find customer in included
                customer_data = None
                for item2 in included:
                    if item2.get("type") == "customers" and item2.get("id") == customer_id:
                        customer_data = item2
                        break
                
                if customer_data:
                    cust_attrs = customer_data.get("attributes", {})
                    
                    # Build player record
                    first_name = cust_attrs.get("first_name", "").strip()
                    last_name = cust_attrs.get("last_name", "").strip()
                    full_name = cust_attrs.get("full_name", f"{first_name} {last_name}").strip()
                    
                    # Get jersey number (could be in registration or customer attributes)
                    jersey_number = reg_attrs.get("jersey_number") or cust_attrs.get("jersey_number")
                    if jersey_number:
                        jersey_number = str(jersey_number).strip()
                    else:
                        jersey_number = ""
                    
                    # Determine if goalie (check various possible fields)
                    # Common indicators: cust_type, position, role, or specific attribute
                    is_goalie = False
                    cust_type = cust_attrs.get("cust_type", "").lower()
                    position = reg_attrs.get("position", "").lower() or cust_attrs.get("position", "").lower()
                    role = reg_attrs.get("role", "").lower() or cust_attrs.get("role", "").lower()
                    
                    if "goalie" in cust_type or "goalie" in position or "goalie" in role:
                        is_goalie = True
                    # Also check if jersey_number matches known goalie patterns (e.g., 1, 30, 31, etc.)
                    # or if there's a specific goalie flag
                    if reg_attrs.get("is_goalie") or cust_attrs.get("is_goalie"):
                        is_goalie = True
                    
                    player = {
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
                    players.append(player)
                break
    
    return players

def main():
    print("Fetching rosters from DaySmart API...\n")
    
    all_players = []
    goalies_found = 0
    
    # Fetch all teams
    for team_id, team_name in TEAM_IDS.items():
        print(f"Fetching {team_name} roster...")
        data = fetch_team_roster(team_id, team_name)
        
        if not data:
            print(f"  [ERROR] Failed to fetch {team_name} data")
            continue
        
        # Extract roster
        players = extract_roster_data(data, team_id, team_name)
        print(f"  [OK] Found {len(players)} players")
        
        # Count goalies
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
    print(f"Teams: {len(TEAM_IDS)}")
    print()
    
    # Build output JSON
    output_data = {
        "season": "Spring 2026",
        "lastUpdated": datetime.now().isoformat() + "Z",
        "players": all_players
    }
    
    # Save to file
    output_file = "players_spring2026_fresh.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"[SUCCESS] Saved to: {output_file}")
    print()
    
    # Show sample of first few players
    print("Sample players (first 3):")
    print("-" * 60)
    for i, player in enumerate(all_players[:3], 1):
        print(f"{i}. {player['full_name']}")
        print(f"   Team: {player['team_name']}")
        print(f"   Jersey: {player['jersey_number'] or 'None'}")
        print(f"   Customer ID: {player['customer_id']}")
        print(f"   Goalie: {'Yes' if player['is_goalie'] else 'No'}")
        print()

if __name__ == "__main__":
    main()

