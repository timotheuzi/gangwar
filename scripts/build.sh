#!/bin/bash

# Gangwar Game Build Script - Cross-Platform Build Version
# This script builds the application locally using PyInstaller with cross-platform compatibility

echo "Building Gangwar Game for cross-platform deployment..."

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

    # Remove old build files (but preserve gangwar.spec)
    echo "Removing old build files..."
    rm -rf build/ dist/ 2>/dev/null || true
    # Remove other spec files but keep gangwar.spec
    find . -maxdepth 1 -name "*.spec" ! -name "gangwar.spec" -delete 2>/dev/null || true

    # Clean Python cache
    echo "Cleaning Python cache files..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true

    # Clean pip cache
    echo "Cleaning pip cache..."
    pip cache purge 2>/dev/null || true

    # Clean system temp files
    echo "Cleaning temporary files..."
    rm -rf /tmp/* 2>/dev/null || true

    echo "Cleanup completed."
}

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    python3 -m pip install --break-system-packages pyinstaller
fi

# Delete and recreate dist directory
echo "Deleting and recreating dist/ directory..."
rm -rf dist
mkdir -p dist
chmod -R u+rwx dist 2>/dev/null || true

# Create run.sh script in dist
cat > dist/run.sh << 'EOF'
#!/bin/bash

# Cross-platform run script for the Gangwar executable
# This script works on Linux, macOS, and can be adapted for Windows

# Function to detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*|MINGW*|MSYS*) echo "windows";;
        *)          echo "unknown";;
    esac
}

# Function to check if a process is running
is_process_running() {
    local pid=$1
    if [ "$(detect_os)" = "windows" ]; then
        # Windows check
        tasklist /FI "PID eq $pid" 2>NUL | grep -q "$pid" && return 0 || return 1
    else
        # Unix-like systems
        kill -0 "$pid" 2>/dev/null
    fi
}

# Function to kill process
kill_process() {
    local pid=$1
    if [ "$(detect_os)" = "windows" ]; then
        taskkill /PID "$pid" /F 2>NUL
    else
        kill "$pid" 2>/dev/null
    fi
}

# Function to find Python executable
find_python() {
    # Try different Python executables
    for python_cmd in python3 python python3.9 python3.8 python3.7; do
        if command -v "$python_cmd" >/dev/null 2>&1; then
            echo "$python_cmd"
            return 0
        fi
    done
    echo "python3"  # fallback
    return 1
}

echo "Gangwar Game Launcher"
echo "======================"
echo "OS Detected: $(detect_os)"
echo ""

# Kill any existing instances of gangwar
echo "Checking for existing gangwar instances..."
if pgrep -f gangwar >/dev/null 2>&1; then
    echo "Killing existing gangwar instances..."
    pkill -f gangwar
    sleep 2  # Wait for processes to terminate
fi

# Determine executable name based on OS
OS_TYPE=$(detect_os)
EXECUTABLE_NAME=""

if [ "$OS_TYPE" = "windows" ]; then
    if [ -f "gangwar.exe" ]; then
        EXECUTABLE_NAME="gangwar.exe"
    elif [ -f "gangwar" ]; then
        EXECUTABLE_NAME="gangwar"
    fi
else
    if [ -f "gangwar" ]; then
        EXECUTABLE_NAME="gangwar"
    elif [ -f "gangwar.exe" ]; then
        EXECUTABLE_NAME="gangwar.exe"
    fi
fi

# Try to run the executable
if [ -n "$EXECUTABLE_NAME" ]; then
    echo "Found executable: $EXECUTABLE_NAME"
    echo "Running Gangwar executable..."

    # Make sure it's executable
    chmod +x "$EXECUTABLE_NAME" 2>/dev/null || true

    # Run the executable
    ./"$EXECUTABLE_NAME" &
    EXECUTABLE_PID=$!

    # Wait a bit to see if it starts
    sleep 5

    if is_process_running "$EXECUTABLE_PID"; then
        echo "Gangwar executable started successfully (PID: $EXECUTABLE_PID)"
        echo "Press Ctrl+C to stop the application"
        wait "$EXECUTABLE_PID"
        exit 0
    else
        echo "Gangwar executable failed to start or crashed."
        kill_process "$EXECUTABLE_PID" 2>/dev/null || true
    fi
else
    echo "No executable found in current directory."
fi

# Fallback to Python
echo "Falling back to Python..."
PYTHON_CMD=$(find_python)
echo "Using Python: $PYTHON_CMD"

# Check if we're in the dist directory and need to go up
if [ -f "../src/app.py" ]; then
    echo "Changing to parent directory..."
    cd ..
fi

# Check if app.py exists
if [ ! -f "src/app.py" ]; then
    echo "Error: src/app.py not found!"
    echo "Please ensure you're running this from the correct directory."
    exit 1
fi

# Check if requirements are installed
echo "Checking Python dependencies..."
if ! "$PYTHON_CMD" -c "import flask, flask_socketio" 2>/dev/null; then
    echo "Installing required dependencies..."
    "$PYTHON_CMD" -m pip install -r requirements.txt --quiet || {
        echo "Failed to install dependencies. Please install manually:"
        echo "$PYTHON_CMD -m pip install -r requirements.txt"
        exit 1
    }
fi

echo "Starting Gangwar with Python..."
"$PYTHON_CMD" app.py
EOF

# Create Windows batch file equivalent
cat > dist/run.bat << 'EOF'
@echo off
REM Windows batch script for running Gangwar executable

echo Gangwar Game Launcher
echo =====================
echo.

REM Kill any existing instances of gangwar
echo Checking for existing gangwar instances...
tasklist /FI "IMAGENAME eq gangwar.exe" 2>NUL | find /I /N "gangwar.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Killing existing gangwar instances...
    taskkill /F /IM gangwar.exe 2>NUL
    timeout /t 2 /nobreak >nul
)

REM Try to run the executable
if exist "gangwar.exe" (
    echo Found executable: gangwar.exe
    echo Running Gangwar executable...
    start "" gangwar.exe
    goto :eof
)

if exist "gangwar" (
    echo Found executable: gangwar
    echo Running Gangwar executable...
    start "" gangwar
    goto :eof
)

REM Fallback to Python
echo No executable found in current directory.
echo Falling back to Python...

REM Check if we're in the dist directory and need to go up
if exist "..\src\app.py" (
    echo Changing to parent directory...
    cd ..
)

REM Check if app.py exists
if not exist "src\app.py" (
    echo Error: src\app.py not found!
    echo Please ensure you're running this from the correct directory.
    pause
    exit /b 1
)

REM Find Python executable
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD=python3
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Python not found!
        echo Please install Python and try again.
        pause
        exit /b 1
    )
)

echo Using Python: %PYTHON_CMD%

REM Check if requirements are installed
%PYTHON_CMD% -c "import flask, flask_socketio" >nul 2>&1
if errorlevel 1 (
    echo Installing required dependencies...
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo Failed to install dependencies. Please install manually:
        echo %PYTHON_CMD% -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo Starting Gangwar with Python...
%PYTHON_CMD% app.py
EOF

# Make run.sh executable
chmod +x dist/run.sh

# Copy deployment scripts to dist
cp scripts/pythonanywhere.py dist/ 2>/dev/null || echo "scripts/pythonanywhere.py not found"

# Clean previous build directory (outside dist)
echo "Cleaning previous build..."
rm -rf build

# Check available disk space before building
echo "Checking available disk space..."
AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')
REQUIRED_SPACE=500000  # Require at least 500MB (in KB)

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo "WARNING: Insufficient disk space detected!"
    echo "Available: $(($AVAILABLE_SPACE / 1024)) MB"
    echo "Required: $(($REQUIRED_SPACE / 1024)) MB"
    echo ""
    echo "Attempting automatic cleanup..."

    # Try to free up space
    cleanup_disk_space

    # Check space again
    sleep 2
    AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')

    if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
        echo "ERROR: Still insufficient disk space after cleanup!"
        echo "Available: $(($AVAILABLE_SPACE / 1024)) MB"
        echo "Required: $(($REQUIRED_SPACE / 1024)) MB"
        echo ""
        echo "Manual cleanup suggestions:"
        echo "1. Check disk usage: df -h"
        echo "2. Find large files: du -h . | sort -hr | head -10"
        echo "3. Clear system temp: rm -rf /tmp/*"
        echo "4. Clear pip cache: pip cache purge"
        echo "5. Remove old kernels if on Linux"
        exit 1
    else
        echo "Success! Disk space freed up. Continuing build..."
        echo "New available space: $(($AVAILABLE_SPACE / 1024)) MB"
    fi
fi

echo "Disk space check passed. Available: $(($AVAILABLE_SPACE / 1024)) MB"

# Additional cleanup before build
echo "Performing additional cleanup..."
rm -rf __pycache__/ */__pycache__/ 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Build the application
echo "Building application with PyInstaller..."

# Generate or regenerate spec file with updated paths
echo "Regenerating gangwar.spec file with models, templates, and static data..."
rm -f gangwar.spec
pyinstaller --name gangwar --onefile --add-data "model:model" --add-data "src/templates:templates" --add-data "src/static:static" src/app.py --specpath .
# Remove the generated executable and build files, keep only spec
rm -rf build/ dist/

pyinstaller --clean gangwar.spec

# Set permissions to ensure directories can be deleted
chmod -R u+rwx build 2>/dev/null || true
chmod -R u+rwx dist 2>/dev/null || true

# Generate environment variables file
echo "Generating environment variables file..."
python3 scripts/generate_env.py

# Check if build was successful
if [ -f "dist/gangwar" ] || [ -f "dist/gangwar.exe" ]; then
    echo "Build successful! Files created in dist/ directory:"
    ls -la dist/

    # Make the executable runnable
    if [ -f "dist/gangwar" ]; then
        chmod +x dist/gangwar
        echo "Made executable runnable: ./dist/gangwar"
    fi

    if [ -f "dist/gangwar.exe" ]; then
        chmod +x dist/gangwar.exe
        echo "Made executable runnable: ./dist/gangwar.exe"
    fi

    echo ""
    echo "To run the application:"
    echo "./dist/gangwar"
    echo "or"
    echo "./dist/gangwar.exe  (on Windows)"
    echo ""
    echo "The executable is standalone and requires no external Python installation or libraries."
    echo ""
    echo "For PythonAnywhere deployment:"
    echo "Upload the contents of the dist/ directory to PythonAnywhere"
    echo "Use pythonanywhere.py as your WSGI application file"
else
    echo "Build failed! Check the output above for errors."
    exit 1
fi
