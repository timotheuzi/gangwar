#!/usr/bin/env python3
"""
Gangwar Game - PythonAnywhere WSGI Entry Point
This is the main WSGI entry point for PythonAnywhere deployment
"""

import os
import sys
import subprocess

# Add src directory to Python path so we can import app
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

# Import the Flask application and socketio
try:
    from app import app, socketio
    print("Successfully imported Flask app and SocketIO")
    # For WSGI deployment - Flask app with SocketIO middleware (auto-applied)
    application = app

    # For local development (if someone runs this directly)
    if __name__ == '__main__':
        socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 6009)), debug=False, allow_unsafe_werkzeug=True)
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)