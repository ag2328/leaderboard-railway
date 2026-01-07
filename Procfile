web: cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --keep-alive 5 --worker-class sync --capture-output --enable-stdio-inheritance --log-level info app:app

