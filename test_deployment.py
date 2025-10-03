#!/usr/bin/env python3
"""
Test script to verify deployment configuration
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        print("Testing Flask import...")
        from flask import Flask
        print("✓ Flask imported successfully")

        print("Testing Flask-SocketIO import...")
        from flask_socketio import SocketIO
        print("✓ Flask-SocketIO imported successfully")

        print("Testing gevent import...")
        try:
            import gevent
            print("✓ gevent imported successfully")
        except ImportError:
            print("⚠ gevent not available (expected in development, required for production)")

        print("Testing python-socketio import...")
        import socketio
        print("✓ python-socketio imported successfully")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_app_creation():
    """Test that the app can be created without errors"""
    try:
        print("Testing app creation...")
        from src.app import app, socketio
        print("✓ App created successfully")

        if socketio:
            print("✓ SocketIO is enabled")
            print(f"  Async mode: {socketio.async_mode}")
        else:
            print("⚠ SocketIO is disabled")

        return True
    except Exception as e:
        print(f"✗ App creation error: {e}")
        return False

def test_wsgi_app():
    """Test that the WSGI app can be created"""
    try:
        print("Testing WSGI app creation...")
        from pythonanywhere import application
        print("✓ WSGI application created successfully")
        print(f"  Application type: {type(application)}")
        return True
    except Exception as e:
        print(f"✗ WSGI app creation error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Gangwar Deployment Test ===\n")

    tests = [
        ("Module Imports", test_imports),
        ("App Creation", test_app_creation),
        ("WSGI Application", test_wsgi_app),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            passed += 1
            print(f"✓ {test_name} passed\n")
        else:
            print(f"✗ {test_name} failed\n")

    print(f"=== Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("🎉 All tests passed! Deployment configuration looks good.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
