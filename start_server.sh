#!/bin/bash
# Script to start the server with Uvicorn (proper WebSocket support)

echo "Starting Binance Analytics Platform with Uvicorn..."
echo "=================================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Start Uvicorn server
echo ""
echo "Starting server on http://127.0.0.1:8000"
echo "Dashboard: http://127.0.0.1:8000"
echo "Admin: http://127.0.0.1:8000/admin"
echo ""
echo "Using Uvicorn for proper WebSocket support"
echo "=================================================="
echo ""

uvicorn binance_analytics.asgi:application --host 0.0.0.0 --port 8000

