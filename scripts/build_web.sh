#!/bin/bash

# Gangwar Game Web Build Script - Web Deployment Version
# This script prepares the application for web hosting (PythonAnywhere, Heroku, etc.)

echo "Building Gangwar Game for web deployment..."

# Check if we're in the scripts directory and cd to parent
if [ -d "../src" ] && [ -f "../requirements.txt" ]; then
    echo "Detected running from scripts/ directory, changing to project root..."
    cd ..
fi

# Ensure we're in the project root
if [ ! -f "src/app.py" ]; then
    echo "ERROR: Please run this script from the project root directory where src/app.py exists."
    exit 1
fi

# Function to clean up disk space
cleanup_disk_space() {
    echo "Attempting to free up disk space..."

    # Remove old build files
    echo "Removing old build files..."
    rm -rf web_build/ __pycache__/ */__pycache__/ 2>/dev/null || true

    # Clean Python cache
    echo "Cleaning Python cache files..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true

    # Clean pip cache
    echo "Cleaning pip cache..."
    pip cache purge 2>/dev/null || true

    echo "Cleanup completed."
}

# Check if requirements are installed
echo "Checking Python dependencies..."
python3 -c "import flask, flask_socketio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required dependencies..."
    python3 -m pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please install manually:"
        echo "python3 -m pip install -r requirements.txt"
        exit 1
    fi
fi

# Create web deployment directory
echo "Creating web deployment directory..."
rm -rf web_build
mkdir -p web_build

# Copy configuration files
cp requirements.txt web_build/ 2>/dev/null || true
cp pythonanywhere_entry.py web_build/ 2>/dev/null || true
cp wsgi.py web_build/ 2>/dev/null || true

# Create main.py that imports from the parent src structure
cat > web_build/main.py << 'EOF'
import os
import sys

# Add the parent directory to Python path to access src/model
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

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
EOF

# Create WSGI entry point
cat > web_build/wsgi.py << 'EOF'
import os
import sys

# Add parent directory to path to access src/model
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the Flask application
from main import application

# This is the WSGI application object
app = application
EOF

# Create startup script for web deployment
cat > web_build/run_web.sh << 'EOF'
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
EOF

chmod +x web_build/run_web.sh

# Create deployment README
cat > web_build/WEB_DEPLOYMENT_README.md << 'EOF'
# Gangwar Game - Web Deployment

This directory contains a web-deployable version of the Gangwar game.

## Files Structure:
- `main.py` - Main application entry point with SocketIO support
- `app.py` - Flask application (imported from src structure)
- `wsgi.py` - WSGI entry point for web servers
- `run_web.sh` - Startup script for local testing
- `src/` - Source code directory
- `model/` - Game data and configuration
- `static/` - CSS, JavaScript, and other static files
- `templates/` - HTML templates

## Deployment Instructions:

### PythonAnywhere:
1. Upload the entire project (including src/, model/, and this web_build/ directory) to your PythonAnywhere account
2. Set WSGI file to: `web_build/wsgi.py`
3. Install requirements: `pip install -r requirements.txt`
4. Set virtual environment path if needed

### Heroku:
1. Upload the entire project to your repository
2. Create a `Procfile` with: `web: python web_build/main.py`
3. Set buildpack to: `heroku/python`
4. Deploy via git

### Local Development:
```bash
./run_web.sh
```

### Manual Start:
```bash
python3 main.py
```

## Environment Variables:
- `PORT` - Server port (default: 6009)
- `FLASK_ENV` - Flask environment (development/production)

## Features:
- Real-time chat with SocketIO
- Turn-based combat system
- Dynamic weapon UI
- Web-based game interface
EOF

# Create simple test script
cat > web_build/test_web.py << 'EOF'
#!/usr/bin/env python3
"""
Simple test script to verify web deployment setup
"""

import os
import sys

# Add parent directory to path to access src/model
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_imports():
    """Test that all required modules can be imported"""
    try:
        import flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False

    try:
        import flask_socketio
        print("✓ Flask-SocketIO imported successfully")
    except ImportError as e:
        print(f"⚠ Flask-SocketIO import failed: {e}")
        print("  Chat functionality will be disabled")

    try:
        from src.app import app
        print("✓ Game application imported successfully")
    except ImportError as e:
        print(f"✗ Game application import failed: {e}")
        return False

    return True

def test_files():
    """Test that required files exist"""
    # Check files in parent directory (project root)
    parent_files = [
        '../src/app.py',
        '../model/npcs.json',
        '../src/templates/base.html',
        '../src/static/style.css'
    ]

    for file_path in parent_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            return False

    return True

def main():
    print("Testing Gangwar Web Deployment Setup...")
    print("=" * 50)

    imports_ok = test_imports()
    files_ok = test_files()

    print("=" * 50)
    if imports_ok and files_ok:
        print("✓ All tests passed! Ready for web deployment.")
        print("\nTo start the server:")
        print("  python3 main.py")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
EOF

chmod +x web_build/test_web.py

# Run tests
echo "Running deployment tests..."
if cd web_build && python3 test_web.py; then
    echo ""
    echo "✓ Web build preparation completed successfully!"
    echo ""
    echo "Files created in web_build/ directory:"
    ls -la web_build/

    echo ""
    echo "To test the web deployment:"
    echo "  cd web_build && python3 test_web.py"
    echo ""
    echo "To run the web application:"
    echo "  cd web_build && ./run_web.sh"
    echo "  or"
    echo "  cd web_build && python3 main.py"
    echo ""
    echo "For production deployment:"
    echo "  Upload web_build/ contents to your web host"
    echo "  Set WSGI file to: wsgi.py"
else
    echo "✗ Web build preparation failed!"
    exit 1
fi
