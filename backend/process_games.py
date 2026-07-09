"""
Manually process pending games to create game_summaries.

Usage:
    python backend/process_games.py
"""

import os
import sys
from dotenv import load_dotenv
from sync_service import process_pending_games

load_dotenv()

def main():
    print("=" * 60)
    print("Processing Pending Games")
    print("=" * 60)
    print()
    
    result = process_pending_games()
    
    print()
    print("=" * 60)
    print("Result:")
    print("=" * 60)
    print(f"Processed: {result.get('processed', 0)} games")
    print(f"Total pending: {result.get('total_pending', 0)} games")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    if result.get('message'):
        print(f"Message: {result['message']}")

if __name__ == '__main__':
    main()




