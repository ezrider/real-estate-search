#!/bin/bash
# Start script for Real Estate Tracker API

# Change to script directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default values
export API_HOST=${API_HOST:-0.0.0.0}
export API_PORT=${API_PORT:-8000}

echo "Starting Real Estate Tracker API..."
echo "Host: $API_HOST"
echo "Port: $API_PORT"
echo ""

# Check if running in development mode
if [ "$1" == "dev" ]; then
    echo "Running in DEVELOPMENT mode (with auto-reload)"
    uvicorn app.main:app --host $API_HOST --port $API_PORT --reload
else
    echo "Running in PRODUCTION mode"
    # Use multiple workers for production
    uvicorn app.main:app --host $API_HOST --port $API_PORT --workers 2
fi
