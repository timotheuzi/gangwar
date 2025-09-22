#!/usr/bin/env python3
"""
gangwar Game - PythonAnywhere Deployment Entry Point
This file serves as the main entry point for deploying on PythonAnywhere
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from src.app import app, socketio

if __name__ == '__main__':
    # For local development/testing
    print("Starting Game server...")
    if socketio:
        socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 6006)), debug=False)
    else:
        print("Warning: SocketIO not available, running Flask app only")
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 6006)), debug=False)

# For PythonAnywhere WSGI
# This will be used by PythonAnywhere's WSGI configuration
# Use socketio middleware if socketio is enabled, otherwise use app
if socketio:
    print("Using SocketIO middleware for WSGI deployment")
    application = socketio.sockio_mw
else:
    print("Warning: SocketIO not available, using Flask app only")
    print("WebSocket functionality will not work - check gevent installation")
    application = app
