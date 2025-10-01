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
