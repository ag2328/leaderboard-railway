# Database Migrations Guide

## Running Migrations

The leaderboard app requires database tables to be created before it can run. You need to run migrations **before** deploying to Railway.

### Option 1: Run Locally (Recommended)

1. **Get your DATABASE_URL from Railway:**
   - Go to your Railway project
   - Click on the Postgres service
   - Copy the `DATABASE_URL` from the Variables tab

2. **Set the DATABASE_URL:**
   ```bash
   # Create a .env file in the backend/ directory
   cd backend
   echo "DATABASE_URL=postgresql://user:password@host:port/database" > .env
   ```

3. **Run the migration script:**
   ```bash
   cd ..  # Back to Leaderboard root
   python run_migrations_local.py
   ```

   This will:
   - Create all required tables (seasons, game_summaries, team_standings, etc.)
   - Create the Spring 2026 season record
   - Track applied migrations

### Option 2: Run via Railway CLI

If you have Railway CLI installed:

```bash
railway run python backend/migrations/run_migrations.py
railway run python backend/setup_season.py
```

### Option 3: Run via Railway One-Off Command

1. Go to your Railway project
2. Click on your service
3. Go to the "Deployments" tab
4. Click "New Deployment" → "One-Off Command"
5. Run:
   ```bash
   cd backend && python migrations/run_migrations.py
   ```
6. Then run:
   ```bash
   cd backend && python setup_season.py
   ```

## What Gets Created

The migration creates:
- `seasons` - Season records
- `game_summaries` - Per-game statistics
- `goalie_game_stats` - Per-game goalie statistics  
- `team_standings` - Aggregated team standings
- `player_season_stats` - Aggregated player statistics
- `goalie_season_stats` - Aggregated goalie statistics
- `schema_migrations` - Tracks which migrations have been applied

It also adds columns to existing tables:
- `games` table: `season_id`, `game_outcome`, `went_to_overtime`, `went_to_shootout`, `winner_team_id`, `leaderboard_processed_at`
- `events` table: `season_id`

## Verifying Migrations

After running migrations, you can verify by checking the database:

```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('seasons', 'game_summaries', 'team_standings');

-- Check if Spring 2026 season exists
SELECT * FROM seasons WHERE name = 'Spring 2026';
```

## Troubleshooting

**Error: "relation does not exist"**
- Migrations haven't been run yet
- Run `python run_migrations_local.py`

**Error: "DATABASE_URL not set"**
- Make sure you've set the DATABASE_URL in your `.env` file
- Or export it as an environment variable

**Error: "permission denied"**
- Make sure your database user has CREATE TABLE permissions
- Check that you're using the correct DATABASE_URL





