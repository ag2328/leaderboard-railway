# Local Testing Guide

Before deploying to Railway, test the app locally to catch errors early.

## Quick Test

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   - Copy your `DATABASE_URL` from Railway (or use Scorekeepr's local .env)
   - Create a `.env` file in the `backend/` directory:
     ```
     DATABASE_URL=postgresql://user:password@host:port/database
     CURRENT_SEASON=Spring 2026
     AUTO_SYNC_ENABLED=false
     FLASK_ENV=development
     ```

3. **Run the test script:**
   ```bash
   cd ..  # Back to Leaderboard root
   python test_local.py
   ```

4. **If tests pass, try running the app:**
   ```bash
   cd backend
   python app.py
   ```
   
   Then test: http://localhost:5000/api/health

## What the Test Script Checks

- ✅ All Python dependencies are installed
- ✅ App module can be imported without errors
- ✅ Database connection works (if DATABASE_URL is set)
- ✅ Flask app can start and respond to requests

## Common Issues

- **ModuleNotFoundError**: Run `pip install -r backend/requirements.txt`
- **DATABASE_URL not set**: Create `.env` file in `backend/` directory
- **Database connection failed**: Check your DATABASE_URL is correct






