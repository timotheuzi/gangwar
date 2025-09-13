#!/usr/bin/env python3
"""
WSGI application file for PythonAnywhere deployment.
This file serves as the entry point for the WSGI server.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask application
from app import app as application

# For debugging (optional - remove in production)
if __name__ == '__main__':
    application.run()
