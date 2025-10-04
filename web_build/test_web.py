#!/usr/bin/env python3
"""
Simple test script to verify web deployment setup
"""

import os
import sys

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
    # Check files in current directory (web_build)
    current_files = [
        'src/app.py',
        'model/npcs.json',
        'src/templates/base.html',
        'src/static/style.css'
    ]

    for file_path in current_files:
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
