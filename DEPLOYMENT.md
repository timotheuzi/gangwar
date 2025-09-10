# PythonAnywhere Deployment Guide

This guide explains how to deploy the Pimpin Game to PythonAnywhere using the Docker-based build process to avoid GLIBC compatibility issues.

## Prerequisites

- PythonAnywhere account (free tier works)
- Docker installed on your local machine
- Git (for cloning/updating the repository)

## Step 1: Build the Application Locally

1. Clone or update your repository:
   ```bash
   git clone https://github.com/timotheuzi/pimpin.git
   cd pimpin
   ```

2. Build the application using Docker:
   ```bash
   ./build.sh
   ```

   This will create a standalone executable in the `dist/` directory that's compatible with PythonAnywhere's older Linux environment.

## Step 2: Upload Files to PythonAnywhere

1. **Create a new web app** on PythonAnywhere:
   - Go to the Web tab
   - Click "Add a new web app"
   - Choose "Manual configuration" (or "Flask" if available)
   - Select Python 3.9 or 3.8 (avoid 3.10+ if possible)

2. **Upload the built files**:
   - Use the Files tab to navigate to your web app directory (usually `/home/yourusername/yourappname`)
   - Upload all files from your local `dist/` directory
   - Also upload:
     - `templates/` directory
     - `static/` directory
     - `npcs.json`
     - `requirements.txt`

## Step 3: Configure PythonAnywhere

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up the WSGI file**:
   - In your web app configuration, set the WSGI file to point to `pythonanywhere.py`
   - Make sure `pythonanywhere.py` is executable: `chmod +x pythonanywhere.py`

3. **Configure static files** (optional but recommended):
   - In the Web tab, add a static files mapping:
     - URL: `/static/`
     - Directory: `/home/yourusername/yourappname/static/`

## Step 4: Reload and Test

1. **Reload your web app** in the PythonAnywhere Web tab
2. **Check the server logs** for any errors
3. **Visit your app's URL** to test the deployment

## Troubleshooting GLIBC Issues

If you still encounter GLIBC errors:

1. **Ensure you're using the Docker build** - this builds on Ubuntu 20.04 which has compatible GLIBC versions
2. **Check PythonAnywhere's Python version** - use Python 3.8 or 3.9, avoid 3.10+
3. **Verify the executable** - make sure the `pimpin` executable in `dist/` is built correctly
4. **Alternative approach**: If the standalone executable still fails, you can:
   - Use the source code directly: set WSGI to import from `app.py`
   - Install dependencies and run as a regular Python app

## Alternative: Source Code Deployment

If the standalone executable continues to have issues:

1. Upload the source files instead of the `dist/` directory
2. Set your WSGI file to:
   ```python
   from app import app as application
   ```
3. Make sure all dependencies are installed
4. This approach avoids PyInstaller compatibility issues entirely

## Performance Considerations

- PythonAnywhere free tier has limitations on CPU and memory
- For better performance, consider upgrading to a paid plan
- Monitor your app's resource usage in the Account tab

## Updating Your App

1. Make changes locally
2. Rebuild with `./build.sh`
3. Upload updated files to PythonAnywhere
4. Reload the web app

## Common Issues

- **Module not found**: Make sure all requirements are installed
- **Static files not loading**: Check static file mappings
- **WebSocket issues**: PythonAnywhere may have limitations with WebSockets on free tier
- **Timeout errors**: Increase timeout settings in Web tab if needed

## Support

If you encounter issues:
1. Check PythonAnywhere's help pages
2. Review server logs in the Web tab
3. Ensure your local build completed successfully
4. Test locally before deploying
