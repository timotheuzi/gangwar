#!/bin/bash

echo "Starting Gangwar Web Application..."
echo "=================================="

# Check if we're in a web deployment environment
if [ -n "$PYTHONHOME" ]; then
    echo "Detected web deployment environment"
fi

# Set default port if not specified
PORT=${PORT:-6009}

echo "Starting server on port $PORT..."

# Try to use socketio if available, fallback to regular Flask
python3 -c "import flask_socketio" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "SocketIO available - starting with chat support..."
    python3 main.py
else
    echo "SocketIO not available - starting Flask app only..."
    python3 app.py
fi
