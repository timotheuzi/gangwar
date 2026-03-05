#!/bin/bash
# Gangwar Game Development Server
# Runs the Flask development server

set -e  # Exit on any error

echo "Starting Gangwar Game development server..."
echo "Flask app: src/app.py"
echo "Listening on: http://localhost:6009"

# Run the Flask development server
python3 -m flask run --host=0.0.0.0 --port=6009 --with-threads --reload --debugger