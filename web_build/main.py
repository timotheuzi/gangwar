import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app from the src directory
from src.app import app

# Try to import socketio if available
socketio = None
try:
    from src.app import socketio
except ImportError:
    pass

# Export for WSGI
application = app

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 6009))

    if socketio:
        print("Starting with SocketIO support...")
        socketio.run(app, host='0.0.0.0', port=port, debug=True)
    else:
        print("Starting Flask app (SocketIO not available)...")
        app.run(host='0.0.0.0', port=port, debug=True)
