#!/usr/bin/env python3
"""
Run migrations locally using Railway DATABASE_URL.
This script will:
1. Run the database migrations
2. Set up the Spring 2026 season
"""

import os
import sys
import subprocess

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

# Also try root .env
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    print("Please set DATABASE_URL in your .env file or environment variables")
    print("\nYou can get the DATABASE_URL from Railway:")
    print("1. Go to your Railway project")
    print("2. Click on the Postgres service")
    print("3. Copy the DATABASE_URL from the Variables tab")
    print("\nOr set it as an environment variable:")
    print("  export DATABASE_URL='postgresql://...'")
    sys.exit(1)

print("=" * 60)
print("Running Leaderboard Migrations")
print("=" * 60)
print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else '***'}")
print()

# Run migrations
print("Step 1: Running database migrations...")
print()

migrations_script = os.path.join(os.path.dirname(__file__), 'backend', 'migrations', 'run_migrations.py')
result = subprocess.run([sys.executable, migrations_script], env=os.environ.copy())

if result.returncode != 0:
    print("\nMigration failed!")
    sys.exit(1)

print()
print("Step 2: Setting up Spring 2026 season...")
print()

# Run season setup
setup_script = os.path.join(os.path.dirname(__file__), 'backend', 'setup_season.py')
result = subprocess.run([sys.executable, setup_script], env=os.environ.copy())

if result.returncode != 0:
    print("\nSeason setup failed!")
    sys.exit(1)

print()
print("=" * 60)
print("Setup complete!")
print("=" * 60)
