#!/usr/bin/env python3
"""
Local test script to verify the Flask app can start and connect to the database.
Run this before deploying to catch errors early.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")
    try:
        import flask
        print("[OK] Flask imported")
    except ImportError as e:
        print(f"[FAIL] Flask import failed: {e}")
        print("  Run: pip install -r backend/requirements.txt")
        return False
    
    try:
        from flask_cors import CORS
        print("[OK] flask-cors imported")
    except ImportError as e:
        print(f"[FAIL] flask-cors import failed: {e}")
        print("  Run: pip install -r backend/requirements.txt")
        return False
    
    try:
        import psycopg2
        print("[OK] psycopg2 imported")
    except ImportError as e:
        print(f"[FAIL] psycopg2 import failed: {e}")
        print("  Run: pip install -r backend/requirements.txt")
        return False
    
    try:
        from dotenv import load_dotenv
        print("[OK] python-dotenv imported")
    except ImportError as e:
        print(f"[FAIL] python-dotenv import failed: {e}")
        print("  Run: pip install -r backend/requirements.txt")
        return False
    
    return True

def test_app_import():
    """Test if the app module can be imported."""
    print("\nTesting app module import...")
    try:
        # Load environment variables first
        from dotenv import load_dotenv
        load_dotenv()
        
        # Try importing app
        import app
        print("[OK] app.py imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] app.py import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection."""
    print("\nTesting database connection...")
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[FAIL] DATABASE_URL not set in environment")
        print("  Create a .env file with DATABASE_URL=...")
        return False
    
    print(f"[OK] DATABASE_URL is set")
    
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"[OK] Database connection successful")
        print(f"  PostgreSQL version: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        return False

def test_app_startup():
    """Test if the Flask app can be created."""
    print("\nTesting Flask app creation...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import after loading env
        import app as flask_app
        
        # Check if app object exists
        if hasattr(flask_app, 'app'):
            print("[OK] Flask app object created")
            
            # Test a simple route
            with flask_app.app.test_client() as client:
                response = client.get('/api/health')
                if response.status_code == 200:
                    print("[OK] Health endpoint responds")
                    print(f"  Response: {response.get_json()}")
                else:
                    print(f"[FAIL] Health endpoint returned {response.status_code}")
                    return False
            
            return True
        else:
            print("[FAIL] Flask app object not found")
            return False
    except Exception as e:
        print(f"[FAIL] Flask app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Local Flask App Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Imports
    if not test_imports():
        all_passed = False
        print("\n[FAIL] Import tests failed. Install dependencies first.")
        sys.exit(1)
    
    # Test 2: App import
    if not test_app_import():
        all_passed = False
        print("\n[FAIL] App import failed. Check for syntax errors.")
        sys.exit(1)
    
    # Test 3: Database connection (optional - skip if DATABASE_URL not set)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        if not test_database_connection():
            all_passed = False
            print("\n⚠️  Database connection failed, but app may still work for testing")
    else:
        print("\n⚠️  DATABASE_URL not set - skipping database test")
        print("   Set DATABASE_URL in .env file to test database connection")
    
    # Test 4: App startup
    if not test_app_startup():
        all_passed = False
        print("\n❌ App startup failed.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed! App should work in production.")
    else:
        print("[FAIL] Some tests failed. Fix errors before deploying.")
    print("=" * 60)

