"""
Migration runner for leaderboard database schema.

Applies migrations in order and tracks applied migrations.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)


def get_migration_files():
    """Get all migration files in order."""
    migrations_dir = os.path.dirname(__file__)
    migration_files = []
    
    for filename in sorted(os.listdir(migrations_dir)):
        if filename.endswith('.sql') and filename.startswith('0'):
            migration_files.append(os.path.join(migrations_dir, filename))
    
    return migration_files


def run_migration(conn, migration_file):
    """Run a single migration file."""
    print(f"Running migration: {os.path.basename(migration_file)}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        print(f"✓ Migration applied successfully")
        return True
    except Exception as e:
        print(f"✗ Error applying migration: {e}")
        conn.rollback()
        return False


def record_migration(conn, migration_file):
    """Record that a migration has been applied."""
    # Create schema_migrations table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    
    # Record this migration
    filename = os.path.basename(migration_file)
    cursor.execute("""
        INSERT INTO schema_migrations (filename)
        VALUES (%s)
        ON CONFLICT (filename) DO NOTHING
    """, (filename,))
    conn.commit()
    cursor.close()


def get_applied_migrations(conn):
    """Get list of already applied migrations."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    
    cursor.execute("SELECT filename FROM schema_migrations ORDER BY filename")
    applied = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return applied


def main():
    """Main migration runner."""
    print("=" * 60)
    print("Leaderboard Database Migrations")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print("✓ Connected to database")
        print()
        
        # Get migration files
        migration_files = get_migration_files()
        if not migration_files:
            print("No migration files found")
            return
        
        # Get already applied migrations
        applied = get_applied_migrations(conn)
        
        # Run migrations
        for migration_file in migration_files:
            filename = os.path.basename(migration_file)
            
            if filename in applied:
                print(f"⊘ Skipping {filename} (already applied)")
                continue
            
            if run_migration(conn, migration_file):
                record_migration(conn, migration_file)
            else:
                print("Migration failed. Stopping.")
                sys.exit(1)
            print()
        
        print("=" * 60)
        print("All migrations completed successfully!")
        print("=" * 60)
        
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

