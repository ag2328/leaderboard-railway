"""
Reprocess a single game to recalculate stats.

Usage:
    python backend/reprocess_game.py <game_id>
    
Example:
    python backend/reprocess_game.py 103
"""

import os
import sys
from dotenv import load_dotenv
from sync_service import process_single_game

load_dotenv()

def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/reprocess_game.py <game_id>")
        print("Example: python backend/reprocess_game.py 103")
        sys.exit(1)
    
    try:
        game_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid game ID")
        sys.exit(1)
    
    print("=" * 60)
    print(f"Reprocessing Game {game_id}")
    print("=" * 60)
    print()
    
    result = process_single_game(game_id)
    
    print()
    print("=" * 60)
    print("Result:")
    print("=" * 60)
    
    if result.get('success'):
        print(f"✓ {result.get('message', 'Game processed successfully')}")
    elif result.get('error'):
        print(f"✗ Error: {result['error']}")
        sys.exit(1)
    else:
        print(f"⚠ Warning: {result.get('message', 'Unknown result')}")
    
    print()
    print("Game stats have been recalculated.")
    print("Check the leaderboard to see updated stats.")

if __name__ == '__main__':
    main()

