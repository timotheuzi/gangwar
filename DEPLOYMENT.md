# PythonAnywhere Deployment Guide

This guide explains how to deploy the Gangwar Game to PythonAnywhere. This updated guide uses the source code deployment approach with proper SocketIO support for WebSockets.

## Prerequisites

- PythonAnywhere account (free tier works, but paid plans offer better performance)
- Git (for cloning/updating the repository)
- Basic familiarity with PythonAnywhere's interface

## Step 1: Prepare Your Code

1. **Clone or update your repository** locally:
   ```bash
   git clone https://github.com/timotheuzi/gangwar.git
   cd gangwar
   ```

2. **Test locally** (optional but recommended):
   ```bash
   pip install -r requirements.txt
   python test_deployment.py  # Run deployment configuration tests
   python pythonanywhere.py  # Start the server
   ```
   Visit `http://localhost:5009` to ensure everything works.

## Step 2: Create PythonAnywhere Web App

1. **Log in to PythonAnywhere** and go to the **Web** tab
2. **Click "Add a new web app"**
3. **Choose "Flask"** as the framework
4. **Select Python version**: Choose Python 3.10 or later (Python 3.13 recommended for best compatibility)
5. **Enter your app name** and click **Next**
6. **Set the PythonAnywhere path** to your desired URL path

## Step 3: Upload Source Files

1. **Navigate to your web app directory** using the **Files** tab:
   - Usually located at `/home/yourusername/yourappname`

2. **Upload the following files and directories**:
   - `pythonanywhere_entry.py` (WSGI entry point that handles imports)
   - `flask_app.py` (main WSGI file that PythonAnywhere will use)
   - `scripts/pythonanywhere.py` (alternative entry point for local development)
   - `src/` directory (contains `app.py`)
   - `templates/` directory
   - `static/` directory
   - `model/` directory (contains JSON config files)
   - `requirements.txt`

3. **Alternative: Use Git** (recommended for easier updates):
   ```bash
   git clone https://github.com/timotheuzi/gangwar.git .
   ```

## Step 4: Configure the Web App

1. **Go back to the Web tab** and click on your app
2. **Update the WSGI configuration**:
   - In the Web tab, look for the "WSGI configuration file" section
   - Change the path to: `/home/yourusername/yourappname/pythonanywhere_entry.py`
   - Replace `yourusername` and `yourappname` with your actual PythonAnywhere username and app name
   - Click the save button if there is one, or the configuration will auto-save

3. **Configure static files**:
   - Add a static files mapping:
     - **URL**: `/static/`
     - **Directory**: `/home/yourusername/yourappname/static/`

4. **Set up virtual environment** (optional but recommended):
   - In the Web tab, create a virtual environment
   - Update the Python path to use the virtual environment

## Step 5: Install Dependencies

1. **Open a Bash console** from the **Consoles** tab
2. **Navigate to your app directory**:
   ```bash
   cd yourappname
   ```

3. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

   **Note**: If using a virtual environment, activate it first:
   ```bash
   source venv/bin/activate  # or your virtual environment path
   pip install -r requirements.txt
   ```

## Step 6: Configure Environment Variables (Optional)

If your app uses environment variables, set them in the Web tab:
- Go to **Web** → **Environment variables**
- Add any required variables (e.g., `SECRET_KEY`, `DEBUG=false`)

## Step 7: Reload and Test

1. **Reload your web app** using the green **Reload** button in the Web tab
2. **Check the server logs**:
   - Click **Log files** in the Web tab
   - Look for any error messages in `error.log` or `server.log`

3. **Visit your app's URL** to test:
   - Your app should be available at `https://yourusername.pythonanywhere.com`
   - Test all major features including chat (WebSocket functionality)

## WebSocket/SocketIO Considerations

This deployment includes robust SocketIO support for real-time features:

- **Gevent**: Used for WebSocket handling in production WSGI environments (included in requirements.txt)
- **Async Mode**: SocketIO automatically uses `gevent` mode for production deployment and `threading` for development
- **WSGI Compatibility**: The `pythonanywhere.py` file properly handles SocketIO WSGI middleware for deployment
- **Error Handling**: Improved error handling ensures graceful fallback if SocketIO initialization fails
- **Free Tier Limitations**: PythonAnywhere's free tier may have WebSocket connection limits

### WebSocket Troubleshooting

If you encounter WebSocket connection issues (500 errors during handshake):

1. **Check Server Logs**: Look for SocketIO initialization messages in PythonAnywhere's error logs
2. **Verify Gevent Installation**: Ensure gevent is properly installed in your PythonAnywhere environment
3. **Test Locally First**: Run the deployment test locally to verify SocketIO works
4. **Check Browser Console**: Look for specific WebSocket error messages in browser developer tools

If WebSockets don't work on the free tier, consider upgrading to a paid plan for better real-time performance.

## File Permissions and Security

1. **Set proper permissions**:
   ```bash
   chmod 755 pythonanywhere_entry.py
   chmod 755 flask_app.py
   chmod -R 755 static/
   chmod -R 755 templates/
   ```

## Alternative WSGI Configuration (If Web Interface Won't Allow Changes)

**If you cannot change the WSGI configuration file through the Web tab**, PythonAnywhere may be using a default file path. Here's the alternative approach:

1. **Upload or create `flask_app.py` in your webapp directory**
2. **Edit the file content to match**:
   ```python
   from pythonanywhere_entry import application
   ```

3. **PythonAnywhere will automatically use this file** if it's present in your webapp directory and named `flask_app.py`

4. **Test the import** by reloading your webapp and checking the logs

2. **Database files**: If your app creates files (like high scores), ensure write permissions:
   ```bash
   touch high_scores.json
   chmod 666 high_scores.json
   ```

## Updating Your App

1. **Make changes locally** and test
2. **Push to GitHub** (if using Git)
3. **Pull updates on PythonAnywhere**:
   ```bash
   cd yourappname
   git pull origin main
   ```
4. **Reinstall dependencies** if requirements.txt changed:
   ```bash
   pip install -r requirements.txt
   ```
5. **Reload the web app** in the Web tab

## Performance Optimization

- **Free Tier**: Limited CPU and memory, occasional timeouts
- **Paid Plans**: Better performance, more concurrent connections
- **Caching**: Consider adding caching headers for static files
- **Database**: For better performance, consider using PythonAnywhere's MySQL instead of file-based storage

## Troubleshooting

### Common Issues:

1. **Import Errors / Module Not Found**:
   - Ensure all dependencies are installed
   - Check Python path in Web configuration
   - Verify virtual environment is activated

2. **Static Files Not Loading**:
   - Check static file mappings in Web tab
   - Ensure correct directory paths
   - Verify file permissions

3. **WebSocket Connection Issues**:
   - Check browser console for errors
   - Verify gevent is installed
   - Free tier may have connection limits

4. **Application Timeout**:
   - Increase timeout settings in Web tab
   - Optimize code for better performance
   - Consider upgrading to paid plan

5. **500 Internal Server Error**:
   - Check error logs in Web tab
   - Test locally first
   - Verify all required files are uploaded

### Debug Steps:

1. **Check logs**: Always check `error.log` and `server.log`
2. **Test locally**: Ensure app works on your machine first
3. **Console testing**: Use PythonAnywhere's Bash console to test imports:
   ```bash
   python -c "from src.app import app; print('Import successful')"
   ```

## Backup and Recovery

- **Regular backups**: PythonAnywhere automatically backs up your files
- **Manual backup**: Download important files regularly
- **Version control**: Use Git for change tracking

## Support Resources

- **PythonAnywhere Help**: Check their official documentation
- **Flask-SocketIO Docs**: For WebSocket-specific issues
- **Community Forums**: PythonAnywhere and Flask communities
- **Logs**: Always check server logs first for error details

## Security Best Practices

1. **Environment Variables**: Store sensitive data in environment variables
2. **File Permissions**: Set appropriate permissions on sensitive files
3. **HTTPS**: PythonAnywhere provides free SSL certificates
4. **Updates**: Keep dependencies updated for security patches

---

**Last Updated**: September 2025
**Tested With**: Python 3.13, Flask 2.3.3, Flask-SocketIO 5.3.6, Gevent 24.2.1
