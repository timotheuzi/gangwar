#!/usr/bin/env python3
"""
Wrapper script to run the Flask app with correct PYTHONPATH.
This ensures Flask and its dependencies can be found.
"""

import sys
import os

# Add both system and user site-packages to PYTHONPATH
sys.path.insert(0, '/usr/lib/python3.13/site-packages')
sys.path.insert(0, '/home/bim/.var/app/com.vscodium.codium/data/python/lib/python3.13/site-packages')

# Now import and run the app
from app import app, socketio

if __name__ == '__main__':
    if socketio:
        socketio.run(app, host='0.0.0.0', port=5005, debug=True)
    else:
        # Run without SocketIO for bundled applications
        app.run(host='0.0.0.0', port=5005, debug=True)
