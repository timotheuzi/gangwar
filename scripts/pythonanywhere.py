#!/usr/bin/env python3
"""
gangwar Game - PythonAnywhere Deployment Entry Point
This file serves as the main entry point for deploying on PythonAnywhere

For WSGI deployment, this imports the Flask application directly.
For standalone executable deployment, this can run the packaged executable.
"""

import os
import sys
import subprocess

# Check if we've got a packaged executable and prefer it
executable_names = ['gangwar', 'gangwar.exe']
executable_path = None

for exe_name in executable_names:
    if os.path.exists(exe_name):
        executable_path = exe_name
        break

if executable_path and __name__ == '__main__':
    # Run the standalone executable for local development
    print(f"Running standalone executable: {executable_path}")
    try:
        subprocess.run([executable_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Executable failed: {e}")
        sys.exit(1)
else:
    # Use Python application for WSGI or when no executable is found
    # Add src directory to Python path
    src_dir = os.path.join(os.path.dirname(__file__), 'src')
    sys.path.insert(0, src_dir)

    # Import the Flask application
    from app import app, socketio

    if __name__ == '__main__':
        # For local development/testing
        print("Starting Game server with Python...")
        socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 6009)), debug=False)

    # For PythonAnywhere WSGI
    # This will be used by PythonAnywhere's WSGI configuration
    application = app
