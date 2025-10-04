import os
import sys

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import the Flask application
from main import application

# This is the WSGI application object
app = application
