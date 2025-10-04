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
1. Upload all files in this directory to your PythonAnywhere account
2. Set WSGI file to: `wsgi.py`
3. Install requirements: `pip install -r requirements.txt`
4. Set virtual environment path if needed

### Heroku:
1. Create a `Procfile` with: `web: python main.py`
2. Set buildpack to: `heroku/python`
3. Deploy via git

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
