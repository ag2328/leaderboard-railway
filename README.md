# 🏆 Legends Hockey Leaderboard

A public-facing leaderboard application that displays team standings, game summaries, and player statistics for Legends Hockey leagues.

## Overview

This application reads game data from the shared Postgres database (used by Scorekeepr) and calculates/displays:
- Team standings (points, wins, losses, ties)
- Game summary cards
- Player statistics (goals, assists, penalties)
- Goalie statistics (saves, save percentage)

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript (modular structure)
- **Database**: Postgres (shared with Scorekeepr)
- **Deployment**: Railway

## Architecture

- **Read-only**: This app only reads from the database, never writes
- **Public-facing**: No authentication required
- **Season-based**: Supports multiple seasons (currently Spring 2026)
- **Sync modes**: Manual or automatic stats calculation

## Project Structure

```
leaderboard-app/
├── backend/
│   ├── app.py                 # Flask application
│   ├── models.py              # Database query functions
│   ├── stats_calculator.py    # Stats calculation logic
│   ├── sync_service.py        # Game sync and processing
│   ├── requirements.txt
│   └── migrations/
│       └── 001_leaderboard_schema.sql
├── frontend/
│   ├── index.html
│   ├── styles.css             # Dark theme matching ratings app
│   └── js/
│       ├── api-client.js      # API communication
│       ├── standings.js       # Standings display logic
│       ├── game-cards.js      # Game summary cards
│       ├── player-stats.js    # Player statistics
│       └── utils.js           # Utility functions
├── .env.example
└── README.md
```

## Setup

### Prerequisites

- Python 3.9+
- Postgres database (shared with Scorekeepr)
- Railway account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Leaderboard
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL
   ```

4. **Run database migrations**
   ```bash
   python backend/migrations/run_migrations.py
   ```

5. **Create Spring 2026 season**
   ```bash
   python backend/setup_season.py
   ```

6. **Start the Flask server**
   ```bash
   cd backend
   flask run
   # Or: python app.py
   ```

7. **Open the frontend**
   - Open `frontend/index.html` in a browser
   - Or serve via a local web server

## Environment Variables

```bash
DATABASE_URL=postgresql://...  # Same as Scorekeepr
CURRENT_SEASON=Spring 2026
AUTO_SYNC_ENABLED=false        # Start with manual sync
FLASK_ENV=development
```

## Deployment

### Railway

1. Create new Railway project
2. Connect to existing Postgres database (from Scorekeepr)
3. Set environment variables
4. Deploy backend service
5. Deploy frontend (static files)

## API Endpoints

### Public Endpoints

- `GET /api/standings?season=Spring+2026` - Get team standings
- `GET /api/teams/:teamId/games?season=Spring+2026` - Get team's games
- `GET /api/teams/:teamId/players?season=Spring+2026` - Get player stats
- `GET /api/teams/:teamId/goalie?season=Spring+2026` - Get goalie stats
- `GET /api/games/:gameId/summary` - Get game summary

### Admin Endpoints (Protected)

- `POST /api/admin/sync-games` - Manually trigger game processing
- `GET /api/admin/sync-status` - Check sync status
- `POST /api/admin/recalculate-stats` - Recalculate all stats

## Development Notes

- Stats are calculated and stored in aggregated tables for performance
- Manual sync mode: Process games, then manually trigger stats update
- Auto sync mode: Stats update automatically when games are processed
- Game summary cards show: scores, shots, outcome (regulation/OT/SO)

## License

Private project for Legends Hockey.


