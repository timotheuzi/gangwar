#!/bin/bash

# Gangwar Game Build Script - Cross-Platform Build Version
# This script builds the application locally using PyInstaller with cross-platform compatibility

echo "Building Gangwar Game for cross-platform deployment..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Delete and recreate dist directory
echo "Deleting and recreating dist/ directory..."
rm -rf dist
mkdir -p dist

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
if [ -f "../app.py" ]; then
    echo "Changing to parent directory..."
    cd ..
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found!"
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
if exist "..\app.py" (
    echo Changing to parent directory...
    cd ..
)

REM Check if app.py exists
if not exist "app.py" (
    echo Error: app.py not found!
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
cp pythonanywhere.py dist/ 2>/dev/null || echo "pythonanywhere.py not found"

# Clean previous build directory (outside dist)
echo "Cleaning previous build..."
rm -rf build

# Build the application
echo "Building application with PyInstaller..."
pyinstaller --clean gangwar.spec

# Generate environment variables file
echo "Generating environment variables file..."
python generate_env.py

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
